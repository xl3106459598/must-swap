import os
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
USE_SQLITE = True
connection_pool = None
MACAU_TIMEZONE = timezone(timedelta(hours=8), 'Asia/Macau')
LATEST_SCHEMA_VERSION = 1
SQLITE_DB_PATH = os.getenv('SQLITE_PATH') or str(BASE_DIR / 'must_swap.db')
SQLITE_SCHEMA = (BASE_DIR / 'schema.sql').read_text(encoding='utf-8-sig')
_state = threading.local()
CATEGORY_SEED = [(1, 'Textbooks & Notes', None, 1), (2, 'Electronics', None, 2), (3, 'Dorm & Daily Use', None, 3), (4, 'Furniture', None, 4), (5, 'Sports & Leisure', None, 5), (6, 'Clothing & Accessories', None, 6), (7, 'Others', None, 7)]
ADDITIONS = {'users': {'phone': 'TEXT', 'is_verified': 'INTEGER NOT NULL DEFAULT 0', 'must_change_password': 'INTEGER NOT NULL DEFAULT 0', 'role': "TEXT NOT NULL DEFAULT 'student'", 'is_suspended': 'INTEGER NOT NULL DEFAULT 0', 'wechat_id': 'TEXT', 'meeting_places': 'TEXT', 'language': "TEXT NOT NULL DEFAULT 'en'", 'avatar': 'TEXT', 'created_at': 'TEXT'}, 'categories': {'name_zh': 'TEXT', 'is_active': 'INTEGER NOT NULL DEFAULT 1', 'sort_order': 'INTEGER NOT NULL DEFAULT 0'}, 'products': {'is_sold': 'INTEGER NOT NULL DEFAULT 0', 'image': 'TEXT', 'status': "TEXT NOT NULL DEFAULT 'available'", 'item_condition': "TEXT NOT NULL DEFAULT 'good'", 'course_code': 'TEXT', 'edition': 'TEXT', 'meeting_place': 'TEXT', 'is_hidden': 'INTEGER NOT NULL DEFAULT 0', 'expiry_reminded': 'INTEGER NOT NULL DEFAULT 0', 'expiry_reminded_at': 'TEXT', 'closed_at': 'TEXT', 'created_at': 'TEXT', 'updated_at': 'TEXT'}}

def local_now():
    return datetime.now(MACAU_TIMEZONE).replace(tzinfo=None)

def now_str(days=0, minutes=0, seconds=0):
    return (local_now() + timedelta(days=days, minutes=minutes, seconds=seconds)).strftime('%Y-%m-%d %H:%M:%S')

def _path(value):
    if value == ':memory:':
        return value
    candidate = Path(value).expanduser()
    return str(candidate if candidate.is_absolute() else BASE_DIR / candidate)

def _connect(path=None):
    path = _path(path or SQLITE_DB_PATH)
    if path != ':memory:':
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 30000')
    return conn

def backup_database(path=None):
    path = _path(path or SQLITE_DB_PATH)
    if path == ':memory:' or not Path(path).exists():
        return None
    directory = Path(path).parent / 'backups'
    directory.mkdir(parents=True, exist_ok=True)
    stamp = local_now().strftime('%Y%m%d_%H%M%S_%f')
    target = directory / (Path(path).name + '.' + stamp + '.bak')
    source = sqlite3.connect(path)
    backup = sqlite3.connect(target)
    try:
        source.backup(backup)
    finally:
        backup.close()
        source.close()
    return str(target)

def _statements():
    return [statement.strip() for statement in SQLITE_SCHEMA.split(';') if statement.strip()]

def _columns(conn, table):
    return {row['name']: row for row in conn.execute('PRAGMA table_info(' + table + ')')}

def _migrate_core(conn):
    legacy_products = bool(_columns(conn, 'products')) and 'status' not in _columns(conn, 'products')
    for statement in _statements():
        if statement.startswith('CREATE TABLE'):
            conn.execute(statement)
    for table, additions in ADDITIONS.items():
        existing = _columns(conn, table)
        for column, definition in additions.items():
            if column not in existing:
                conn.execute('ALTER TABLE ' + table + ' ADD COLUMN ' + column + ' ' + definition)
    users = _columns(conn, 'users')
    if users.get('phone') and users['phone']['notnull']:
        statement = next((s for s in _statements() if s.startswith('CREATE TABLE IF NOT EXISTS users ')))
        conn.execute(statement.replace('IF NOT EXISTS users', 'users_upgrade', 1))
        names = list(_columns(conn, 'users_upgrade'))
        columns = ','.join(names)
        conn.execute('INSERT INTO users_upgrade (' + columns + ') SELECT ' + columns + ' FROM users')
        conn.execute('DROP TABLE users')
        conn.execute('ALTER TABLE users_upgrade RENAME TO users')
    timestamp = now_str()
    conn.execute("UPDATE users SET language = 'en', created_at = COALESCE(created_at, ?)", (timestamp,))
    conn.execute('UPDATE categories SET name_zh = NULL, sort_order = CASE WHEN sort_order = 0 THEN id ELSE sort_order END')
    conn.execute('UPDATE products SET created_at = COALESCE(created_at, ?), updated_at = COALESCE(updated_at, created_at, ?)', (timestamp, timestamp))
    if legacy_products:
        conn.execute("UPDATE products SET status = CASE WHEN is_sold = 1 THEN 'sold' ELSE 'available' END")
    conn.execute("UPDATE products SET closed_at = ? WHERE status IN ('sold','expired','deleted') AND closed_at IS NULL", (timestamp,))
    if conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0] == 0:
        conn.executemany('INSERT INTO categories(id,name,name_zh,sort_order) VALUES(?,?,?,?)', CATEGORY_SEED)
    else:
        for _, name, _, order in CATEGORY_SEED:
            conn.execute('INSERT OR IGNORE INTO categories(name,sort_order) VALUES(?,?)', (name, order))

def init_sqlite(path=None):
    global SQLITE_DB_PATH
    if path:
        SQLITE_DB_PATH = _path(str(path))
    conn = _connect()
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        current = conn.execute('SELECT COALESCE(MAX(version),0) FROM schema_migrations').fetchone()[0] if 'schema_migrations' in tables else 0
        if current > LATEST_SCHEMA_VERSION:
            raise RuntimeError('This database was created by a newer release. Use a matching application version.')
        if current == LATEST_SCHEMA_VERSION:
            return SQLITE_DB_PATH
        if tables:
            backup_database()
        conn.execute('PRAGMA foreign_keys = OFF')
        conn.execute('BEGIN IMMEDIATE')
        _migrate_core(conn)
        for statement in _statements():
            if statement.startswith('CREATE INDEX'):
                conn.execute(statement)
        for version, name in [(1, 'Marketplace foundation')]:
            conn.execute('INSERT OR IGNORE INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)', (version, name, now_str()))
        violations = conn.execute('PRAGMA foreign_key_check').fetchall()
        if violations:
            raise RuntimeError('Migration found inconsistent foreign keys; the original database was preserved.')
        conn.commit()
        return SQLITE_DB_PATH
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def migrate_from(source, destination=None, upload_folder=None):
    source = Path(source).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError('The migration source database does not exist.')
    destination = _path(str(destination or SQLITE_DB_PATH))
    if source == Path(destination).resolve():
        init_sqlite(destination)
    else:
        if Path(destination).exists():
            check = sqlite3.connect(destination)
            try:
                has_users = check.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
                if has_users and check.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
                    raise RuntimeError('The destination contains accounts. Choose an empty destination database.')
            finally:
                check.close()
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        original = sqlite3.connect('file:' + source.as_posix() + '?mode=ro', uri=True)
        target = sqlite3.connect(destination)
        try:
            original.backup(target)
        finally:
            target.close()
            original.close()
        init_sqlite(destination)
    uploads = Path(upload_folder or BASE_DIR / 'static' / 'uploads')
    originals = source.parent / 'static' / 'uploads'
    if originals.is_dir() and originals.resolve() != uploads.resolve():
        uploads.mkdir(parents=True, exist_ok=True)
        files = execute_query('SELECT image AS filename FROM products WHERE image IS NOT NULL UNION SELECT avatar AS filename FROM users WHERE avatar IS NOT NULL', fetchall=True)
        for row in files:
            name = row['filename']
            if name and Path(name).name == name:
                original = originals / name
                target = uploads / name
                if original.is_file() and (not target.exists()):
                    shutil.copy2(original, target)
    return destination

def get_db():
    return _connect()

def dict_from_row(row):
    return None if row is None else dict(row)

@contextmanager
def transaction():
    active = getattr(_state, 'connection', None)
    if active is not None:
        sequence = getattr(_state, 'savepoint', 0) + 1
        _state.savepoint = sequence
        name = 'nested_' + str(sequence)
        active.execute('SAVEPOINT ' + name)
        try:
            yield active
            active.execute('RELEASE SAVEPOINT ' + name)
        except Exception:
            active.execute('ROLLBACK TO SAVEPOINT ' + name)
            active.execute('RELEASE SAVEPOINT ' + name)
            raise
        return
    conn = get_db()
    _state.connection = conn
    _state.savepoint = 0
    try:
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _state.connection = None
        conn.close()

def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    active = getattr(_state, 'connection', None)
    conn = active if active is not None else get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(query.replace('%s', '?'), params if params is not None else ())
        if fetchone:
            result = dict_from_row(cursor.fetchone())
        elif fetchall:
            result = [dict_from_row(row) for row in cursor.fetchall()]
        else:
            result = cursor.lastrowid if commit else None
        if commit and active is None:
            conn.commit()
        return result
    except Exception:
        if active is None:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if active is None:
            conn.close()
init_sqlite()
