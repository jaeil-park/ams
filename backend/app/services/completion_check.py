"""
app/services/completion_check.py — 프로젝트 완료 처리 체크리스트

두 종류로 나눈다.
- 자동 검사: AMS가 데이터로 직접 확인할 수 있는 항목. 사람이 체크할 수 없고, 통과해야 완료된다.
- 수기 확인: AMS가 알 수 없는 현장 사실. 담당자가 직접 체크해야 완료된다.

자동 검사를 사람이 체크하게 만들면 '체크는 했지만 실제로는 안 된' 상태가 생기므로 분리한다.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models

# 수기 확인 항목 — 담당자가 직접 체크해야 하는 현장 사실
MANUAL_CHECK_ITEMS = [
    {"key": "FIELD_INSTALL", "label": "현장 설치/검수 완료"},
    {"key": "HANDOVER", "label": "고객사 인수인계 완료"},
    {"key": "NAS_DOCS", "label": "NAS 문서 정리 완료 (견적서·확인서·검수사진)"},
]


async def run_auto_checks(db: AsyncSession, project: models.Project) -> list[dict]:
    """자동 검사 결과를 반환한다. 각 항목: {key, label, passed, detail}"""
    project_id = project.id
    checks: list[dict] = []

    # 1) PO 문서 첨부
    po_count = await db.scalar(
        select(func.count(models.ProjectAttachment.id)).where(
            models.ProjectAttachment.project_id == project_id,
            models.ProjectAttachment.kind == "PO",
            models.ProjectAttachment.is_deleted == False,
        )
    ) or 0
    checks.append({
        "key": "PO_ATTACHED",
        "label": "PO 문서 첨부됨",
        "passed": po_count > 0,
        "detail": f"{po_count}건" if po_count else "PO 문서를 첨부해 주세요.",
    })

    # 2) 검수확인서 첨부
    insp_count = await db.scalar(
        select(func.count(models.ProjectAttachment.id)).where(
            models.ProjectAttachment.project_id == project_id,
            models.ProjectAttachment.kind == "INSPECTION",
            models.ProjectAttachment.is_deleted == False,
        )
    ) or 0
    checks.append({
        "key": "INSPECTION_ATTACHED",
        "label": "검수확인서 첨부됨",
        "passed": insp_count > 0,
        "detail": f"{insp_count}건" if insp_count else "납품설치확인서 등 검수 문서를 첨부해 주세요.",
    })

    # 3) 소속 서버 1대 이상
    server_count = await db.scalar(
        select(func.count(models.ServerInventory.id)).where(
            models.ServerInventory.project_id == project_id,
            models.ServerInventory.is_deleted == False,
        )
    ) or 0
    checks.append({
        "key": "HAS_SERVERS",
        "label": "소속 서버가 1대 이상 등록됨",
        "passed": server_count > 0,
        "detail": f"{server_count}대" if server_count else "납품목록에서 이 프로젝트로 서버를 지정해 주세요.",
    })

    # 4) 승인 대기 중인 파트 출고 없음
    #    파트 출고 요청은 payload.po_number 로 프로젝트와 연결된다.
    pending = 0
    if project.po_number:
        result = await db.execute(
            select(models.Approval).where(
                models.Approval.status == "PENDING",
                models.Approval.resource_type == "PART_USAGE",
            )
        )
        pending = sum(
            1 for a in result.scalars().all()
            if (a.payload or {}).get("po_number") == project.po_number
        )
    checks.append({
        "key": "NO_PENDING_APPROVALS",
        "label": "승인 대기 중인 파트 출고 없음",
        "passed": pending == 0,
        "detail": "없음" if pending == 0 else f"{pending}건이 결재 대기 중입니다. 먼저 처리해 주세요.",
    })

    return checks


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
