from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.auth import hash_password
from app.config import get_settings
from app.database import SessionLocal
from app.errors import logger
from app.models.user import User


def _table_exists(engine: Engine, table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def _column_exists(engine: Engine, table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return False
    return any(col.get("name") == column_name for col in inspector.get_columns(table_name))


def _ensure_column(engine: Engine, table_name: str, column_ddl: str, column_name: str) -> None:
    if not _table_exists(engine, table_name):
        return
    if _column_exists(engine, table_name, column_name):
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}"))
    logger.info("Schema patch: added column %s.%s", table_name, column_name)


def _ensure_index(engine: Engine, index_sql: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(index_sql))


def _safe_exec(engine: Engine, sql: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(sql))


def _ensure_initial_admin() -> None:
    settings = get_settings()
    username = (settings.initial_admin_username or "").strip()
    password = (settings.initial_admin_password or "").strip()
    if not username or not password:
        return
    if len(password) < 8:
        logger.warning("Initial admin password too short; skipped")
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return
        admin_user = User(
            account_id=1,
            username=username,
            password_hash=hash_password(password),
            display_name=settings.initial_admin_display_name or username,
            department=settings.initial_admin_department or "admin",
            role="admin",
        )
        db.add(admin_user)
        db.commit()
        logger.info("Initial admin user created: %s", username)
    except Exception as e:
        db.rollback()
        logger.warning("Initial admin bootstrap failed: %s", e)
    finally:
        db.close()


def ensure_account_schema(engine: Engine) -> None:
    # 1) Add account_id columns (idempotent)
    column_targets = {
        "users": "account_id INTEGER DEFAULT 1",
        "materials": "account_id INTEGER DEFAULT 1",
        "chat_sessions": "account_id INTEGER DEFAULT 1",
        "chat_messages": "account_id INTEGER DEFAULT 1",
        "session_drafts": "account_id INTEGER DEFAULT 1",
        "generated_documents": "account_id INTEGER DEFAULT 1",
        "user_preferences": "account_id INTEGER DEFAULT 1",
        "writing_habits": "account_id INTEGER DEFAULT 1",
        "style_profiles": "account_id INTEGER DEFAULT 1",
        "book_sources": "account_id INTEGER DEFAULT 1",
        "book_style_rules": "account_id INTEGER DEFAULT 1",
    }
    for table_name, column_ddl in column_targets.items():
        _ensure_column(engine, table_name, column_ddl, "account_id")

    # 2) Ensure default account row exists.
    if _table_exists(engine, "accounts"):
        _safe_exec(
            engine,
            (
                "INSERT INTO accounts (id, code, name, status, created_at, updated_at) "
                "SELECT 1, 'default', 'default', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
                "WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE id = 1)"
            ),
        )

    # 3) Backfill account_id by relation (best effort, idempotent).
    if _table_exists(engine, "users") and _column_exists(engine, "users", "account_id"):
        _safe_exec(engine, "UPDATE users SET account_id = COALESCE(account_id, 1)")

    if _table_exists(engine, "materials"):
        _safe_exec(
            engine,
            (
                "UPDATE materials SET account_id = COALESCE(account_id, "
                "(SELECT account_id FROM users WHERE users.id = materials.user_id), 1)"
            ),
        )

    if _table_exists(engine, "chat_sessions"):
        _safe_exec(
            engine,
            (
                "UPDATE chat_sessions SET account_id = COALESCE(account_id, "
                "(SELECT account_id FROM users WHERE users.id = chat_sessions.user_id), 1)"
            ),
        )

    if _table_exists(engine, "chat_messages"):
        _safe_exec(
            engine,
            (
                "UPDATE chat_messages SET account_id = COALESCE(account_id, "
                "(SELECT account_id FROM chat_sessions WHERE chat_sessions.id = chat_messages.session_id), 1)"
            ),
        )

    if _table_exists(engine, "session_drafts"):
        _safe_exec(
            engine,
            (
                "UPDATE session_drafts SET account_id = COALESCE(account_id, "
                "(SELECT account_id FROM chat_sessions WHERE chat_sessions.id = session_drafts.session_id), "
                "(SELECT account_id FROM users WHERE users.id = session_drafts.user_id), 1)"
            ),
        )

    if _table_exists(engine, "generated_documents"):
        _safe_exec(
            engine,
            (
                "UPDATE generated_documents SET account_id = COALESCE(account_id, "
                "(SELECT account_id FROM users WHERE users.id = generated_documents.user_id), 1)"
            ),
        )

    if _table_exists(engine, "user_preferences"):
        _safe_exec(
            engine,
            (
                "UPDATE user_preferences SET account_id = COALESCE(account_id, "
                "(SELECT account_id FROM users WHERE users.id = user_preferences.user_id), 1)"
            ),
        )

    if _table_exists(engine, "writing_habits"):
        _safe_exec(
            engine,
            (
                "UPDATE writing_habits SET account_id = COALESCE(account_id, "
                "(SELECT account_id FROM users WHERE users.id = writing_habits.user_id), 1)"
            ),
        )

    if _table_exists(engine, "style_profiles"):
        _safe_exec(engine, "UPDATE style_profiles SET account_id = COALESCE(account_id, 1)")

    if _table_exists(engine, "book_sources"):
        _safe_exec(engine, "UPDATE book_sources SET account_id = COALESCE(account_id, 1)")

    if _table_exists(engine, "book_style_rules"):
        _safe_exec(
            engine,
            (
                "UPDATE book_style_rules SET account_id = COALESCE(account_id, "
                "(SELECT account_id FROM book_sources WHERE book_sources.id = book_style_rules.source_id), 1)"
            ),
        )

    # 4) Ensure indexes
    _ensure_index(engine, "CREATE INDEX IF NOT EXISTS ix_users_account_id ON users(account_id)")
    _ensure_index(engine, "CREATE INDEX IF NOT EXISTS ix_materials_account_id ON materials(account_id)")
    _ensure_index(engine, "CREATE INDEX IF NOT EXISTS ix_chat_sessions_account_id ON chat_sessions(account_id)")
    _ensure_index(engine, "CREATE INDEX IF NOT EXISTS ix_generated_documents_account_id ON generated_documents(account_id)")
    _ensure_index(engine, "CREATE INDEX IF NOT EXISTS ix_book_sources_account_id ON book_sources(account_id)")
    _ensure_index(engine, "CREATE INDEX IF NOT EXISTS ix_book_style_rules_account_id ON book_style_rules(account_id)")

    # Rebuild legacy unique index for book_sources -> account scoped.
    try:
        _safe_exec(engine, "DROP INDEX IF EXISTS uq_book_sources_source_hash")
    except Exception:
        pass
    _ensure_index(
        engine,
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_book_sources_account_source_hash ON book_sources(account_id, source_hash)",
    )

    logger.info("Schema patch: account isolation bootstrap completed")
    _ensure_initial_admin()
