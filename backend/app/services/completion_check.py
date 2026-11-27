"""
app/services/completion_check.py — 프로젝트 완료 처리 체크리스트

두 종류로 나눈다.
- 자동 검사: AMS가 데이터로 직접 확인할 수 있는 항목. 사람이 체크할 수 없고, 통과해야 완료된다.
- 수기 확인: AMS가 알 수 없는 현장 사실. 담당자가 직접 체크해야 완료된다.

자동 검사를 사람이 체크하게 만들면 '체크는 했지만 실제로는 안 된' 상태가 생기므로 분리한다.

예외(해당 없음) 처리
- 발주 문서가 없는 하도급·구두 발주 건, 품목 없이 작업만 한 기술지원 건처럼
  검사를 통과할 수 없는 '정상 사례'가 있다. 이런 항목은 사유를 남기고 해당 없음으로 처리한다.
- 단, 결재 대기 같은 '실제로 처리해야 끝나는 일'은 예외 대상이 아니다 (exemptable=False).
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.services.po_link import pending_usage_approvals, usage_po_filter

# 수기 확인 항목 — 담당자가 직접 체크해야 하는 현장 사실
MANUAL_CHECK_ITEMS = [
    {"key": "FIELD_INSTALL", "label": "현장 설치/검수 완료"},
    {"key": "HANDOVER", "label": "고객사 인수인계 완료"},
    {"key": "NAS_DOCS", "label": "NAS 문서 정리 완료 (견적서·확인서·검수사진)"},
]

# 해당 없음 처리가 허용되는 자동 검사
EXEMPTABLE_CHECKS = {"PO_ATTACHED", "INSPECTION_ATTACHED", "HAS_ITEMS"}

# 예외 사유 최소 길이 — '없음', '.' 같은 형식적 입력을 막는다
MIN_EXEMPTION_REASON = 4


async def _count_attachments(db: AsyncSession, project_id: int, kinds: tuple[str, ...]) -> int:
    return await db.scalar(
        select(func.count(models.ProjectAttachment.id)).where(
            models.ProjectAttachment.project_id == project_id,
            models.ProjectAttachment.kind.in_(kinds),
            models.ProjectAttachment.is_deleted == False,
        )
    ) or 0


async def run_auto_checks(
    db: AsyncSession,
    project: models.Project,
    exemptions: dict | None = None,
) -> list[dict]:
    """
    자동 검사 결과를 반환한다.
    각 항목: {key, label, passed, detail, exemptable, exempted, exemption}
    exemptions 에 사유가 있는 항목은 미충족이어도 '해당 없음'으로 통과시킨다.
    """
    project_id = project.id
    exemptions = exemptions or {}
    checks: list[dict] = []

    # 1) 발주 근거 문서 — 쿠팡 Ariba PO(.htm)뿐 아니라 발주서·계약서 PDF 등도 인정한다
    po_count = await _count_attachments(db, project_id, ("PO",))
    checks.append({
        "key": "PO_ATTACHED",
        "label": "발주 근거 문서 첨부됨 (PO·발주서·계약서)",
        "passed": po_count > 0,
        "detail": f"{po_count}건" if po_count else "첨부 구분 'PO·발주서'로 발주 문서를 올려주세요.",
    })

    # 2) 검수·완료 확인 문서 — 납품설치확인서·납품완료확인서·검수보고서·장비 인수증 등
    #    고객 서명본을 인수인계서로 분류하는 경우도 있어 함께 인정한다
    insp_count = await _count_attachments(db, project_id, ("INSPECTION", "HANDOVER"))
    checks.append({
        "key": "INSPECTION_ATTACHED",
        "label": "검수·완료 확인서 첨부됨",
        "passed": insp_count > 0,
        "detail": f"{insp_count}건" if insp_count else "납품설치·완료확인서, 검수보고서, 인수증 등을 올려주세요.",
    })

    # 3) 납품 품목 — 서버뿐 아니라 파트만 납품한 건도 인정한다
    server_count = await db.scalar(
        select(func.count(models.ServerInventory.id)).where(
            models.ServerInventory.project_id == project_id,
            models.ServerInventory.is_deleted == False,
        )
    ) or 0
    part_count = await db.scalar(
        select(func.count(models.PartInventory.id)).where(
            models.PartInventory.project_id == project_id,
            models.PartInventory.is_deleted == False,
        )
    ) or 0
    # 승인 완료된 파트 출고는 PO 번호로 프로젝트와 연결된다 (표기 차이는 무시)
    usage_count = 0
    po_filter = usage_po_filter(project.po_number)
    if po_filter is not None:
        usage_count = await db.scalar(select(func.count(models.PartUsage.id)).where(po_filter)) or 0
    items = []
    if server_count:
        items.append(f"서버 {server_count}대")
    if part_count or usage_count:
        items.append(f"파트 {part_count + usage_count}건")
    checks.append({
        "key": "HAS_ITEMS",
        "label": "납품 품목 등록됨 (서버 또는 파트)",
        "passed": bool(items),
        "detail": ", ".join(items) if items else "납품목록·파트재고에서 이 프로젝트로 품목을 지정해 주세요.",
    })

    # 4) 승인 대기 중인 파트 출고 없음 — 실제로 처리해야 끝나는 일이라 예외 불가
    pending = len(await pending_usage_approvals(db, project.po_number))
    checks.append({
        "key": "NO_PENDING_APPROVALS",
        "label": "승인 대기 중인 파트 출고 없음",
        "passed": pending == 0,
        "detail": "없음" if pending == 0 else f"{pending}건이 결재 대기 중입니다. 먼저 처리해 주세요.",
    })

    # 예외 반영
    for check in checks:
        check["exemptable"] = check["key"] in EXEMPTABLE_CHECKS
        check["exempted"] = False
        check["exemption"] = None
        if check["passed"] or not check["exemptable"]:
            continue
        exemption = exemptions.get(check["key"])
        reason = exemption.get("reason") if isinstance(exemption, dict) else exemption
        if reason and len(str(reason).strip()) >= MIN_EXEMPTION_REASON:
            check["passed"] = True
            check["exempted"] = True
            check["exemption"] = exemption if isinstance(exemption, dict) else {"reason": str(reason).strip()}
            check["detail"] = f"해당 없음 — {str(reason).strip()}"

    return checks


def validate_exemptions(requested: dict | None) -> dict[str, str]:
    """
    요청으로 들어온 예외 {검사키: 사유} 를 검증해 정리한다.
    예외 불가 항목이거나 사유가 너무 짧으면 ValueError.
    """
    cleaned: dict[str, str] = {}
    for key, reason in (requested or {}).items():
        if key not in EXEMPTABLE_CHECKS:
            raise ValueError(f"'{key}' 항목은 예외 처리할 수 없습니다.")
        text = str(reason or "").strip()
        if len(text) < MIN_EXEMPTION_REASON:
            raise ValueError(f"예외 사유를 {MIN_EXEMPTION_REASON}자 이상 입력해 주세요.")
        cleaned[key] = text[:500]
    return cleaned


def evaluate_manual(checklist: dict | None) -> list[dict]:
    """수기 확인 항목의 체크 상태를 반환한다."""
    state = checklist or {}
    return [
        {**item, "checked": bool(state.get(item["key"]))}
        for item in MANUAL_CHECK_ITEMS
    ]


def blocking_reasons(auto_checks: list[dict], manual_items: list[dict]) -> list[str]:
    """완료 처리를 막는 사유 목록 (비어 있으면 완료 가능)."""
    reasons = [c["label"] for c in auto_checks if not c["passed"]]
    reasons += [m["label"] for m in manual_items if not m["checked"]]
    return reasons
