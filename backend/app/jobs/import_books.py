from __future__ import annotations

import argparse
import os
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="Import book knowledge into OpenViking")
    parser.add_argument("--dir", default="", help="Books directory, default from BOOKS_DIR/settings")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild books namespace and tables before import")
    parser.add_argument(
        "--selected-file",
        action="append",
        default=[],
        help="Selected filename or relative path, repeatable",
    )
    args = parser.parse_args()

    if args.dir:
        os.environ["BOOKS_DIR"] = args.dir

    from app.database import Base, engine, SessionLocal
    import app.models  # noqa: F401
    from app.services.book_import_service import BookImportService
    from app.services.book_import_task_service import book_import_task_tracker

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        service = BookImportService(db)
        task_id, total_files = service.start_import_task(
            rebuild=args.rebuild,
            selected_files=args.selected_file or None,
        )
    finally:
        db.close()

    print(f"[book-import] task={task_id} total_files={total_files} rebuild={args.rebuild}")
    last_line = ""

    while True:
        task = book_import_task_tracker.get(task_id)
        if not task:
            print("[book-import] task not found")
            return 1

        line = (
            f"status={task['status']} stage={task['stage']} overall={task['overall_progress']}% "
            f"files={task['completed_files']}/{task['total_files']} "
            f"chunks={task['completed_chunks']}/{task['total_chunks']} "
            f"ocr_files={task['ocr_used_files']} ocr_pages={task['ocr_pages']}"
        )
        if line != last_line:
            print(f"[book-import] {line}")
            last_line = line

        if task["status"] in {"completed", "partial", "failed"}:
            if task.get("message"):
                print(f"[book-import] message={task['message']}")
            return 0 if task["status"] in {"completed", "partial"} else 1
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
