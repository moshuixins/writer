from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

import app.models  # noqa: F401

from app.database import Base, engine
from app.errors import logger
from app.schema_patch import apply_account_schema_patch

APP_TABLE_NAMES = tuple(Base.metadata.tables.keys())


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parent.parent
    config = Config(str(backend_root / 'alembic.ini'))
    config.set_main_option('script_location', str(backend_root / 'alembic'))
    config.set_main_option('sqlalchemy.url', database_url)
    return config


def _has_alembic_version_table(target_engine: Engine) -> bool:
    return 'alembic_version' in inspect(target_engine).get_table_names()


def _has_existing_app_tables(target_engine: Engine) -> bool:
    existing = set(inspect(target_engine).get_table_names())
    return bool(existing.intersection(APP_TABLE_NAMES))


def run_database_migrations(
    target_engine: Engine | None = None,
    *,
    allow_legacy_bootstrap: bool = True,
) -> None:
    target_engine = target_engine or engine
    database_url = target_engine.url.render_as_string(hide_password=False)
    config = _alembic_config(database_url)

    if _has_alembic_version_table(target_engine):
        command.upgrade(config, 'head')
        logger.info('Database migrated to Alembic head')
        return

    if allow_legacy_bootstrap and _has_existing_app_tables(target_engine):
        Base.metadata.create_all(bind=target_engine)
        apply_account_schema_patch(target_engine)
        command.stamp(config, 'head')
        logger.info('Legacy schema normalized and stamped to Alembic head')
        return

    command.upgrade(config, 'head')
    logger.info('Database migrated to Alembic head')
