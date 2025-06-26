import sqlite3
import secrets
import time
from typing import List, Dict

class TokenSystem:
    """Simple token and user management backed by SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def init_db(self) -> None:
        """Ensure required tables exist."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            expires INTEGER
        )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS tokens (
            user TEXT PRIMARY KEY,
            tokens INTEGER DEFAULT 0
        )"""
        )
        conn.commit()
        conn.close()

    def create_user(self, ttl: int = 24 * 3600) -> (str, int):
        """Return a new user id valid for ``ttl`` seconds."""
        user_id = secrets.token_hex(8)
        expires = int(time.time()) + ttl
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('INSERT INTO users(id, expires) VALUES(?, ?)', (user_id, expires))
        c.execute('INSERT INTO tokens(user, tokens) VALUES(?, 0) ON CONFLICT(user) DO NOTHING', (user_id,))
        conn.commit()
        conn.close()
        return user_id, expires

    def valid_user(self, user_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT expires FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        conn.close()
        return bool(row and row[0] > int(time.time()))

    def add_tokens(self, user: str, amount: int) -> bool:
        if amount <= 0:
            return False
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            'INSERT INTO tokens(user, tokens) VALUES(?, ?) '
            'ON CONFLICT(user) DO UPDATE SET tokens = tokens + ?',
            (user, amount, amount)
        )
        conn.commit()
        conn.close()
        return True

    def spend_tokens(self, user: str, amount: int) -> bool:
        if amount <= 0:
            return False
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT tokens FROM tokens WHERE user = ?', (user,))
        row = c.fetchone()
        balance = row[0] if row else 0
        if balance < amount:
            conn.close()
            return False
        c.execute('UPDATE tokens SET tokens = tokens - ? WHERE user = ?', (amount, user))
        conn.commit()
        conn.close()
        return True

    def transfer_tokens(self, from_user: str, to_user: str, amount: int) -> bool:
        if not self.spend_tokens(from_user, amount):
            return False
        self.add_tokens(to_user, amount)
        return True

    def get_balances(self) -> List[Dict[str, int]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT * FROM tokens').fetchall()
        conn.close()
        return [dict(row) for row in rows]
