"""
app/services/po_parser.py — PO 문서(HTML) 파싱

SAP Business Network(Ariba)가 발행한 구매 오더 HTML에서 주요 필드를 추출한다.
쿠팡 등 Ariba를 쓰는 고객사의 PO는 CSS 클래스명이 일정하므로 이를 기준으로 뽑고,
클래스가 없는 항목은 '라벨: 값' 형태의 표 구조에서 라벨로 찾는다.

의존성을 늘리지 않기 위해 표준 라이브러리(html.parser)만 사용한다.
파싱은 어디까지나 '입력 도우미'이므로, 어떤 이유로든 실패하면 예외를 던지지 않고
찾은 항목만 돌려준다 (첨부 업로드 자체는 성공해야 한다).
"""

import logging
import re
from datetime import date
from html import unescape
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# 추출 대상 CSS 클래스 → 결과 키
_CLASS_FIELDS = {
    "po-INSPON-doc-num": "po_number",
    "fdml-ov-bill-to-gf-addr-name-val": "buyer_name",
}

# '라벨: 값' 표에서 찾을 항목 (라벨 텍스트 → 결과 키)
_LABEL_FIELDS = {
    "요청 번호": "pr_number",
    "요청자": "requester",
    "회사 코드": "company_code",
    "분류 코드": "category_code",
}

_DATE_RE = re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일")
_MONEY_RE = re.compile(r"([\d,]{4,})\s*(KRW|USD|EUR|JPY)")
# \w 는 한글도 매칭하므로 ASCII로 한정한다 (한글이 뒤에 붙어 들어오는 것을 방지)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# 약관 안내문에 반복 등장하는 일반 문의 주소 — 담당자 메일이 아니다
_GENERIC_EMAIL_PARTS = ("supplierhelp@", "accounts.payable@", "noreply@", "no-reply@")


def _squash(text: str) -> str:
    """줄바꿈·연속 공백을 하나로 접는다."""
    return re.sub(r"\s+", " ", text).strip()


class _TextExtractor(HTMLParser):
    """관심 있는 class를 가진 요소의 텍스트와, 전체 텍스트 조각 목록을 모은다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.by_class: dict[str, str] = {}
        self.chunks: list[str] = []
        self._class_stack: list[str | None] = []

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        matched = next((c for c in _CLASS_FIELDS if c in cls), None)
        self._class_stack.append(matched)

    def handle_endtag(self, tag):
        if self._class_stack:
            self._class_stack.pop()

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        self.chunks.append(text)
        for cls in self._class_stack:
            if cls and cls not in self.by_class:
                self.by_class[cls] = text


def _parse_korean_date(text: str) -> str | None:
    m = _DATE_RE.search(text)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


def parse_ariba_po(raw: bytes) -> dict:
    """
    Ariba PO HTML에서 주요 필드를 추출한다.
    인식하지 못한 필드는 결과 dict에 포함되지 않는다 (없는 값을 추측하지 않는다).
    """
    result: dict = {}
    try:
        html_text = raw.decode("utf-8", errors="replace")
    except Exception:
        return result

    # Ariba 문서가 맞는지 최소한으로 확인 — 아니면 파싱하지 않는다
    if "SAP Business Network" not in html_text and "ariba" not in html_text.lower():
        return result

    try:
        parser = _TextExtractor()
        parser.feed(html_text)
        chunks = parser.chunks

        for cls, key in _CLASS_FIELDS.items():
            if cls in parser.by_class:
                result[key] = parser.by_class[cls]

        # 라벨 다음에 오는 텍스트 조각을 값으로 본다
        for idx, chunk in enumerate(chunks):
            label = chunk.rstrip(":").strip()
            key = _LABEL_FIELDS.get(label)
            if key and key not in result and idx + 1 < len(chunks):
                result[key] = chunks[idx + 1]

        # 총 금액 — 문서에 여러 번 나오므로 가장 큰 값을 총액으로 본다
        amounts = [
            (int(m.group(1).replace(",", "")), m.group(2))
            for m in _MONEY_RE.finditer(html_text)
        ]
        if amounts:
            amount, currency = max(amounts, key=lambda a: a[0])
            result["total_amount"] = amount
            result["currency"] = currency

        # 요구 납기 — 문서에서 가장 이른 날짜를 납기로 본다
        # (오더 제출일·수신일은 항상 납기보다 앞서므로 '오더/수신' 문맥은 제외)
        delivery_dates = []
        for idx, chunk in enumerate(chunks):
            if "오더 제출" in chunk or "수신한 날짜" in chunk:
                continue
            parsed = _parse_korean_date(chunk)
            if parsed:
                delivery_dates.append(parsed)
        if delivery_dates:
            result["delivery_date"] = min(delivery_dates)

        # 납품처 담당자 이메일. 자사 메일과 약관 안내문의 일반 문의 주소는 제외한다.
        emails = []
        for e in _EMAIL_RE.findall(html_text):
            low = e.lower()
            if low.endswith("ezenuri.com") or "@ariba" in low or "@sap" in low:
                continue
            if any(g in low for g in _GENERIC_EMAIL_PARTS):
                continue
            emails.append(e)
        if emails:
            result["requester_email"] = emails[0]

        # 품목 설명 — '[...]' 로 시작하는 구매 건명
        for chunk in chunks:
            if chunk.startswith("[") and "]" in chunk and len(chunk) > 5:
                result["item_description"] = chunk
                break

        # 납품처 주소 — '품목 납품처' 라벨 뒤에 나오는 첫 굵은 텍스트와 주소
        for idx, chunk in enumerate(chunks):
            if chunk == "품목 납품처":
                tail = [c for c in chunks[idx + 1: idx + 12] if c and c != "대한민국"]
                if tail:
                    result["ship_to_name"] = _squash(tail[0])
                addr = next((c for c in tail if "도 " in c or "시 " in c or "구 " in c), None)
                if addr:
                    # Ariba는 '시/도'와 '전체 주소'를 한 텍스트 노드에 줄바꿈으로 함께 넣는다.
                    # 줄 단위로 나눠 가장 구체적인(긴) 줄만 취해 중복을 없앤다.
                    lines = [_squash(ln) for ln in addr.splitlines() if _squash(ln)]
                    result["ship_to_address"] = max(lines, key=len) if lines else _squash(addr)
                break

        for key in ("buyer_name", "requester", "item_description"):
            if key in result:
                result[key] = _squash(result[key])
    except Exception:
        # 파싱 실패가 업로드를 막아서는 안 된다
        logger.exception("PO 파싱 실패")

    return result


def is_parsable_po(filename: str, content_type: str | None) -> bool:
    """HTML 형식의 PO 문서인지 (파싱을 시도할 만한지) 판단한다."""
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    return name.endswith((".htm", ".html")) or "html" in ctype
