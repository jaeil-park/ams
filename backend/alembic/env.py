"""
Alembic env.py — async 모드 설정
sync DB 세션 사용 금지 → async only (claude_rule.md §4)
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.db.base import Base  # noqa: F401 — 모든 모델의 metadata 가져오기

# app.models 내의 모든 모델을 임포트하여 metadata에 등록되도록 함
from app import models  # noqa: F401

# ─── Alembic Config ──────────────────────────────
config = context.config

# Logging 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL을 settings에서 동적으로 가져오되, configparser 보간법 오류 방지를 위해 %를 %%로 이스케이프
escaped_url = settings.DATABASE_URL.replace("%", "%%")
config.set_main_option("sqlalchemy.url", escaped_url)

# autogenerate용 metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """오프라인 모드 마이그레이션 (SQL 스크립트 생성용)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """마이그레이션 실행 (공통)"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """비동기 엔진으로 마이그레이션 실행"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """온라인 모드 마이그레이션 (비동기)"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
