"""
파트 출고 ↔ 프로젝트 PO 연결 테스트 (메모리 SQLite)
실행: cd backend && python -m pytest tests/test_po_link.py -q
"""

import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import models
from app.db.base import Base
from app.services.completion_check import run_auto_checks
from app.services.po_link import normalize_po, pending_usage_approvals, relink_po, usage_po_filter

TABLES = ["audit_logs", "users", "customers", "projects", "part_inventories", "part_usages", "approvals",
          "server_inventories", "project_attachments"]


def run(coro_fn):
    async def main():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: Base.metadata.create_all(
                c, tables=[Base.metadata.tables[t] for t in TABLES if t in Base.metadata.tables]))
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            db.add_all([
                models.User(id=1, email="a@x", password_hash="x", name="담당자"),
                models.Customer(id=1, code="C1", name="쿠팡_물리보안"),
                models.PartInventory(id=1, model="Broadcom 57414", qty=5),
            ])
            await db.commit()
            result = await coro_fn(db)
        await engine.dispose()
        return result
    return asyncio.run(main())


def _usage(po):
    return models.PartUsage(part_id=1, customer_id=1, used_date=date(2026, 11, 27), qty=1, po_number=po)


def _pending(po):
    return models.Approval(requester_id=1, resource_type="PART_USAGE", resource_id=1, status="PENDING",
                           payload={"qty": 1, "customer_id": 1, "po_number": po})


def test_normalize_po():
    assert normalize_po(" po 403813 ") == "PO403813"
    assert normalize_po("PO403813\t") == "PO403813"
    assert normalize_po("") is None and normalize_po(None) is None and normalize_po("   ") is None


def test_usage_registered_before_project_links_regardless_of_spelling():
    async def body(db):
        # PO 프로젝트가 없을 때 수기 번호로 먼저 불출 (표기가 제각각)
        db.add_all([_usage("po403813"), _usage("PO 403813"), _usage("PO999999"), _pending("Po403813 ")])
        await db.commit()
        # 나중에 같은 PO 의 프로젝트가 등록됨
        project = models.Project(po_number="PO403813", name="물리보안 서버", customer_id=1)
        db.add(project)
        await db.commit()

        linked = (await db.execute(select(models.PartUsage).where(usage_po_filter(project.po_number)))).scalars().all()
        pending = await pending_usage_approvals(db, project.po_number)
        checks = {c["key"]: c for c in await run_auto_checks(db, project)}
        return len(linked), len(pending), checks

    linked, pending, checks = run(body)
    assert linked == 2                     # PO999999 는 제외
    assert pending == 1
    assert checks["HAS_ITEMS"]["passed"] and "파트 2건" in checks["HAS_ITEMS"]["detail"]
    assert not checks["NO_PENDING_APPROVALS"]["passed"]


def test_relink_moves_usages_and_pending_from_temporary_number():
    async def body(db):
        db.add_all([_usage("NOPO-261127-01"), _usage("nopo-261127-01"), _usage("PO111111"),
                    _pending("NOPO-261127-01"), _pending("PO111111")])
        await db.commit()
        moved = await relink_po(db, "NOPO-261127-01", "po 403813")
        await db.commit()
        usage_pos = sorted(u.po_number for u in (await db.execute(select(models.PartUsage))).scalars().all())
        approval_pos = sorted(a.payload["po_number"] for a in (await db.execute(select(models.Approval))).scalars().all())
        return moved, usage_pos, approval_pos

    moved, usage_pos, approval_pos = run(body)
    assert moved == {"usages": 2, "pending": 1}
    assert usage_pos == ["PO111111", "PO403813", "PO403813"]
    assert approval_pos == ["PO111111", "PO403813"]


def test_relink_with_empty_numbers_does_nothing():
    async def body(db):
        db.add(_usage(None))
        await db.commit()
        return await relink_po(db, None, "PO1"), await relink_po(db, "PO1", "")

    assert run(body) == ({"usages": 0, "pending": 0}, {"usages": 0, "pending": 0})


def test_project_endpoints_list_usages_and_relink_on_po_change():
    import httpx
    from fastapi import FastAPI

    from app.api.v1.endpoints import projects
    from app.core.deps import get_current_user, get_db

    async def body(db):
        project = models.Project(po_number="NOPO-261127-01", name="선지원 건", customer_id=1)
        db.add_all([project, _usage("nopo-261127-01"), _pending("NOPO-261127-01")])
        await db.commit()

        app = FastAPI()
        app.include_router(projects.router, prefix="/projects")
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: models.User(id=1, email="a@x", name="담당자")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            before = (await c.get(f"/projects/{project.id}/part-usages")).json()["data"]
            r = await c.patch(f"/projects/{project.id}", json={"po_number": "PO403813"})
            after = (await c.get(f"/projects/{project.id}/part-usages")).json()["data"]
        return before, r.status_code, after

    before, code, after = run(body)
    assert (len(before["usages"]), len(before["pending"])) == (1, 1)
    assert before["usages"][0]["part_model"] == "Broadcom 57414"
    assert before["pending"][0]["requester_name"] == "담당자"
    assert code == 200
    assert after["po_number"] == "PO403813"
    assert after["usages"][0]["po_number"] == "PO403813" and len(after["pending"]) == 1
