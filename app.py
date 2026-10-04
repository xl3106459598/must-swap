"""
app.py — College Marketplace Flask Application
=================================================
A peer-to-peer campus marketplace for students to buy/sell
second-hand products. Uses raw SQL to demonstrate CRUD operations,
bcrypt for password hashing, and Flask sessions for authentication.
"""

import os
import uuid
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, abort
)
import bcrypt
from dotenv import load_dotenv
from db import execute_query

load_dotenv()

# ── Flask App Configuration ──────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max upload

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


# ── Helpers ──────────────────────────────────────────────────

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file):
    """Save an uploaded image and return the filename."""
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None


def login_required(f):
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ── Template Context ─────────────────────────────────────────

@app.context_processor
def inject_categories():
    """Make categories available in every template."""
    try:
        categories = execute_query("SELECT * FROM categories ORDER BY name", fetchall=True)
    except Exception:
        categories = []
    return dict(categories=categories)


@app.context_processor
def inject_user():
    """Make current user info available in every template."""
    user = None
    if 'user_id' in session:
        try:
            user = execute_query(
                "SELECT id, name, email, phone, created_at FROM users WHERE id = %s",
                (session['user_id'],), fetchone=True
            )
        except Exception:
            pass
    return dict(current_user=user)


@app.template_filter('format_date')
def format_date_filter(val, fmt='%b %d'):
    """Format datetime object or timestamp string gracefully."""
    if not val:
        return ''
    if isinstance(val, str):
        from datetime import datetime
        # Try various string date formats
        for date_fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S'):
            try:
                val = datetime.strptime(val.split('.')[0], date_fmt)
                break
            except Exception:
                pass
    try:
        return val.strftime(fmt)
    except Exception:
        return str(val)[:10]


# ══════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new student account."""
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # ── Validation ──
        errors = []
        if not name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        if not phone:
            errors.append('Phone number is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        # Check if email already exists
        if not errors:
            existing = execute_query(
                "SELECT id FROM users WHERE email = %s", (email,), fetchone=True
            )
            if existing:
                errors.append('An account with this email already exists.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        # ── Hash password with bcrypt ──
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # ── Insert into database ──
        execute_query(
            "INSERT INTO users (name, email, phone, password_hash) VALUES (%s, %s, %s, %s)",
            (name, email, phone, password_hash), commit=True
        )

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Log in an existing user."""
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = execute_query(
            "SELECT id, name, password_hash FROM users WHERE email = %s",
            (email,), fetchone=True
        )

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')
            return render_template('login.html', email=email)

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Log out the current user."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ══════════════════════════════════════════════════════════════
#  PRODUCT ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Home page — browse products with search, filter, and sort."""
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category', '', type=str)
    sort = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price', '', type=str)
    max_price = request.args.get('max_price', '', type=str)

    # ── Build dynamic SQL query ──
    query = """
        SELECT p.*, c.name AS category_name, u.name AS seller_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        JOIN users u ON p.seller_id = u.id
        WHERE p.is_sold = FALSE
    """
    params = []

    if search:
        query += " AND (p.name LIKE %s OR p.description LIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])

    if category_id:
        query += " AND p.category_id = %s"
        params.append(int(category_id))

    if min_price:
        query += " AND p.price >= %s"
        params.append(float(min_price))

    if max_price:
        query += " AND p.price <= %s"
        params.append(float(max_price))

    # ── Sorting ──
    sort_map = {
        'newest': 'p.created_at DESC',
        'oldest': 'p.created_at ASC',
        'price_asc': 'p.price ASC',
        'price_desc': 'p.price DESC',
    }
    query += f" ORDER BY {sort_map.get(sort, 'p.created_at DESC')}"

    products = execute_query(query, tuple(params) if params else None, fetchall=True)

    return render_template(
        'index.html',
        products=products,
        search=search,
        selected_category=category_id,
        selected_sort=sort,
        min_price=min_price,
        max_price=max_price,
    )


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """View a single product's details and seller contact info."""
    product = execute_query(
        """SELECT p.*, c.name AS category_name,
                  u.name AS seller_name, u.email AS seller_email,
                  u.phone AS seller_phone, u.id AS seller_user_id
           FROM products p
           JOIN categories c ON p.category_id = c.id
           JOIN users u ON p.seller_id = u.id
           WHERE p.id = %s""",
        (product_id,), fetchone=True
    )
    if not product:
        abort(404)

    return render_template('product_detail.html', product=product)


@app.route('/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    """Seller adds a new product listing."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '').strip()
        category_id = request.form.get('category_id', '').strip()
        image_file = request.files.get('image')

        # ── Validation ──
        errors = []
        if not name:
            errors.append('Product name is required.')
        if not price:
            errors.append('Price is required.')
        else:
            try:
                price = float(price)
                if price <= 0:
                    errors.append('Price must be greater than 0.')
            except ValueError:
                errors.append('Price must be a valid number.')
        if not category_id:
            errors.append('Please select a category.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('add_product.html',
                                   name=name, description=description,
                                   price=price, category_id=category_id)

        # ── Save image ──
        image_filename = save_uploaded_image(image_file)

        # ── Insert product ──
        execute_query(
            """INSERT INTO products (seller_id, category_id, name, description, price, image)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (session['user_id'], int(category_id), name, description, price, image_filename),
            commit=True
        )

        flash('Product listed successfully!', 'success')
        return redirect(url_for('my_listings'))

    return render_template('add_product.html')


@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Seller edits an existing product listing."""
    product = execute_query(
        "SELECT * FROM products WHERE id = %s AND seller_id = %s",
        (product_id, session['user_id']), fetchone=True
    )
    if not product:
        abort(404)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '').strip()
        category_id = request.form.get('category_id', '').strip()
        image_file = request.files.get('image')

        errors = []
        if not name:
            errors.append('Product name is required.')
        if not price:
            errors.append('Price is required.')
        else:
            try:
                price = float(price)
                if price <= 0:
                    errors.append('Price must be greater than 0.')
            except ValueError:
                errors.append('Price must be a valid number.')
        if not category_id:
            errors.append('Please select a category.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('edit_product.html', product=product)

        # ── Handle image update ──
        image_filename = product['image']
        if image_file and image_file.filename:
            new_image = save_uploaded_image(image_file)
            if new_image:
                # Delete old image if it exists
                if image_filename:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                image_filename = new_image

        execute_query(
            """UPDATE products
               SET name = %s, description = %s, price = %s,
                   category_id = %s, image = %s
               WHERE id = %s AND seller_id = %s""",
            (name, description, price, int(category_id), image_filename,
             product_id, session['user_id']),
            commit=True
        )

        flash('Product updated successfully!', 'success')
        return redirect(url_for('my_listings'))

    return render_template('edit_product.html', product=product)


@app.route('/delete-product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Seller deletes a product listing."""
    product = execute_query(
        "SELECT image FROM products WHERE id = %s AND seller_id = %s",
        (product_id, session['user_id']), fetchone=True
    )
    if not product:
        abort(404)

    # Delete image file
    if product['image']:
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image'])
        if os.path.exists(img_path):
            os.remove(img_path)

    execute_query(
        "DELETE FROM products WHERE id = %s AND seller_id = %s",
        (product_id, session['user_id']), commit=True
    )

    flash('Product deleted.', 'info')
    return redirect(url_for('my_listings'))


@app.route('/mark-sold/<int:product_id>', methods=['POST'])
@login_required
def mark_sold(product_id):
    """Seller marks a product as sold — removes it from available listings."""
    execute_query(
        "UPDATE products SET is_sold = TRUE WHERE id = %s AND seller_id = %s",
        (product_id, session['user_id']), commit=True
    )
    flash('Product marked as sold!', 'success')
    return redirect(url_for('my_listings'))


# ══════════════════════════════════════════════════════════════
#  DASHBOARD ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/my-listings')
@login_required
def my_listings():
    """Seller dashboard — manage own product listings."""
    products = execute_query(
        """SELECT p.*, c.name AS category_name
           FROM products p
           JOIN categories c ON p.category_id = c.id
           WHERE p.seller_id = %s
           ORDER BY p.created_at DESC""",
        (session['user_id'],), fetchall=True
    )
    return render_template('my_listings.html', products=products)


@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    user = execute_query(
        "SELECT id, name, email, phone, created_at FROM users WHERE id = %s",
        (session['user_id'],), fetchone=True
    )
    # Count user's listings
    stats = execute_query(
        """SELECT
               COUNT(*) AS total_listings,
               SUM(CASE WHEN is_sold = FALSE THEN 1 ELSE 0 END) AS active_listings,
               SUM(CASE WHEN is_sold = TRUE THEN 1 ELSE 0 END) AS sold_listings
           FROM products WHERE seller_id = %s""",
        (session['user_id'],), fetchone=True
    )
    return render_template('profile.html', user=user, stats=stats)


# ══════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ══════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error_code=404, error_msg='Page Not Found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error_code=500, error_msg='Internal Server Error'), 500


# ══════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)
