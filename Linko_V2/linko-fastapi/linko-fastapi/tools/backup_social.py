"""Safely back up Linko's SQLite social database with SQLite's online backup API.

Usage (from backend directory): python tools/backup_social.py
Use LINKO_SOCIAL_DB to override the source; LINKO_BACKUP_DIR for destination.
"""
from __future__ import annotations

import os
from contextlib import closing
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('LINKO_SOCIAL_DB', str(BASE / 'linko_social.db'))).expanduser()
DEST_DIR = Path(os.environ.get('LINKO_BACKUP_DIR', str(BASE / 'backups'))).expanduser()


def run(source: Path = SOURCE, destination_dir: Path = DEST_DIR) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f'Chưa tìm thấy SQLite tại {source}. Hãy chạy backend trước.')
    destination_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    destination = destination_dir / f'linko_social_{stamp}.db'
    try:
        with closing(sqlite3.connect(f'file:{source.resolve().as_posix()}?mode=ro', uri=True)) as original:
            with closing(sqlite3.connect(destination)) as snapshot:
                original.backup(snapshot)
                result = snapshot.execute('PRAGMA integrity_check').fetchone()[0]
                if result != 'ok':
                    raise RuntimeError(f'SQLite integrity check failed: {result}')
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


if __name__ == '__main__':
    try:
        created = run()
        print(f'[Linko V7] Sao luu thanh cong: {created}')
    except (OSError, sqlite3.Error, RuntimeError) as exc:
        print(f'[Linko V7] Sao luu that bai: {exc}', file=sys.stderr)
        raise SystemExit(1)
