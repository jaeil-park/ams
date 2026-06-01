"""
app/api/v1/router.py — API v1 통합 라우터 구성
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    customers,
    projects,
    inventory,
    parts,
    approvals,
    addresses,
    warranty,
    dashboard,
    audit_logs,
    search,
    users,
)

api_router = APIRouter()

# 각 도메인별 라우터 바인딩
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(parts.router, prefix="/parts", tags=["parts"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(addresses.router, prefix="/addresses", tags=["addresses"])
api_router.include_router(warranty.router, prefix="/warranty", tags=["warranty"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

