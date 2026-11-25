"""
연동 API 테스트 (DB 불필요 — 세션을 가짜로 바꾼다)
실행: cd backend && python -m pytest tests/test_integrations.py -q
"""

from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app import models
from app.api.v1.endpoints import integrations
from app.core.config import settings
from app.core.deps import get_db

TOKEN = "t" * 40
URL = "/api/v1/integrations/warranties"


def _row(serial: str, end: date, **kw) -> models.WarrantyLookup:
    return models.WarrantyLookup(serial_tag=serial, vendor="DELL", status="DONE", end_date=end,
                                 updated_at=datetime(2026, 11, 25, tzinfo=timezone.utc), **kw)


class FakeDb:
    def __init__(self, rows):
        self.rows, self.sql = rows, ""

    async def execute(self, q):
        self.sql = str(q.compile(dialect=postgresql.dialect()))
        return self

    def scalars(self):
        return self

    def all(self):
        return self.rows


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(settings, "INTEGRATION_TOKEN", TOKEN)
    db = FakeDb([
        _row("abc1234", date(2028, 3, 10), start_date=date(2025, 2, 25), service_level="ProSupport",
             product_name="PowerEdge R660", requested_by_id=7, detail={"x": 1}),
        _row("ABC1234", date(2020, 1, 1)),   # 같은 시리얼의 옛 기록
    ])
    app = FastAPI()
    app.include_router(integrations.router, prefix="/api/v1/integrations")
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    c.db = db
    return c


def test_latest_per_serial_and_no_extra_fields(api):
    data = api.get(URL, headers={"X-Integration-Token": TOKEN}).json()["data"]
    assert data == [{"serial": "ABC1234", "vendor": "DELL", "start_date": "2025-02-25", "end_date": "2028-03-10",
                     "service_level": "ProSupport", "product_name": "PowerEdge R660",
                     "looked_up_at": "2026-11-25T00:00:00+00:00"}]
    assert "end_date IS NOT NULL" in api.db.sql and "is_deleted = false" in api.db.sql


@pytest.mark.parametrize("headers", [{}, {"X-Integration-Token": "wrong"}, {"Authorization": f"Bearer {TOKEN}"}])
def test_wrong_token(api, headers):
    assert api.get(URL, headers=headers).status_code == 401


@pytest.mark.parametrize("configured", ["", "   ", "short"])
def test_closed_without_strong_token(api, monkeypatch, configured):
    monkeypatch.setattr(settings, "INTEGRATION_TOKEN", configured)
    assert api.get(URL, headers={"X-Integration-Token": configured}).status_code == 403


def test_router_registered():
    from app.api.v1.router import api_router
    assert any(r.path == "/integrations/warranties" for r in api_router.routes)
