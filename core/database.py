from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = Path('data') / 'weibo.db'
        db_path = Path(db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if not str(db_path).startswith(str(Path.cwd().resolve())):
            raise ValueError('Database path must be within current working directory')
        self.db_path = str(db_path)
        self.connection = None
        self.cursor = None
        self._initialize_database()

    def _initialize_database(self):
        self.connection = sqlite3.connect(self.db_path, timeout=30.0)
        self.connection.execute('PRAGMA foreign_keys = ON')
        self.connection.execute('PRAGMA journal_mode = WAL')
        self.cursor = self.connection.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS weibo (
                id INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_weibo_id ON weibo(id)
        ''')
        try:
            self.cursor.execute('PRAGMA table_info(weibo)')
            cols = [row[1] for row in self.cursor.fetchall()]
            if 'processed_at' not in cols:
                self.cursor.execute('ALTER TABLE weibo ADD COLUMN processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except Exception:
            pass
        self.connection.commit()
        logger.info(f'Database initialized: {self.db_path}')

    def check_and_add_id(self, weibo_id: int) -> bool:
        try:
            if not isinstance(weibo_id, int) or weibo_id <= 0:
                return False
            self.cursor.execute('SELECT id FROM weibo WHERE id = ?', (weibo_id,))
            if self.cursor.fetchone() is None:
                try:
                    self.cursor.execute('INSERT INTO weibo (id, processed_at) VALUES (?, CURRENT_TIMESTAMP)', (weibo_id,))
                except sqlite3.OperationalError:
                    self.cursor.execute('INSERT INTO weibo (id) VALUES (?)', (weibo_id,))
                self.connection.commit()
                return True
            return False
        except Exception as e:
            logger.error(f'Database operation error: {e}')
            return False

    def add_all_ids(self, weibo_items: List[Dict[str, Any]]):
        try:
            valid_ids = []
            for item in weibo_items:
                if isinstance(item, dict) and 'id' in item and isinstance(item['id'], int) and item['id'] > 0:
                    valid_ids.append(item['id'])
            if valid_ids:
                try:
                    self.cursor.executemany('INSERT OR IGNORE INTO weibo (id, processed_at) VALUES (?, CURRENT_TIMESTAMP)', [(i,) for i in valid_ids])
                except sqlite3.OperationalError:
                    self.cursor.executemany('INSERT OR IGNORE INTO weibo (id) VALUES (?)', [(i,) for i in valid_ids])
                self.connection.commit()
                logger.info(f'Added {len(valid_ids)} weibo IDs to database')
        except Exception as e:
            logger.error(f'Error adding IDs to database: {e}')

    def cleanup_old_records(self, days: int = 30):
        try:
            self.cursor.execute(f"DELETE FROM weibo WHERE processed_at < datetime('now', '-{int(days)} days')")
            deleted_count = self.cursor.rowcount
            self.connection.commit()
            if deleted_count > 0:
                logger.info(f'Cleaned up {deleted_count} old records')
        except Exception as e:
            logger.error(f'Error cleaning up old records: {e}')

    def get_recent_ids(self, limit: int = 100) -> List[int]:
        try:
            self.cursor.execute('SELECT id FROM weibo ORDER BY processed_at DESC LIMIT ?', (int(limit),))
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f'Error getting recent IDs: {e}')
            return []

    def close(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info('Database connection closed')
        except Exception as e:
            logger.error(f'Error closing database: {e}')


