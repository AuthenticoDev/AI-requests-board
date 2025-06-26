import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from tokens import TokenSystem


def load_env():
    """Load configuration from .env or .env.example into os.environ."""
    env_path = '.env' if os.path.exists('.env') else '.env.example'
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key, value)


load_env()

DATABASE = os.environ.get('DATABASE', 'board.db')
PORT = int(os.environ.get('PORT', '8080'))
ARTICLE_CODE = os.environ.get('ARTICLE_CODE', 'BETTERCHOICES')

# initialize token system for reuse across components
token_system = TokenSystem(DATABASE)


def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        details TEXT,
        requester TEXT,
        status TEXT DEFAULT 'open'
    )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        user TEXT,
        content TEXT,
        accepted INTEGER DEFAULT 0,
        valuable INTEGER DEFAULT 0
    )"""
    )
    # ensure "valuable" column exists if database was created with an older schema
    c.execute("PRAGMA table_info(replies)")
    columns = [row[1] for row in c.fetchall()]
    if "valuable" not in columns:
        c.execute("ALTER TABLE replies ADD COLUMN valuable INTEGER DEFAULT 0")
    conn.commit()
    conn.close()


def get_json_body(handler):
    length = int(handler.headers.get('Content-Length', 0))
    if length:
        body = handler.rfile.read(length).decode('utf-8')
        return json.loads(body or '{}')
    return {}


def send_json(handler, obj, code=200):
    data = json.dumps(obj).encode('utf-8')
    handler.send_response(code)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def path_parts(path):
    """Return non-empty parts of the URL path."""
    return [p for p in path.strip('/').split('/') if p]




class BoardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        parts = path_parts(parsed.path)
        if parts == ['tasks']:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            tasks = [dict(row) for row in conn.execute('SELECT * FROM tasks')]
            conn.close()
            send_json(self, tasks)
        elif len(parts) == 3 and parts[0] == 'tasks' and parts[2] == 'replies':
            task_id = parts[1]
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            replies = [dict(row) for row in conn.execute('SELECT * FROM replies WHERE task_id = ?', (task_id,))]
            conn.close()
            send_json(self, replies)
        elif parts == ['tokens']:
            send_json(self, token_system.get_balances())
        elif parts == ['register']:
            user_id, expires = token_system.create_user()
            send_json(self, {'user': user_id, 'expires': expires})
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        parts = path_parts(parsed.path)
        if parts == ['earn']:
            data = get_json_body(self)
            user = data.get('user')
            code = data.get('code')
            if not user or not code or not token_system.valid_user(user):
                send_json(self, {'error': 'invalid user or code'}, 400)
                return
            if code != ARTICLE_CODE:
                send_json(self, {'error': 'invalid proof'}, 400)
                return
            token_system.add_tokens(user, 1)
            send_json(self, {'user': user, 'earned': 1})
        elif parts == ['tokens']:
            data = get_json_body(self)
            user = data.get('user')
            amount = int(data.get('amount', 0))
            if not user or amount <= 0 or not token_system.valid_user(user):
                send_json(self, {'error': 'user and positive amount required'}, 400)
                return
            token_system.add_tokens(user, amount)
            send_json(self, {'user': user, 'added': amount})
        elif parts == ['tasks']:
            data = get_json_body(self)
            title = data.get('title')
            details = data.get('details')
            requester = data.get('requester')
            if not title or not requester or not token_system.valid_user(requester):
                send_json(self, {'error': 'title and requester required'}, 400)
                return
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('INSERT INTO tokens(user, tokens) VALUES(?,0) ON CONFLICT(user) DO NOTHING', (requester,))
            conn.commit()
            if not token_system.spend_tokens(requester, 1):
                conn.close()
                send_json(self, {'error': 'not enough tokens'}, 400)
                return
            c.execute('INSERT INTO tasks (title, details, requester) VALUES (?, ?, ?)', (title, details, requester))
            task_id = c.lastrowid
            conn.commit()
            conn.close()
            send_json(self, {'id': task_id, 'title': title, 'details': details, 'requester': requester, 'status': 'open'})
        elif len(parts) == 3 and parts[0] == 'tasks' and parts[2] == 'replies':
            task_id = parts[1]
            data = get_json_body(self)
            user = data.get('user')
            content = data.get('content')
            if not user or not content or not token_system.valid_user(user):
                send_json(self, {'error': 'user and content required'}, 400)
                return
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('INSERT INTO replies (task_id, user, content) VALUES (?,?,?)', (task_id, user, content))
            reply_id = c.lastrowid
            conn.commit()
            conn.close()
            send_json(self, {'id': reply_id, 'task_id': task_id, 'user': user, 'content': content})
        elif len(parts) == 3 and parts[0] == 'replies' and parts[2] == 'accept':
            reply_id = parts[1]
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('SELECT task_id, user FROM replies WHERE id = ?', (reply_id,))
            reply = c.fetchone()
            if not reply:
                conn.close()
                send_json(self, {'error': 'reply not found'}, 404)
                return
            task_id, volunteer = reply
            c.execute('SELECT requester FROM tasks WHERE id = ?', (task_id,))
            row = c.fetchone()
            requester = row[0] if row else None
            if not requester or not token_system.valid_user(requester):
                conn.close()
                send_json(self, {'error': 'task not found'}, 404)
                return
            if not token_system.transfer_tokens(requester, volunteer, 1):
                conn.close()
                send_json(self, {'error': 'not enough tokens'}, 400)
                return
            c.execute('UPDATE replies SET accepted = 1 WHERE id = ?', (reply_id,))
            conn.commit()
            conn.close()
            send_json(self, {'reply': reply_id, 'accepted': True})
        elif len(parts) == 3 and parts[0] == 'replies' and parts[2] == 'valuable':
            reply_id = parts[1]
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('SELECT task_id, user, valuable FROM replies WHERE id = ?', (reply_id,))
            reply = c.fetchone()
            if not reply:
                conn.close()
                send_json(self, {'error': 'reply not found'}, 404)
                return
            task_id, volunteer, valuable = reply
            if valuable:
                conn.close()
                send_json(self, {'error': 'already rewarded'}, 400)
                return
            c.execute('SELECT requester FROM tasks WHERE id = ?', (task_id,))
            row = c.fetchone()
            requester = row[0] if row else None
            if not requester or not token_system.valid_user(requester):
                conn.close()
                send_json(self, {'error': 'task not found'}, 404)
                return
            if not token_system.transfer_tokens(requester, volunteer, 1):
                conn.close()
                send_json(self, {'error': 'not enough tokens'}, 400)
                return
            c.execute('UPDATE replies SET valuable = 1 WHERE id = ?', (reply_id,))
            conn.commit()
            conn.close()
            send_json(self, {'reply': reply_id, 'valuable': True})
        else:
            self.send_error(404)


if __name__ == '__main__':
    init_db()
    server = HTTPServer(('', PORT), BoardHandler)
    print(f'Server running on port {PORT}')
    server.serve_forever()
