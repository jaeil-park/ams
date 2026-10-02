"""
app/services/hpe_portal.py — HPE 지원 포털 '보증 확인' 자동 조회 (Playwright, warranty-worker 컨테이너 전용)

- 조회 전용 HPE 계정(HPE_USERNAME/HPE_PASSWORD)으로 로그인하고 세션을 HPE_STATE_PATH 에 보관한다.
- 로그인 화면은 2단계: 이메일 입력 → '다음' → 비밀번호 입력 → 로그인 (auth.hpe.com)
- 캡차·추가 인증(MFA)·비밀번호 오류가 나오면 우회하지 않고 HpeLoginRequired 를 던진다.
  → 작업자는 LOGIN_REQUIRED 상태를 기록하고 대기 건을 그대로 둔다. (AMS 화면에 '재로그인 필요' 표시)

playwright 는 warranty-worker 이미지에만 설치되므로 백엔드에서 이 모듈을 import 하지 않는다.
"""

from __future__ import annotations

import logging
import os
import re

from playwright.async_api import Browser, BrowserContext, Page, async_playwright, TimeoutError as PwTimeout

from app.core.config import settings
from app.services.warranty_parse import hpe_not_found, parse_hpe_text, summarize_hpe_rows

logger = logging.getLogger(__name__)

WARRANTY_URL = "https://support.hpe.com/connect/s/warrantycheck"
_RESULT_MARK = re.compile(r"제품 번호|Product Number", re.I)
_CHALLENGE = re.compile(r"captcha|recaptcha|hcaptcha|verify it'?s you|인증 코드|verification code|okta verify|본인 확인", re.I)


class HpeLoginRequired(Exception):
    """자동 로그인이 불가능한 상태 (캡차, 추가 인증, 계정 정보 오류 등)"""


class HpePortalClient:
    def __init__(self) -> None:
        self._pw = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=settings.HPE_HEADLESS)
        state = settings.HPE_STATE_PATH if os.path.exists(settings.HPE_STATE_PATH) else None
        self._ctx = await self._browser.new_context(locale="ko-KR", storage_state=state)

    async def close(self) -> None:
        for obj in (self._ctx, self._browser):
            try:
                if obj:
                    await obj.close()
            except Exception:  # noqa: BLE001
                pass
        if self._pw:
            await self._pw.stop()

    async def _save_state(self) -> None:
        os.makedirs(os.path.dirname(settings.HPE_STATE_PATH) or ".", exist_ok=True)
        await self._ctx.storage_state(path=settings.HPE_STATE_PATH)

    # ─── 로그인 ─────────────────────────────────────────────────────────────────

    async def _login(self, page: Page) -> None:
        if not (settings.HPE_USERNAME and settings.HPE_PASSWORD):
            raise HpeLoginRequired("HPE_USERNAME / HPE_PASSWORD 환경변수가 설정되지 않았습니다.")
        logger.info("HPE 포털 로그인 시도")
        await page.wait_for_selector("#email-sign-in, input[name='email']", timeout=30000)
        await self._check_challenge(page)
        await page.fill("#email-sign-in, input[name='email']", settings.HPE_USERNAME)
        await page.click("button[type='submit']")
        try:
            await page.wait_for_selector("input[type='password']", timeout=30000)
        except PwTimeout:
            await self._check_challenge(page)
            raise HpeLoginRequired("비밀번호 입력 화면이 나오지 않았습니다. (계정 확인 필요)")
        await page.fill("input[type='password']", settings.HPE_PASSWORD)
        await page.click("button[type='submit']")
        try:
            await page.wait_for_url(re.compile(r"https://support\.hpe\.com/.*"), timeout=60000)
        except PwTimeout:
            await self._check_challenge(page)
            body = (await page.inner_text("body"))[:200].replace("\n", " ")
            raise HpeLoginRequired(f"로그인 후 포털로 돌아오지 않았습니다: {body}")
        await self._save_state()
        logger.info("HPE 포털 로그인 완료, 세션 저장")

    async def _check_challenge(self, page: Page) -> None:
        html = (await page.content())[:200000]
        if _CHALLENGE.search(html) or await page.locator("iframe[src*='captcha']").count():
            raise HpeLoginRequired("캡차 또는 추가 인증(MFA)이 요구됩니다. HPE 계정 설정을 확인하세요.")

    async def _open_check_page(self, page: Page) -> None:
        await page.goto(WARRANTY_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=60000)
        if "auth.hpe.com" in page.url or await page.locator("#email-sign-in").count():
            await self._login(page)
            await page.goto(WARRANTY_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=60000)
        await page.locator("input.slds-input").first.wait_for(state="visible", timeout=45000)

    async def ensure_login(self) -> None:
        """작업자 시작 시 세션 확인 (필요하면 로그인)"""
        page = await self._ctx.new_page()
        try:
            await self._open_check_page(page)
        finally:
            await page.close()

    # ─── 조회 ───────────────────────────────────────────────────────────────────

    async def lookup(self, serial: str) -> dict:
        """
        시리얼 1건 조회 → {status, start_date, end_date, service_level, product_name, detail, error}
        """
        page = await self._ctx.new_page()
        try:
            await self._open_check_page(page)
            box = page.locator("input.slds-input").first
            await box.fill(serial)
            await page.get_by_role("button", name=re.compile(r"제출|Submit")).first.click()
            try:
                await page.wait_for_function(
                    "() => /제품 번호|Product Number|찾을 수 없|not found|유효하지 않/i.test(document.body.innerText)",
                    timeout=45000,
                )
            except PwTimeout:
                return {"status": "ERROR", "error": "HPE 조회 결과가 45초 안에 나오지 않았습니다."}
            await page.wait_for_timeout(1500)
            text = await page.evaluate("() => document.body.innerText")
            if not _RESULT_MARK.search(text):
                if hpe_not_found(text):
                    return {"status": "NOT_FOUND", "error": "HPE 포털에서 찾을 수 없는 일련 번호"}
                return {"status": "ERROR", "error": "HPE 결과 화면을 해석하지 못했습니다."}

            info = parse_hpe_text(text)
            s = summarize_hpe_rows(info["rows"])
            detail = {"product_number": info.get("product_number"), "rows": info["rows"]}
            if not s["end_date"]:
                return {"status": "NOT_FOUND", "product_name": info.get("product_name"), "detail": detail,
                        "error": "하드웨어 워런티 항목이 없습니다."}
            return {
                "status": "DONE",
                "start_date": s["start_date"], "end_date": s["end_date"],
                "service_level": s["service_level"], "product_name": info.get("product_name"),
                "detail": detail, "error": None,
            }
        finally:
            await page.close()
