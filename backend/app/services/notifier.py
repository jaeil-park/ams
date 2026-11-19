"""
app/services/notifier.py — Discord 알림

승인 요청이 들어오면 관리자에게 Discord로 알린다.
- 웹후크(DISCORD_WEBHOOK_URL): 채널로 전송
- 봇(DISCORD_BOT_TOKEN + DISCORD_CHANNEL_ID): DM 채널 포함, 봇이 접근 가능한 채널로 전송

원칙
- 알림은 부가 기능이다. 전송 실패가 승인 요청 자체를 실패시키면 안 되므로 예외를 삼킨다.
- 요청 응답을 늦추지 않도록 BackgroundTasks 로 응답 후에 보낸다.
- 웹후크 URL·봇 토큰은 비밀값이므로 로그에 남기지 않는다.
- 사유 등 사용자 입력이 그대로 실리므로 @everyone 같은 멘션이 터지지 않게 막는다.
"""

import logging
from datetime import datetime, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_DISCORD_API = "https://discord.com/api/v10"
_TIMEOUT = httpx.Timeout(5.0)

# Discord embed 제한
_TITLE_MAX = 256
_FIELD_MAX = 1024

# 요청 종류별 표시
_KIND = {
    "PART_USAGE": ("파트 출고", 0x0D9488),   # teal
    "PART_QTY": ("재고 수량 변경", 0x7C3AED),  # violet
}


def is_enabled() -> bool:
    return bool(
        settings.DISCORD_WEBHOOK_URL
        or (settings.DISCORD_BOT_TOKEN and settings.DISCORD_CHANNEL_ID)
    )


def _clip(text, limit: int = _FIELD_MAX) -> str:
    value = str(text) if text not in (None, "") else "-"
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _app_url(path: str = "") -> str | None:
    base = (settings.APP_PUBLIC_URL or settings.FRONTEND_URL or "").rstrip("/")
    return f"{base}{path}" if base.startswith("http") else None


async def send_discord(message: dict) -> bool:
    """설정된 대상(웹후크/봇)으로 메시지를 보낸다. 하나라도 성공하면 True."""
    if not is_enabled():
        return False

    # 사용자 입력에 섞인 @everyone·@here·역할 멘션이 실제로 울리지 않게 한다
    body = {**message, "allowed_mentions": {"parse": []}}
    delivered = False

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        if settings.DISCORD_WEBHOOK_URL:
            try:
                res = await client.post(settings.DISCORD_WEBHOOK_URL, json=body)
                if res.status_code < 300:
                    delivered = True
                else:
                    logger.warning("Discord 웹후크 전송 실패: HTTP %s", res.status_code)
            except httpx.HTTPError as e:
                logger.warning("Discord 웹후크 전송 오류: %s", type(e).__name__)

        if settings.DISCORD_BOT_TOKEN and settings.DISCORD_CHANNEL_ID:
            try:
                res = await client.post(
                    f"{_DISCORD_API}/channels/{settings.DISCORD_CHANNEL_ID}/messages",
                    json=body,
                    headers={"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"},
                )
                if res.status_code < 300:
                    delivered = True
                else:
                    # 403 이면 봇이 그 채널(DM)에 접근할 수 없는 것
                    logger.warning("Discord 봇 전송 실패: HTTP %s", res.status_code)
            except httpx.HTTPError as e:
                logger.warning("Discord 봇 전송 오류: %s", type(e).__name__)

    return delivered


async def notify_approval_requested(
    *,
    approval_id: int,
    resource_type: str,
    part_label: str,
    current_qty: int,
    payload: dict,
    reason: str | None,
    requester_name: str | None,
    customer_name: str | None = None,
) -> None:
    """
    승인 요청 알림. BackgroundTasks 에서 호출되므로 ORM 객체 대신 값만 받는다
    (요청이 끝나면 DB 세션이 닫히기 때문).
    """
    try:
        kind_label, color = _KIND.get(resource_type, (resource_type, 0x2563EB))

        if resource_type == "PART_USAGE":
            qty = payload.get("qty")
            request_text = f"**{qty}개 출고**  (현재 재고 {current_qty}개 → {current_qty - (qty or 0)}개)"
        elif resource_type == "PART_QTY":
            target = payload.get("qty")
            diff = (target or 0) - current_qty
            sign = "+" if diff >= 0 else ""
            request_text = f"**{current_qty}개 → {target}개**  ({sign}{diff})"
        else:
            request_text = str(payload)

        fields = [
            {"name": "파트", "value": _clip(part_label), "inline": False},
            {"name": "요청 내용", "value": _clip(request_text), "inline": False},
        ]
        if customer_name:
            fields.append({"name": "고객사", "value": _clip(customer_name), "inline": True})
        if payload.get("po_number"):
            fields.append({"name": "PO / PR", "value": _clip(payload["po_number"]), "inline": True})
        fields.append({"name": "요청자", "value": _clip(requester_name), "inline": True})
        if reason:
            fields.append({"name": "사유", "value": _clip(reason), "inline": False})

        embed = {
            "title": _clip(f"🔔 승인 요청 #{approval_id} — {kind_label}", _TITLE_MAX),
            "color": color,
            "fields": fields,
            "footer": {"text": "AMS ERP · 승인 관리에서 처리해 주세요"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        url = _app_url("/approvals")
        if url:
            embed["url"] = url

        await send_discord({"embeds": [embed]})
    except Exception:
        # 알림 실패가 다른 흐름에 영향을 주지 않도록 한다
        logger.exception("승인 요청 알림 처리 실패 (approval_id=%s)", approval_id)


async def send_test_message(requested_by: str | None) -> bool:
    """설정 확인용 테스트 메시지."""
    embed = {
        "title": "✅ AMS 알림 연결 테스트",
        "description": "이 메시지가 보이면 승인 요청 알림이 정상적으로 설정된 것입니다.",
        "color": 0x16A34A,
        "fields": [{"name": "요청자", "value": _clip(requested_by), "inline": True}],
        "footer": {"text": "AMS ERP"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    url = _app_url("/approvals")
    if url:
        embed["url"] = url
    return await send_discord({"embeds": [embed]})
