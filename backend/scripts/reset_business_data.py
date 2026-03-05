"""Reset business data for full doc-type rewrite rollout.

This script preserves the `users` table and clears all business tables/files.
Default mode is dry-run. Use `--execute` to perform actual deletion.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

import httpx
from sqlalchemy import text


BUSINESS_TABLES = [
    "chat_messages",
    "session_drafts",
    "generated_documents",
    "chat_sessions",
    "materials",
    "user_preferences",
    "writing_habits",
    "style_profiles",
]

OPENVIKING_URIS = [
    "viking://resources/materials",
    "viking://session/default",
]


def _bootstrap_import_path() -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))
    return backend_root


def _count_rows(session, table: str) -> int:
    return int(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


def _clear_database(execute: bool) -> None:
    from app.database import SessionLocal  # noqa: PLC0415

    with SessionLocal() as session:
        counts = {table: _count_rows(session, table) for table in BUSINESS_TABLES}
        total = sum(counts.values())
        print(f"[DB] Rows to clear: {total}")
        for table in BUSINESS_TABLES:
            print(f"  - {table}: {counts[table]}")

        if not execute:
            print("[DB] Dry-run mode, no rows deleted.")
            return

        for table in BUSINESS_TABLES:
            session.execute(text(f"DELETE FROM {table}"))
        session.commit()
        print("[DB] Business tables cleared.")


def _clear_directory(path: Path, execute: bool) -> int:
    if not path.exists():
        return 0

    removed = 0
    for item in path.iterdir():
        removed += 1
        if not execute:
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)
    return removed


def _clear_files(execute: bool) -> None:
    from app.config import get_settings  # noqa: PLC0415

    settings = get_settings()
    targets = [
        Path(settings.upload_dir),
        Path(settings.export_dir),
    ]

    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        removed = _clear_directory(target, execute=execute)
        print(f"[FS] {target} -> {removed} entries {'removed' if execute else 'to remove'}")


async def _clear_openviking(execute: bool) -> None:
    from app.config import get_settings  # noqa: PLC0415

    settings = get_settings()
    headers = {}
    if settings.openviking_root_api_key:
        headers["Authorization"] = f"Bearer {settings.openviking_root_api_key}"

    if not execute:
        for uri in OPENVIKING_URIS:
            print(f"[OV] {uri} -> to remove")
        print("[OV] Dry-run mode, no resources deleted.")
        return

    base_url = settings.openviking_server_url.rstrip("/")
    for uri in OPENVIKING_URIS:
        try:
            # Use one client per request to avoid broken keep-alive reuse.
            async with httpx.AsyncClient(base_url=base_url, timeout=30.0, headers=headers) as client:
                # New API: DELETE /api/v1/fs?uri=...&recursive=true
                resp = await client.delete("/api/v1/fs", params={"uri": uri, "recursive": True})
                if resp.status_code == 404:
                    # Backward-compatible fallback for older OpenViking API.
                    resp = await client.post("/api/v1/fs/rm", json={"uri": uri, "recursive": True})

            if resp.status_code >= 400:
                body = (resp.text or "").strip()
                # New OV may return 500 + "not found" when target path is absent.
                if "not found" in body.lower():
                    print(f"[OV] Already empty {uri}")
                else:
                    print(f"[OV] Failed to remove {uri}: {resp.status_code} {body}")
            else:
                print(f"[OV] Removed {uri}")
        except Exception as exc:  # pragma: no cover - best effort cleanup
            print(f"[OV] Failed to remove {uri}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset writer business data (preserve users).")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform deletion. Without this flag, runs in dry-run mode.",
    )
    parser.add_argument(
        "--skip-openviking",
        action="store_true",
        help="Skip OpenViking resource cleanup.",
    )
    args = parser.parse_args()

    _bootstrap_import_path()

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"== Reset business data ({mode}) ==")
    _clear_database(execute=args.execute)
    _clear_files(execute=args.execute)
    if args.skip_openviking:
        print("[OV] Skipped by flag.")
    else:
        asyncio.run(_clear_openviking(execute=args.execute))
    print("== Done ==")


if __name__ == "__main__":
    main()
