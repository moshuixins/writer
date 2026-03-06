from __future__ import annotations

from datetime import datetime, timezone

from app.auth import hash_password
from app.config import get_settings
from app.database import SessionLocal
from app.errors import logger
from app.models.book_import_task import BookImportTask
from app.models.user import User
from app.services.rbac_service import RBACService


def ensure_initial_admin() -> None:
    settings = get_settings()
    username = (settings.initial_admin_username or '').strip()
    password = (settings.initial_admin_password or '').strip()
    if not username or not password:
        return
    if len(password) < 8:
        logger.warning('Initial admin password too short; skipped')
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
            department=settings.initial_admin_department or 'admin',
            role='admin',
        )
        db.add(admin_user)
        db.commit()
        logger.info('Initial admin user created: %s', username)
    except Exception as exc:
        db.rollback()
        logger.warning('Initial admin bootstrap failed: %s', exc)
    finally:
        db.close()


def bootstrap_rbac() -> None:
    db = SessionLocal()
    try:
        service = RBACService(db)
        service.ensure_permissions()
        service.ensure_all_accounts_system_roles()
        service.backfill_user_roles_from_legacy()
        db.commit()
        logger.info('Runtime bootstrap: RBAC bootstrap completed')
    except Exception as exc:
        db.rollback()
        logger.warning('RBAC bootstrap failed: %s', exc)
    finally:
        db.close()


def mark_interrupted_book_tasks() -> None:
    db = SessionLocal()
    try:
        rows = (
            db.query(BookImportTask)
            .filter(BookImportTask.status.in_(['pending', 'running']))
            .all()
        )
        if not rows:
            return
        now = datetime.now(timezone.utc)
        for row in rows:
            row.status = 'interrupted'
            row.stage = '已中断'
            row.message = row.message or '服务重启导致任务中断'
            row.finished_at = now
        db.commit()
        logger.info('Runtime bootstrap: marked %s interrupted book import tasks', len(rows))
    except Exception as exc:
        db.rollback()
        logger.warning('Book import task recovery failed: %s', exc)
    finally:
        db.close()


def run_runtime_bootstrap_tasks() -> None:
    ensure_initial_admin()
    bootstrap_rbac()
    mark_interrupted_book_tasks()
