"""
db.py — Database Connection Helper (MySQL + Automatic SQLite Fallback)
======================================================================
Provides execute_query() for database interactions.
- Tries MySQL connection first (configured via .env).
- If MySQL server is not running or unconfigured, seamlessly falls back
  to local SQLite (college_marketplace.db) so the app works immediately.
"""

import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

USE_SQLITE = False
connection_pool = None
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'college_marketplace.db')

# 1. Attempt MySQL connection
try:
    import mysql.connector
    from mysql.connector import pooling

    db_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'college_marketplace'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'pool_name': 'marketplace_pool',
        'pool_size': 5,
        'pool_reset_session': True,
    }
    connection_pool = pooling.MySQLConnectionPool(**db_config)
    print("[DB INFO] Connected to MySQL successfully.")
except Exception as err:
    print(f"[DB INFO] MySQL is not available ({err}).")
    print("[DB INFO] Falling back to SQLite mode (college_marketplace.db).")
    USE_SQLITE = True


def _init_sqlite():
    """Create SQLite tables if they do not exist."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image TEXT DEFAULT NULL,
            is_sold INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE
        );

        INSERT OR IGNORE INTO categories (id, name) VALUES
            (1, 'Books'),
            (2, 'Electronics'),
            (3, 'Furniture'),
            (4, 'Clothing'),
            (5, 'Sports'),
            (6, 'Stationery'),
            (7, 'Other');
    """)
    conn.commit()
    conn.close()


if USE_SQLITE:
    _init_sqlite()


def get_db():
    """Get a database connection (MySQL or SQLite)."""
    if USE_SQLITE:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    else:
        if connection_pool is None:
            raise Exception("MySQL connection pool is not available.")
        return connection_pool.get_connection()


def close_db(conn):
    """Close connection or return to pool."""
    if conn:
        conn.close()


def dict_from_row(row):
    """Convert sqlite3.Row or dict to standard python dictionary."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    """
    Execute a SQL query across MySQL or SQLite.

    Args:
        query   : SQL query string (uses %s placeholders)
        params  : Tuple/list of query parameters
        fetchone: Return a single row as dict
        fetchall: Return all rows as list of dicts
        commit  : Commit the transaction

    Returns:
        Query result, or lastrowid for INSERT, or None
    """
    conn = get_db()

    if USE_SQLITE:
        # SQLite uses ? instead of %s
        sql_query = query.replace('%s', '?')
        # Handle BOOLEAN syntax differences if present
        sql_query = sql_query.replace('is_sold = FALSE', 'is_sold = 0')
        sql_query = sql_query.replace('is_sold = TRUE', 'is_sold = 1')
        sql_query = sql_query.replace('FALSE', '0').replace('TRUE', '1')

        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(sql_query, params)
            else:
                cursor.execute(sql_query)

            if commit:
                conn.commit()
                return cursor.lastrowid
            if fetchone:
                row = cursor.fetchone()
                return dict_from_row(row)
            if fetchall:
                rows = cursor.fetchall()
                return [dict_from_row(r) for r in rows]
            return None
        except Exception as err:
            if commit:
                conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()
    else:
        # MySQL path
        cursor = conn.cursor(dictionary=True)
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if commit:
                conn.commit()
                return cursor.lastrowid
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            return None
        except Exception as err:
            if commit:
                conn.rollback()
            raise err
        finally:
            cursor.close()
            close_db(conn)
