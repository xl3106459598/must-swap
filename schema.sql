-- ============================================================
-- College Marketplace — Database Schema
-- ============================================================
-- Tech: MySQL
-- Tables: users, categories, products, orders
-- Demonstrates: PRIMARY KEY, FOREIGN KEY, UNIQUE, AUTO_INCREMENT
-- ============================================================

CREATE DATABASE IF NOT EXISTS college_marketplace;
USE college_marketplace;

-- -----------------------------------------------------------
-- 1. USERS — every registered student
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL,
    email       VARCHAR(150)  NOT NULL UNIQUE,
    phone       VARCHAR(15)   NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- 2. CATEGORIES — product categories
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Pre-seed categories
INSERT IGNORE INTO categories (name) VALUES
    ('Books'),
    ('Electronics'),
    ('Furniture'),
    ('Clothing'),
    ('Sports'),
    ('Stationery'),
    ('Other');

-- -----------------------------------------------------------
-- 3. PRODUCTS — items listed by sellers
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    seller_id   INT           NOT NULL,
    category_id INT           NOT NULL,
    name        VARCHAR(200)  NOT NULL,
    description TEXT,
    price       DECIMAL(10,2) NOT NULL,
    image       VARCHAR(300)  DEFAULT NULL,
    is_sold     BOOLEAN       DEFAULT FALSE,
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (seller_id)   REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------
-- 4. ORDERS — purchase / contact records
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    product_id  INT NOT NULL,
    buyer_id    INT NOT NULL,
    ordered_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (buyer_id)   REFERENCES users(id)    ON DELETE CASCADE
);
