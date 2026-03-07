from __future__ import annotations

import logging
import os
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime

from extensions import db
from models import BackupLog
from config import BACKUP_DIR

logger = logging.getLogger(__name__)

_db_user = os.environ.get('DB_USER', '')
_db_pass = os.environ.get('DB_PASSWORD', '')
_db_host = os.environ.get('DB_HOST', 'localhost')
_db_port = os.environ.get('DB_PORT', '3306')
_db_name = os.environ.get('DB_NAME', 'zitatdatenbank')


def _backup_log(level: str, message: str) -> None:
    db.session.add(BackupLog(level=level, message=message))
    db.session.commit()
    # Prune old log entries (keep 500)
    count = db.session.query(BackupLog).count()
    if count > 500:
        oldest = db.session.query(BackupLog).order_by(BackupLog.ran_at.asc()).limit(count - 500).all()
        for entry in oldest:
            db.session.delete(entry)
        db.session.commit()


def run_backup() -> tuple[bool, str]:
    """Create a full backup tar.gz. Returns (True, filename) or (False, error_msg)."""
    ts = datetime.now().strftime('%Y_%m_%d_%H-%M-%S')
    filename = f'zitate_backup_{ts}.tar.gz'
    dest = os.path.join(BACKUP_DIR, filename)
    os.makedirs(BACKUP_DIR, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            dump_path = os.path.join(tmp, 'dump.sql')
            with open(dump_path, 'wb') as dump_file:
                result = subprocess.run(
                    ['mysqldump', '-h', _db_host, '-P', _db_port,
                     f'-u{_db_user}', f'-p{_db_pass}',
                     '--add-drop-table', _db_name],
                    stdout=dump_file, stderr=subprocess.PIPE, timeout=300
                )
            if result.returncode != 0:
                err = result.stderr.decode(errors='replace')[:300]
                _backup_log('ERROR', f'mysqldump failed: {err}')
                return False, 'Database backup failed'

            with tarfile.open(dest, 'w:gz') as tar:
                tar.add(dump_path, arcname='dump.sql')

        _backup_log('SUCCESS', f'Backup created: {filename}')
        logger.info('Backup created: %s', filename)
        return True, filename

    except Exception as e:
        err = str(e)[:300]
        _backup_log('ERROR', err)
        logger.error('Backup failed: %s', err)
        if os.path.exists(dest):
            os.remove(dest)
        return False, err


def restore_backup(filename: str) -> tuple[bool, str]:
    """Restore database from a backup file. Returns (True, msg) or (False, error)."""
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        return False, 'Backup file not found'

    try:
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(filepath, 'r:gz') as tar:
                # Only extract expected files to prevent path traversal
                for member in tar.getmembers():
                    if member.name not in ('dump.sql', '.env') or '..' in member.name:
                        continue
                    tar.extract(member, tmp)

            dump_path = os.path.join(tmp, 'dump.sql')
            if not os.path.exists(dump_path):
                return False, 'No dump.sql found in backup'

            with open(dump_path, 'rb') as dump_file:
                result = subprocess.run(
                    ['mariadb', '-h', _db_host, '-P', _db_port,
                     f'-u{_db_user}', f'-p{_db_pass}', _db_name],
                    stdin=dump_file,
                    stderr=subprocess.PIPE, timeout=300
                )
            if result.returncode != 0:
                err = result.stderr.decode(errors='replace')[:300]
                _backup_log('ERROR', 'Restore failed')
                return False, 'Database restore failed'

        _backup_log('SUCCESS', f'Restored from: {filename}')
        return True, f'Restored from {filename}'

    except Exception as e:
        err = str(e)[:300]
        _backup_log('ERROR', f'Restore error: {err}')
        return False, err


def list_backups() -> list[dict[str, str | int | datetime]]:
    """Return list of backup files, newest first."""
    backups: list[dict] = []
    if os.path.exists(BACKUP_DIR):
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if re.match(r'^zitate_backup_[\d_-]+\.tar\.gz$', f):
                fpath = os.path.join(BACKUP_DIR, f)
                stat = os.stat(fpath)
                backups.append({
                    'filename': f,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                })
    return backups


def delete_backup_file(filename: str) -> bool:
    """Delete a backup file. Returns True if deleted."""
    filepath = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(filepath) and re.match(r'^zitate_backup_[\d_-]+\.tar\.gz$', filename):
        os.remove(filepath)
        _backup_log('INFO', f'Deleted backup: {filename}')
        return True
    return False
