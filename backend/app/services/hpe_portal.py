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
# 보증 확인의 '일련 번호' 입력칸 (type=text). 상단 헤더 검색창도 slds-input 이지만 type=search 라 제외한다.
SERIAL_INPUT = "input.slds-input[type='text']:visible"
_CHALLENGE = re.compile(r"captcha|recaptcha|hcaptcha|verify it'?s you|인증 코드|verification code|okta verify|본인 확인", re.I)


# HPE 포털은 Salesforce 컴포넌트(Shadow DOM) 안에 결과를 그린다. document.body.innerText 는 Shadow DOM 안의
# 글자를 읽지 못하므로, Shadow DOM·슬롯까지 따라 들어가 innerText 와 같은 형식(표 칸 = 탭 한 줄, 행 = 빈 줄)으로 모은다.
DEEP_TEXT_JS = r"""() => {
  const BLOCK = new Set(['DIV','P','SECTION','ARTICLE','HEADER','FOOTER','LI','UL','OL','H1','H2','H3','H4','H5','H6',
    'TABLE','THEAD','TBODY','TFOOT','FORM','LABEL','DT','DD','DL','NAV','MAIN','ASIDE','BR']);
  const SKIP = new Set(['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','svg','SVG']);
  let out = '';
  const nl = () => { if (out && !out.endsWith('\n')) out += '\n'; };
  // 현재 행 시작(min) 이후의 끝 줄바꿈만 지운다 — 앞 행과의 경계(빈 줄)는 보존
  const trimTo = (min) => { while (out.length > min && out.endsWith('\n')) out = out.slice(0, -1); };
  const shown = (el) => { const cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden'; };
  function kids(el) {
    if (el.tagName === 'SLOT') return el.assignedNodes({ flatten: true });
    return [...(el.shadowRoot || el).childNodes];
  }
  function walk(node) {
    if (node.nodeType === 3) {
      const t = node.textContent.replace(/\s+/g, ' ').trim();
      if (t) out += (out && !out.endsWith('\n') && !out.endsWith(' ') ? ' ' : '') + t;
      return;
    }
    if (node.nodeType !== 1) return;
    if (SKIP.has(node.tagName) || !shown(node)) return;
    if (node.tagName === 'TR') {
      nl();
      const start = out.length;
      const cells = [...node.children].filter((c) => c.tagName === 'TD' || c.tagName === 'TH');
      cells.forEach((c, i) => {
        if (i) { trimTo(start); out += '\n\t\n'; }
        kids(c).forEach(walk);
      });
      trimTo(start);
      out += '\n\n';
      return;
    }
    const block = BLOCK.has(node.tagName);
    if (block) nl();
    kids(node).forEach(walk);
    if (block) nl();
  }
  walk(document.body);
  return out;
}"""


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

    async def _wait_state(self, page: Page, timeout_sec: float = 60) -> str:
        """
        HPE 포털은 로그인 여부에 따라 여러 번 리다이렉트된다. 화면이 자리 잡을 때까지 기다려
        LOGIN(로그인 화면) / READY(보증 확인 입력 화면) / UNKNOWN(그 밖의 화면) 중 하나를 돌려준다.
        """
        waited = 0.0
        while waited < timeout_sec:
            try:
                url = page.url
                if "auth.hpe.com" in url or await page.locator("#email-sign-in").count():
                    return "LOGIN"
                if ("warrantycheck" in url and "LoginFlow" not in url
                        and await page.locator(SERIAL_INPUT).count()):
                    return "READY"
            except Exception:  # noqa: BLE001 — 리다이렉트 중 페이지 컨텍스트가 바뀌면 다시 확인
                pass
            await page.wait_for_timeout(1500)
            waited += 1.5
        return "UNKNOWN"

    async def _diagnose(self, page: Page) -> str:
        """예상과 다른 화면을 /data 에 스크린샷·텍스트로 남기고 요약 문구를 돌려준다."""
        base = os.path.dirname(settings.HPE_STATE_PATH) or "."
        text = ""
        try:
            text = (await page.evaluate(DEEP_TEXT_JS))[:20000]
            with open(os.path.join(base, "hpe_last_page.txt"), "w", encoding="utf-8") as f:
                f.write(f"URL: {page.url}\n\n{text}")
            await page.screenshot(path=os.path.join(base, "hpe_last_page.png"), full_page=True)
        except Exception:  # noqa: BLE001
            logger.exception("HPE 진단 자료 저장 실패")
        return " ".join(text.split())[:160]

    async def _open_check_page(self, page: Page) -> None:
        await page.goto(WARRANTY_URL, wait_until="domcontentloaded", timeout=60000)
        state = await self._wait_state(page)
        if state == "LOGIN":
            await self._login(page)
            await page.goto(WARRANTY_URL, wait_until="domcontentloaded", timeout=60000)
            state = await self._wait_state(page)
            if state == "LOGIN":
                raise HpeLoginRequired("로그인 후에도 다시 로그인 화면이 나옵니다. 계정 정보를 확인하세요.")
        if state != "READY":
            summary = await self._diagnose(page)
            if "LoginFlow" in page.url:
                raise HpeLoginRequired(
                    "HPE가 로그인 후 추가 절차 화면(DCELoginFlowScreen)을 요구합니다. 조회 전용 계정으로 일반 브라우저에서 "
                    "support.hpe.com 에 한 번 직접 로그인해 약관·프로필 절차를 마친 뒤 작업자를 재시작하세요. "
                    f"(화면: {summary} / 스크린샷: hpe_last_page.png)"
                )
            raise HpeLoginRequired(f"HPE 보증 확인 화면을 열지 못했습니다 ({page.url[:80]}): {summary}")

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
            box = page.locator(SERIAL_INPUT).first
            await box.fill(serial)
            await box.press("Tab")  # 입력값 확정(change 이벤트)
            await page.get_by_role("button", name=re.compile(r"제출|Submit")).first.click()
            # Playwright 텍스트 검색은 Shadow DOM 안까지 찾는다
            result = page.get_by_text(re.compile(r"제품 번호|Product Number"))
            missing = page.get_by_text(re.compile(r"찾을 수 없|유효하지 않|not found|could not find|invalid serial", re.I))
            try:
                await result.or_(missing).first.wait_for(state="visible", timeout=45000)
            except PwTimeout:
                summary = await self._diagnose(page)
                return {"status": "ERROR", "error": f"HPE 조회 결과가 45초 안에 나오지 않았습니다. (화면: {summary})"}
            await page.wait_for_timeout(2500)  # 표가 다 그려질 시간
            text = await page.evaluate(DEEP_TEXT_JS)
            if not _RESULT_MARK.search(text):
                if hpe_not_found(text):
                    return {"status": "NOT_FOUND", "error": "HPE 포털에서 찾을 수 없는 일련 번호"}
                summary = await self._diagnose(page)
                return {"status": "ERROR", "error": f"HPE 결과 화면을 해석하지 못했습니다. (화면: {summary})"}

            info = parse_hpe_text(text)
            s = summarize_hpe_rows(info["rows"])
            detail = {"product_number": info.get("product_number"), "rows": info["rows"]}
            if not info["rows"]:
                summary = await self._diagnose(page)
                return {"status": "ERROR", "product_name": info.get("product_name"),
                        "error": f"HPE 결과 표를 해석하지 못했습니다 (hpe_last_page.txt 확인). (화면: {summary})"}
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
