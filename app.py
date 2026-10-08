from werkzeug.routing import BaseConverter, ValidationError

class IdentifierConverter(BaseConverter):
    regex = '[0-9]{1,10}'

    def to_python(self, value):
        number = int(value)
        if not 0 < number <= 2147483647:
            raise ValidationError()
        return number
import os
import secrets
from datetime import datetime
from flask import Flask, abort, flash, g, redirect, render_template, request, send_from_directory, session, url_for
from db import execute_query
from security import check_csrf, csrf_token, secret_key_is_safe
from i18n import t

def create_app(test_config=None):
    app = Flask(__name__)
    app.url_map.converters['int'] = IdentifierConverter
    secret = os.getenv('SECRET_KEY', '')
    if not secret_key_is_safe(secret):
        secret = secrets.token_hex(32)
    app.config.update(SECRET_KEY=secret, UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads'), MAX_CONTENT_LENGTH=30 * 1024 * 1024, CSRF_ENABLED=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE', '0') == '1')
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    from features import browse
    for module in (browse,):
        app.register_blueprint(module.bp)

    @app.route('/static/uploads/<path:filename>')
    def uploaded_image(filename):
        if '/' in filename or '\\' in filename:
            from flask import abort
            abort(404)
        products = execute_query('SELECT DISTINCT p.seller_id, p.status, p.is_hidden, u.is_suspended, u.is_verified FROM products p JOIN users u ON p.seller_id = u.id WHERE p.image = %s', (filename,), fetchall=True)
        admin = g.user and g.user['role'] == 'admin' and g.user['is_verified']
        permitted = any((row['status'] != 'deleted' and (admin or (g.user and g.user['id'] == row['seller_id']) or (not row['is_hidden'] and (not row['is_suspended']) and row['is_verified'])) for row in products))
        avatars = execute_query('SELECT id, is_suspended, is_verified FROM users WHERE avatar = %s', (filename,), fetchall=True)
        permitted = permitted or any((admin or (g.user and g.user['id'] == row['id']) or (not row['is_suspended'] and row['is_verified']) for row in avatars))
        if not permitted:
            from flask import abort
            abort(404)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    original_static = app.view_functions['static']

    def guarded_static(filename):
        import posixpath
        normalized = posixpath.normpath(filename.replace(chr(92), '/'))
        if normalized.lower().startswith('uploads/'):
            return uploaded_image(normalized.split('/', 1)[1])
        return original_static(filename=filename)
    app.view_functions['static'] = guarded_static

    @app.before_request
    def load_user_and_check_csrf():
        g.user = None
        uid = session.get('user_id')
        if isinstance(uid, int) and 0 < uid <= 2147483647:
            user = execute_query('SELECT * FROM users WHERE id=%s', (uid,), fetchone=True)
            if user and (not user['is_suspended']):
                g.user = user
            else:
                session.pop('user_id', None)
        if any((isinstance(value, int) and value > 2147483647 for value in (request.view_args or {}).values())):
            abort(404)
        check_csrf()
        if g.user and g.user['must_change_password']:
            permitted = request.endpoint in ('accounts.change_password', 'accounts.logout', 'static', 'uploaded_image') or (request.endpoint == 'accounts.profile' and request.method == 'GET')
            if not permitted:
                return redirect(url_for('accounts.profile'))

    @app.context_processor
    def inject_globals():
        return dict(current_user=g.user, categories=execute_query('SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order,name', fetchall=True), csrf_token=csrf_token, _=t, lang='en', unread_count=0, cat_label=lambda value: value['name'], cond_label=lambda code: code.replace('_', ' ').title(), status_label=lambda code: code.title(), conditions=[('new', 'New'), ('like_new', 'Like new'), ('good', 'Good'), ('fair', 'Fair')])

    @app.template_filter('money')
    def money(value):
        if value is None:
            return ''
        number = float(value)
        return 'Free' if number == 0 else f'MOP {number:,.2f}'

    @app.template_filter('format_date')
    def format_date(value, fmt='%Y-%m-%d'):
        if not value:
            return ''
        try:
            return datetime.fromisoformat(str(value)).strftime(fmt)
        except ValueError:
            return str(value)[:10]
    for code in (400, 403, 404, 409, 413, 500):
        app.register_error_handler(code, lambda error: (render_template('error.html', code=error.code, message='The request could not be completed.'), error.code))
    return app
app = create_app()
if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1', host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '5000')))
