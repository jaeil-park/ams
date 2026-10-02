"""
워런티 조회 결과 해석 단위 테스트 (DB/네트워크 불필요)
실행: cd backend && python -m pytest tests/test_warranty_parse.py -q

HPE 시험 자료는 2026-10-02 HPE 포털 '보증 확인' 화면에서 실제로 조회한 결과 텍스트 형식을 그대로 옮겼다.
"""

from datetime import date

from app.services.warranty_parse import (
    detect_vendor,
    parse_date,
    parse_hpe_text,
    summarize_dell_api,
    summarize_dell_site,
    summarize_hpe_rows,
)

T = "\n\t\n"  # HPE 표 innerText 의 칸 구분


def _row(*cells: str) -> str:
    return T.join(cells)


HEADER = _row("유형", "서비스 유형", "시작일", "종료일", "서비스 수준", "제공 제품", "상태")


def _page(serial: str, pn: str, name: str, *rows: str) -> str:
    return (
        "보증 확인\n영업 담당자에게 문의\n아래에서 제품 보증 및 지원 상태를 확인합니다.\nLoading Image\n"
        f"일련 번호\n{serial}\n제품 번호\n{pn}\n제품 이름\n{name}\n제품 추가\n탐색 모드\n"
        + HEADER + "\n\n" + "\n\n".join(rows)
        + "\n\n다른 제품 확인\n\nHPE 고객 지원 센터 포털을 통해 얻은 HPE 보증 및 지원 검증 상태는 법률적 목적에 대한 구속력이 없습니다."
    )


# 만료된 DL360 Gen9 — 기본 보증 + Initial Setup
HPE_SGH629VE6B = _page(
    "SGH629VE6B", "755258-B21", "HPE DL360 Gen9 8SFF CTO Server",
    _row("기본 보증", "Wty: HPE HW Maintenance Onsite Support", "2016년 7월 25일", "2019년 8월 23일",
         "Global Coverage\nNextAvail TechResource Remote\nNext Cov Day Onsite Response",
         "Parts and Material provided\nOnsite Support\nHardware Problem Diagnosis", "만료됨"),
    _row("", "Wty: HPE Support for Initial Setup", "2016년 7월 25일", "2016년 11월 21일",
         "NextAvail TechResource Remote\n2 Hr Remote Response", "Initial Setup Assistance", "만료됨"),
)

# DL380 Gen12 — 지원 계약 + 패키지(Tech Care) + 기본 보증 + Initial Setup(2026-09-19 종료)
HPE_SGHD45FLRB = _page(
    "SGHD45FLRB", "P89232-375", "HPE DL380 G12 6505P 2x32G 8SFF SSD Svr",
    _row("지원 계약", "HPE Tech Care Essential SVC", "", "", "", "", ""),
    _row("", "HPE Remote Tech Support", "2026년 6월 22일", "2029년 6월 21일", "", "", "활성"),
    _row("", "HPE Hardware Tech Support", "2026년 6월 22일", "2029년 6월 21일", "", "", "활성"),
    _row("패키지 지원", "HPE 3Y Tech Care Essential Service HW On", "", "", "", "", ""),
    _row("", "HPE Hardware Tech Care", "2026년 6월 22일", "2029년 6월 21일",
         "Essential Support\nService Level Key\nTech Care", "Replacement Parts\nOnsite Support", "활성"),
    _row("", "HPE Remote Tech Care", "2026년 6월 22일", "2029년 6월 21일",
         "Essential Support", "Technical Support", "활성"),
    _row("기본 보증", "Wty: HPE HW Maintenance Onsite Support", "2026년 6월 22일", "2029년 6월 21일",
         "Std Office Hrs Std Office Days\nNext Cov Day Onsite Response",
         "Onsite Support\nParts and Material provided", "활성"),
    _row("", "Wty: HPE Support for Initial Setup", "2026년 6월 22일", "2026년 9월 19일",
         "NextAvail TechResource Remote", "Initial Setup Assistance", "만료됨"),
)

# DL20 Gen9 — 원래 기본 보증 1년
HPE_SGH912Y2MQ = _page(
    "SGH912Y2MQ", "871429-B21", "HPE DL20 Gen9 E3-1220v6 LFF Base BTO Svr",
    _row("기본 보증", "Wty: HPE HW Maintenance Onsite Support", "2019년 3월 25일", "2020년 4월 23일",
         "Next Cov Day Onsite Response", "Onsite Support", "만료됨"),
    _row("", "Wty: HPE Support for Initial Setup", "2019년 3월 25일", "2019년 7월 22일",
         "2 Hr Remote Response", "Initial Setup Assistance", "만료됨"),
)

# DL360 Gen10 — 리스트 Get 에 Initial Setup 종료일(2025-03-30)이 잘못 들어갔던 장비
HPE_CNXD1R009Y = _page(
    "CNXD1R009Y", "P19774-B21", "HPE DL360 Gen10 4208 1P 16G NC 8SFF Svr",
    _row("기본 보증", "Wty: HPE HW Maintenance Onsite Support", "2024년 12월 31일", "2027년 12월 30일",
         "Next Cov Day Onsite Response", "Onsite Support", "활성"),
    _row("", "Wty: HPE Support for Initial Setup", "2024년 12월 31일", "2025년 3월 30일",
         "2 Hr Remote Response", "Initial Setup Assistance", "만료됨"),
)


# ─── 날짜 ──────────────────────────────────────────────────────────────────────

def test_parse_date_formats():
    assert parse_date("2026년 6월 22일") == date(2026, 6, 22)
    assert parse_date("2월 28, 2026") == date(2026, 2, 28)           # Dell 사이트 ko-kr
    assert parse_date("Jun 22, 2026") == date(2026, 6, 22)
    assert parse_date("June 22, 2026") == date(2026, 6, 22)
    assert parse_date("2026-02-28T00:00:00Z") == date(2026, 2, 28)
    assert parse_date("2024-09-31") is None                         # 존재하지 않는 날짜
    assert parse_date("") is None


# ─── 제조사 판별 ───────────────────────────────────────────────────────────────

def test_detect_vendor():
    assert detect_vendor("8MN7CC4") == "DELL"
    assert detect_vendor("SGHD45FLRB") == "HPE"
    assert detect_vendor("CN703816MW") == "HPE"
    assert detect_vendor("ABC") == "UNKNOWN"
    assert detect_vendor("ABC", "Dell Inc.") == "DELL"             # AMS 등록 제조사 우선
    assert detect_vendor("8MN7CC4", "HPE") == "HPE"


# ─── HPE ───────────────────────────────────────────────────────────────────────

def test_hpe_product_info():
    info = parse_hpe_text(HPE_SGHD45FLRB)
    assert info["serial"] == "SGHD45FLRB"
    assert info["product_number"] == "P89232-375"
    assert info["product_name"].startswith("HPE DL380 G12")


def test_hpe_initial_setup_is_ignored():
    """Initial Setup 종료일(2026-09-19)이 아니라 하드웨어 지원 종료일(2029-06-21)을 써야 한다."""
    s = summarize_hpe_rows(parse_hpe_text(HPE_SGHD45FLRB)["rows"])
    assert s["start_date"] == date(2026, 6, 22)
    assert s["end_date"] == date(2029, 6, 21)
    assert "Initial Setup" not in s["service_level"]


def test_hpe_expired_base_warranty():
    s = summarize_hpe_rows(parse_hpe_text(HPE_SGH629VE6B)["rows"])
    assert (s["start_date"], s["end_date"]) == (date(2016, 7, 25), date(2019, 8, 23))


def test_hpe_dl20_one_year_is_kept():
    s = summarize_hpe_rows(parse_hpe_text(HPE_SGH912Y2MQ)["rows"])
    assert (s["start_date"], s["end_date"]) == (date(2019, 3, 25), date(2020, 4, 23))


def test_hpe_start_date_not_initial_setup_end():
    s = summarize_hpe_rows(parse_hpe_text(HPE_CNXD1R009Y)["rows"])
    assert (s["start_date"], s["end_date"]) == (date(2024, 12, 31), date(2027, 12, 30))


def test_hpe_rows_have_sections():
    rows = parse_hpe_text(HPE_SGHD45FLRB)["rows"]
    sections = {r["section"] for r in rows}
    assert {"지원 계약", "패키지 지원", "기본 보증"} <= sections


# ─── Dell ──────────────────────────────────────────────────────────────────────

def test_dell_api_summary():
    asset = {
        "serviceTag": "8MN7CC4", "shipDate": "2025-08-19T00:00:00Z", "productLineDescription": "POWEREDGE R760XS",
        "invalid": False,
        "entitlements": [
            {"startDate": "2025-08-19T00:00:00Z", "endDate": "2028-08-26T23:59:59Z", "serviceLevelDescription": "ProSupport"},
            {"startDate": "2025-08-19T00:00:00Z", "endDate": "2025-09-19T23:59:59Z", "serviceLevelDescription": "Onsite Diagnosis"},
        ],
    }
    s = summarize_dell_api(asset)
    assert (s["start_date"], s["end_date"], s["service_level"]) == (date(2025, 8, 19), date(2028, 8, 26), "ProSupport")


def test_dell_api_invalid_tag():
    assert summarize_dell_api({"serviceTag": "XXXXXXX", "invalid": True, "entitlements": []})["end_date"] is None


def test_dell_site_summary():
    s = summarize_dell_site({"warrantyStartDate": "2월 28, 2026", "warrantyEndDate": "4월 21, 2029",
                             "warrantyDisplayName": "ProSupport"})
    assert (s["start_date"], s["end_date"]) == (date(2026, 2, 28), date(2029, 4, 21))
