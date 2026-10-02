"""
app/services/warranty_parse.py — 제조사 워런티 조회 결과 해석 (순수 함수, DB/네트워크 없음)

- detect_vendor        : 시리얼/AMS 등록 제조사로 DELL·HPE 판별
- parse_date           : '2026년 6월 22일' / '2월 28, 2026' / 'Jun 22, 2026' / ISO 날짜를 date 로 변환
- parse_hpe_text       : HPE 포털 '보증 확인' 결과 화면 텍스트 → 제품 정보 + 지원 항목 행
- summarize_hpe_rows   : 지원 항목 행 → 워런티 시작/종료일
- summarize_dell_api   : Dell TechDirect asset-entitlements 응답 1건 → 워런티 시작/종료일

HPE 결과에는 'Wty: HPE Support for Initial Setup'(초기 설정 지원, 약 3개월) 같은 항목이 같이 나온다.
이 종료일을 하드웨어 워런티 종료일로 착각하면 워런티가 3개월~1년으로 잘못 기록되므로
하드웨어 지원 항목만 골라 종료일을 계산한다.
"""

from __future__ import annotations

import re
from datetime import date, datetime

VENDORS = ("DELL", "HPE")

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


# ─── 제조사 판별 ───────────────────────────────────────────────────────────────

def detect_vendor(serial: str, inventory_vendor: str | None = None) -> str:
    """
    AMS에 등록된 제조사(vendor) 값이 있으면 그것을 우선 사용하고,
    없으면 시리얼 형식으로 추정한다. (Dell 서비스 태그 7자리, HPE 시리얼 10자리)
    """
    v = (inventory_vendor or "").upper()
    if "DELL" in v:
        return "DELL"
    if v.startswith("HP"):
        return "HPE"
    s = re.sub(r"\s", "", serial or "").upper()
    if re.fullmatch(r"[0-9A-Z]{7}", s):
        return "DELL"
    if re.fullmatch(r"[0-9A-Z]{10}", s):
        return "HPE"
    return "UNKNOWN"


def normalize_serial(serial: str) -> str:
    return re.sub(r"\s", "", serial or "").upper()


# ─── 날짜 ──────────────────────────────────────────────────────────────────────

def parse_date(text: str | None) -> date | None:
    """제조사 화면/API에 나오는 여러 날짜 표기를 date 로 변환한다. 해석 불가 시 None."""
    if not text:
        return None
    t = str(text).strip()
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", t)          # 2026년 6월 22일
    if m:
        return _safe(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})\s*월\s*(\d{1,2}),\s*(\d{4})", t)                    # 2월 28, 2026 (Dell ko-kr)
    if m:
        return _safe(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)                                  # 2026-02-28 / ISO
    if m:
        return _safe(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s*(\d{4})", t)            # Jun 22, 2026 / June 22, 2026
    if m and m.group(1).lower() in _MONTHS:
        return _safe(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?\s+(\d{4})", t)             # 22 Jun 2026
    if m and m.group(2).lower() in _MONTHS:
        return _safe(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
    return None


def _safe(y: int, mo: int, d: int) -> date | None:
    try:
        return date(y, mo, d)
    except ValueError:
        return None


# ─── HPE ───────────────────────────────────────────────────────────────────────

_HPE_LABELS = {
    "serial": ("일련 번호", "Serial Number", "Serial number"),
    "product_number": ("제품 번호", "Product Number", "Product number"),
    "product_name": ("제품 이름", "Product Name", "Product name"),
}
_HPE_HEADER_FIRST = ("유형", "Type")
_HPE_BASE_SECTIONS = ("기본 보증", "Base Warranty", "Base warranty")


def parse_hpe_text(text: str) -> dict:
    """
    HPE 포털 '보증 확인' 결과 화면의 텍스트(document.body.innerText)를 해석한다.
    표는 행이 빈 줄로, 칸이 '\\n\\t\\n' 으로 구분된 형태로 들어온다.
    반환: {serial, product_number, product_name, rows: [{section, service_type, start, end, status}]}
    """
    lines = [ln.strip() for ln in text.replace("\r", "").split("\n")]
    info: dict = {"serial": None, "product_number": None, "product_name": None}
    for key, labels in _HPE_LABELS.items():
        for i, ln in enumerate(lines):
            if ln in labels:
                nxt = next((x for x in lines[i + 1:i + 4] if x), None)
                info[key] = nxt
                break

    # 표 영역: 헤더('유형'/'Type') 이후
    norm = "\n" + text.replace("\r", "")
    start = -1
    for h in _HPE_HEADER_FIRST:
        start = norm.find("\n" + h + "\n")
        if start >= 0:
            break
    info["rows"] = rows_from_cells(_split_table(norm[start + 1:])) if start >= 0 else []
    return info


def _split_table(table_text: str) -> list[list[str]]:
    """
    innerText 표 → 행/칸. 탭만 있는 줄 = 칸 경계, 완전히 빈 줄 = 행 경계.
    (한 줄 안에 탭이 섞여 있으면 탭 기준으로도 칸을 나눈다)
    """
    rows: list[list[str]] = []
    cur: list[list[str]] = [[]]

    def flush():
        if any(any(x for x in c) for c in cur):
            rows.append(["\n".join(c).strip() for c in cur])

    for ln in table_text.split("\n"):
        if not ln.strip():
            if "\t" in ln:
                cur.append([])
            else:
                flush()
                cur = [[]]
            continue
        parts = ln.split("\t")
        cur[-1].append(parts[0].strip())
        for p in parts[1:]:
            cur.append([p.strip()] if p.strip() else [])
    flush()
    return rows


def rows_from_cells(cells_rows: list[list[str]]) -> list[dict]:
    """
    표의 행(칸 목록)들을 지원 항목으로 정리한다. 첫 칸(구분)이 빈 행은 위 행의 구분을 이어받는다.
    칸 구성: [구분, 서비스 유형, 시작일, 종료일, 서비스 수준, 제공 제품, 상태]
    """
    rows: list[dict] = []
    section = ""
    for cells in cells_rows:
        cells = [c for c in cells]
        if not cells or cells[0] in _HPE_HEADER_FIRST:
            continue
        if cells[0]:
            section = cells[0].split("\n")[0]
        if len(cells) < 2 or not cells[1]:
            continue
        dates = [d for d in (parse_date(c) for c in cells[2:]) if d]
        status = cells[-1].split("\n")[0] if len(cells) >= 7 else ""
        rows.append({
            "section": section,
            "service_type": cells[1].split("\n")[0],
            "start": dates[0].isoformat() if len(dates) >= 1 else None,
            "end": dates[1].isoformat() if len(dates) >= 2 else None,
            "status": status,
        })
    return rows


def _is_hw_coverage(service_type: str) -> bool:
    s = service_type.lower()
    if "initial setup" in s or "remote" in s or "software" in s or "install" in s:
        return False
    return s.startswith("wty:") or "hardware" in s or " hw " in f" {s} "


def summarize_hpe_rows(rows: list[dict]) -> dict:
    """
    하드웨어 지원 항목만으로 워런티 기간을 계산한다.
    - 시작일: '기본 보증'의 하드웨어 항목 시작일 (없으면 하드웨어 항목 중 가장 이른 시작일)
    - 종료일: 하드웨어 항목(기본 보증 + Care Pack/계약) 중 가장 늦은 종료일
    """
    hw = [r for r in rows if r.get("end") and _is_hw_coverage(r.get("service_type", ""))]
    if not hw:
        return {"start_date": None, "end_date": None, "service_level": None}
    base = [r for r in hw if r.get("section") in _HPE_BASE_SECTIONS and r.get("start")]
    starts = [r["start"] for r in (base or hw) if r.get("start")]
    last = max(hw, key=lambda r: r["end"])
    return {
        "start_date": date.fromisoformat(min(starts)) if starts else None,
        "end_date": date.fromisoformat(last["end"]),
        "service_level": last["service_type"][:200],
    }


def hpe_not_found(text: str) -> bool:
    """조회 결과가 없다는 안내 문구가 있으면 True"""
    t = text.lower()
    return any(k in t for k in ("찾을 수 없", "유효하지 않", "not found", "no results", "could not find", "invalid serial"))


# ─── Dell ──────────────────────────────────────────────────────────────────────

def summarize_dell_api(asset: dict) -> dict:
    """
    Dell TechDirect asset-entitlements 응답의 자산 1건을 정리한다.
    종료일은 entitlements 중 가장 늦은 endDate, 시작일은 가장 이른 startDate(없으면 shipDate).
    """
    ents = [e for e in (asset.get("entitlements") or []) if e.get("endDate")]
    if asset.get("invalid") or not ents:
        return {"start_date": parse_date(asset.get("shipDate")), "end_date": None, "service_level": None,
                "product_name": asset.get("productLineDescription")}
    last = max(ents, key=lambda e: e["endDate"])
    starts = [d for d in (parse_date(e.get("startDate")) for e in ents) if d]
    return {
        "start_date": min(starts) if starts else parse_date(asset.get("shipDate")),
        "end_date": parse_date(last["endDate"]),
        "service_level": (last.get("serviceLevelDescription") or "")[:200] or None,
        "product_name": asset.get("productLineDescription") or asset.get("systemDescription"),
    }


def summarize_dell_site(payload: dict) -> dict:
    """Dell 지원 사이트(contractservicesapi) 응답 → 워런티 시작/종료일 (확장 프로그램 결과 검증용)"""
    return {
        "start_date": parse_date(payload.get("warrantyStartDate")),
        "end_date": parse_date(payload.get("warrantyEndDate")),
        "service_level": payload.get("warrantyDisplayName"),
    }


def to_iso(d: date | datetime | None) -> str | None:
    return d.isoformat() if d else None
