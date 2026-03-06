from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TARGET_SUFFIXES = {
    '.py',
    '.ts',
    '.tsx',
    '.js',
    '.jsx',
    '.vue',
    '.json',
    '.md',
    '.yml',
    '.yaml',
    '.sh',
    '.env',
    '.example',
    '.conf',
}
SKIP_DIRS = {
    '.git',
    '.qoder',
    '.claude',
    'node_modules',
    'dist',
    'dist-test',
    '__pycache__',
    '.pnpm-store',
}
SKIP_FILES: set[str] = set()


def should_check(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if rel in SKIP_FILES:
        return False
    return any(str(path).endswith(suffix) for suffix in TARGET_SUFFIXES)


def iter_repo_files(root: Path):
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if should_check(path, root):
            yield path


def iter_changed_files(root: Path):
    result = subprocess.run(
        ['git', 'status', '--short', '--untracked-files=all'],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        yield from iter_repo_files(root)
        return

    seen: set[Path] = set()
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rel = line[3:].strip().replace('\\', '/')
        path = (root / rel).resolve()
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if should_check(path, root) and path not in seen:
            seen.add(path)
            yield path


def fix_bom(paths: list[Path]) -> list[Path]:
    fixed: list[Path] = []
    for path in paths:
        data = path.read_bytes()
        if not data.startswith(b'\xef\xbb\xbf'):
            continue
        text = data.decode('utf-8-sig')
        path.write_text(text, encoding='utf-8')
        fixed.append(path)
    return fixed


def scan(paths: list[Path], root: Path) -> list[str]:
    invalid: list[str] = []
    for path in paths:
        data = path.read_bytes()
        rel = path.relative_to(root)
        if data.startswith(b'\xef\xbb\xbf'):
            invalid.append(f'BOM: {rel}')
            continue
        try:
            data.decode('utf-8')
        except UnicodeDecodeError as exc:
            invalid.append(f'UTF8: {rel} ({exc})')
    return invalid


def main() -> int:
    parser = argparse.ArgumentParser(description='Check repository text encoding')
    parser.add_argument('--all', action='store_true', help='Scan all repository text files instead of changed files only')
    parser.add_argument('--fix-bom', action='store_true', help='Rewrite UTF-8 BOM files as UTF-8 without BOM before checking')
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    paths = list(iter_repo_files(root) if args.all else iter_changed_files(root))

    if args.fix_bom:
        fixed = fix_bom(paths)
        if fixed:
            print('Removed BOM from:')
            for item in fixed:
                print(f' - {item.relative_to(root)}')

    invalid = scan(paths, root)

    if invalid:
        print('Text encoding check failed:')
        for item in invalid:
            print(f' - {item}')
        return 1

    scope = 'all files' if args.all else 'changed files'
    print(f'Text encoding check passed ({scope})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
