"""
init_db.py — Database Initialization & Demo Seeding
===================================================
Run this script to initialize the database (MySQL or local SQLite fallback)
and seed realistic sample campus listings and demo student accounts.

Usage:
    python init_db.py
"""

import os
import sys
import uuid
import bcrypt
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'college_marketplace')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))


def try_mysql_init():
    """Attempt to initialize MySQL database and return connection if successful."""
    print(f"Connecting to MySQL server at {MYSQL_HOST}:{MYSQL_PORT} (User: '{MYSQL_USER}')...")
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            connection_timeout=3
        )
        cursor = conn.cursor()
        print("[+] Successfully connected to MySQL server!")

        # Read schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        for stmt in statements:
            lines = [line for line in stmt.splitlines() if not line.strip().startswith('--')]
            clean_stmt = '\n'.join(lines).strip()
            if clean_stmt:
                cursor.execute(clean_stmt)

        conn.commit()
        cursor.close()
        conn.close()
        print(f"[+] MySQL Database '{MYSQL_DATABASE}' created and initialized.")
        return True
    except Exception as err:
        print(f"[-] MySQL connection failed: {err}")
        return False


def seed_mysql():
    """Seed sample data into MySQL."""
    import mysql.connector
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        port=MYSQL_PORT
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()['count'] > 0:
        print("[i] MySQL already contains data. Skipping seeding.")
        cursor.close()
        conn.close()
        return

    _perform_seeding(cursor, conn, placeholder="%s")
    cursor.close()
    conn.close()


def init_and_seed_sqlite():
    """Initialize and seed SQLite database."""
    import sqlite3
    from db import _init_sqlite, SQLITE_DB_PATH

    print(f"[+] Initializing local SQLite database at: {SQLITE_DB_PATH}...")
    _init_sqlite()

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        print("[i] SQLite database already contains data. Skipping seeding.")
        conn.close()
        return

    _perform_seeding(cursor, conn, placeholder="?")
    conn.close()


def _perform_seeding(cursor, conn, placeholder="%s"):
    """Generic seeding logic supporting both MySQL and SQLite."""
    hashed_pw = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode('utf-8')
    users_data = [
        ("Alex Chen", "alex@college.edu", "9876543210", hashed_pw),
        ("Priya Sharma", "priya@college.edu", "9876543211", hashed_pw),
        ("Rahul Verma", "rahul@college.edu", "9876543212", hashed_pw),
    ]

    p = placeholder
    user_ids = []
    for name, email, phone, pw in users_data:
        cursor.execute(
            f"INSERT INTO users (name, email, phone, password_hash) VALUES ({p}, {p}, {p}, {p})",
            (name, email, phone, pw)
        )
        user_ids.append(cursor.lastrowid)

    print(f"[+] Created {len(user_ids)} student demo accounts.")

    # Get categories
    cursor.execute("SELECT id, name FROM categories")
    categories = {row[1] if isinstance(row, (list, tuple)) else row['name']: row[0] if isinstance(row, (list, tuple)) else row['id'] for row in cursor.fetchall()}

    sample_products = [
        (
            user_ids[0],
            categories.get('Books', 1),
            "Advanced Engineering Mathematics - 10th Ed (Erwin Kreyszig)",
            "Hardcover edition in excellent condition. Barely used with no markings or highlights. Essential for 2nd year engineering students.",
            450.00,
            "math_textbook.jpg"
        ),
        (
            user_ids[1],
            categories.get('Electronics', 2),
            "Casio FX-991EX ClassWiz Scientific Calculator",
            "Original scientific calculator with solar backup. Perfect for engineering, math, and physics exams. Comes with protective hard slide-case.",
            750.00,
            "casio_calculator.jpg"
        ),
        (
            user_ids[2],
            categories.get('Sports', 5),
            "Hero Sprint 26T Campus Bicycle",
            "Single-speed commuter bicycle, ideal for traveling between hostel and department blocks. Serviced last month, tires in great condition.",
            2200.00,
            "campus_bicycle.jpg"
        ),
        (
            user_ids[0],
            categories.get('Electronics', 2),
            "Sony WH-CH520 Wireless Bluetooth Headphones",
            "On-ear headphones with 50-hour battery life. Crisp sound and mic for online classes and study sessions. Comes with original USB-C charging cable.",
            1800.00,
            "wireless_headphones.jpg"
        ),
        (
            user_ids[1],
            categories.get('Stationery', 6),
            "Chemistry Lab Coat + Safety Goggles (Size M)",
            "100% white cotton lab coat used for only one semester. Clean, stainless, washed and ironed. Free UV protective safety goggles included.",
            250.00,
            "lab_coat.jpg"
        ),
        (
            user_ids[2],
            categories.get('Furniture', 3),
            "Foldable Bed Study Table with Cup Holder",
            "Multi-purpose lap desk with tablet/phone slot and cup holder. Non-slip legs, perfect for late-night hostel study sessions.",
            350.00,
            "study_table.jpg"
        ),
    ]

    for seller_id, cat_id, name, desc, price, img in sample_products:
        cursor.execute(
            f"INSERT INTO products (seller_id, category_id, name, description, price, image, is_sold) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, 0)",
            (seller_id, cat_id, name, desc, price, img)
        )

    conn.commit()
    print(f"[+] Seeded {len(sample_products)} active campus product listings.")


if __name__ == '__main__':
    print("=" * 60)
    print("College Marketplace — Database Setup")
    print("=" * 60)

    mysql_ok = try_mysql_init()
    if mysql_ok:
        seed_mysql()
        db_mode = "MySQL"
    else:
        print("\n--> Automatically configuring zero-setup SQLite database...")
        init_and_seed_sqlite()
        db_mode = "SQLite (Local File)"

    print("\n" + "=" * 60)
    print(f"DATABASE READY ({db_mode})")
    print("=" * 60)
    print("\nTo start your application, run:")
    print("    python app.py\n")
    print("Demo Student Logins:")
    print("    - alex@college.edu   (Password: password123)")
    print("    - priya@college.edu  (Password: password123)")
    print("    - rahul@college.edu  (Password: password123)")
    print("=" * 60 + "\n")
