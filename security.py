import hmac
import math
import os
import re
import secrets
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlsplit

import bcrypt
from flask import abort, current_app, flash, g, redirect, request, session, url_for

KNOWN_DEFAULT_KEYS = {'dev-secret-key', 'your-secret-key-here', 'change-me-to-a-long-random-string', 'secret', 'changeme'}
MIN_SECRET_LENGTH = 16
EMAIL_LOCAL = re.compile(r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+$")
EMAIL_DOMAIN = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')


def secret_key_is_safe(key):
    key = (key or '').strip()
    return len(key) >= MIN_SECRET_LENGTH and key.lower() not in KNOWN_DEFAULT_KEYS and not key.lower().startswith('college-marketplace-secret')


def allowed_domain():
    return os.getenv('ALLOWED_EMAIL_DOMAIN', 'must.edu.mo').strip().lower()


def is_campus_email(email):
    if not isinstance(email, str) or len(email) > 150 or email.count('@') != 1:
        return False
    local, domain = email.lower().split('@')
    if not local or len(local) > 64 or not EMAIL_LOCAL.fullmatch(local) or local.startswith('.') or local.endswith('.') or '..' in local:
        return False
    if not all(EMAIL_DOMAIN.fullmatch(label) for label in domain.split('.')):
        return False
    allowed = allowed_domain()
    return bool(allowed) and (domain == allowed or domain.endswith('.' + allowed))


def like_pattern(text):
    return '%' + (text or '').replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'


def parse_int(value, default=None, minimum=0, maximum=2147483647):
    if isinstance(value, bool):
        return default
    text = str(value).strip() if value is not None else ''
    if not re.fullmatch(r'[0-9]{1,10}', text):
        return default
    result = int(text)
    return result if minimum <= result <= maximum else default


def finite_price(value, minimum=0, maximum=99999):
    try:
        number = Decimal(str(value).strip())
        if not number.is_finite() or not Decimal(str(minimum)) <= number <= Decimal(str(maximum)):
            return None
        if number.quantize(Decimal('0.01')) != number:
            return None
        result = float(number)
        return result if math.isfinite(result) else None
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return None


def password_problem(password):
    if len(password.encode('utf-8')) > 72:
        return 'The password can have at most 72 UTF-8 bytes.'
    if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
        return 'The password needs at least 8 characters, including letters and digits.'
    return None


def check_password(password, password_hash):
    if not isinstance(password, str) or len(password.encode('utf-8')) > 72:
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except (ValueError, TypeError, AttributeError):
        return False


def safe_next(target):
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target or any(ord(character) < 32 for character in target):
        return None
    parsed = urlsplit(target)
    return target if not parsed.scheme and not parsed.netloc else None


def csrf_token():
    token = session.get('_csrf')
    if not isinstance(token, str) or not re.fullmatch(r'[0-9a-f]{32}', token):
        token = secrets.token_hex(16)
        session['_csrf'] = token
    return token


def check_csrf():
    if not current_app.config.get('CSRF_ENABLED', True):
        return
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        sent = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token', '')
        expected = session.get('_csrf', '')
        if not isinstance(sent, str) or not re.fullmatch(r'[0-9a-f]{32}', sent) or not isinstance(expected, str):
            abort(400)
        if not hmac.compare_digest(sent.encode('ascii'), expected.encode('ascii', errors='replace')):
            abort(400)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            flash('Please log in first.', 'warning')
            return redirect(url_for('accounts.login', next=request.full_path.rstrip('?')))
        return view(*args, **kwargs)
    return wrapper


def verified_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            flash('Please log in first.', 'warning')
            return redirect(url_for('accounts.login', next=request.full_path.rstrip('?')))
        if g.user['must_change_password']:
            return redirect(url_for('accounts.profile') + '#password')
        if not g.user['is_verified']:
            flash('Your account is waiting for approval by an administrator.', 'warning')
            return redirect(url_for('accounts.pending'))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None or g.user['role'] != 'admin' or not g.user['is_verified']:
            abort(403)
        if g.user['must_change_password']:
            return redirect(url_for('accounts.profile') + '#password')
        return view(*args, **kwargs)
    return wrapper
