CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
 phone TEXT, password_hash TEXT NOT NULL, is_verified INTEGER NOT NULL DEFAULT 0,
 must_change_password INTEGER NOT NULL DEFAULT 0, role TEXT NOT NULL DEFAULT 'student',
 is_suspended INTEGER NOT NULL DEFAULT 0, wechat_id TEXT, meeting_places TEXT,
 language TEXT NOT NULL DEFAULT 'en', avatar TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now','+8 hours'))
);
CREATE TABLE IF NOT EXISTS categories (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, name_zh TEXT,
 is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 category_id INTEGER NOT NULL REFERENCES categories(id), name TEXT NOT NULL, description TEXT,
 price REAL NOT NULL, image TEXT, is_sold INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'available', item_condition TEXT NOT NULL DEFAULT 'good',
 course_code TEXT, edition TEXT, meeting_place TEXT, is_hidden INTEGER NOT NULL DEFAULT 0,
 expiry_reminded INTEGER NOT NULL DEFAULT 0, expiry_reminded_at TEXT, closed_at TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schema_migrations (
 version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_products_visible ON products(status,is_hidden,created_at);
