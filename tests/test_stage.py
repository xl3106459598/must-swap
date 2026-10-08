import io
import os
import re
import tempfile
from pathlib import Path
import bcrypt
import pytest
from PIL import Image
TMP = Path(tempfile.mkdtemp(prefix='must_swap_stage_tests_'))
os.environ['SQLITE_PATH'] = str(TMP / 'startup.db')
os.environ['SECRET_KEY'] = 'stage-tests-private-key-1234567890'
from app import create_app
import db
STAGE = 1

def token(client, path='/'):
    client.get(path)
    with client.session_transaction() as session:
        return session['_csrf']

def post(client, path, data=None, source='/'):
    values = dict(data or {})
    values['csrf_token'] = token(client, source)
    return client.post(path, data=values, follow_redirects=True)

@pytest.fixture
def app(tmp_path):
    db.init_sqlite(tmp_path / 'test.db')
    instance = create_app({'TESTING': True, 'UPLOAD_FOLDER': str(tmp_path / 'uploads')})
    for name, email, role in [('Admin', 'admin@must.edu.mo', 'admin'), ('Seller', 'seller@must.edu.mo', 'student'), ('Buyer', 'buyer@must.edu.mo', 'student')]:
        password = bcrypt.hashpw(b'Password123', bcrypt.gensalt()).decode()
        db.execute_query('INSERT INTO users(name,email,password_hash,role,is_verified,created_at) VALUES(%s,%s,%s,%s,1,%s)', (name, email, password, role, db.now_str()), commit=True)
    seller = db.execute_query("SELECT id FROM users WHERE email='seller@must.edu.mo'", fetchone=True)['id']
    db.execute_query('INSERT INTO products(seller_id,category_id,name,description,price,meeting_place,created_at,updated_at) VALUES(%s,3,%s,%s,50,%s,%s,%s)', (seller, 'Desk lamp', 'A working lamp', 'Library', db.now_str(), db.now_str()), commit=True)
    return instance

def login(app, email):
    client = app.test_client()
    result = post(client, '/login', {'email': email, 'password': 'Password123'}, '/login')
    assert result.status_code == 200
    return client

def test_browse_and_schema(app):
    client = app.test_client()
    assert client.get('/').status_code == 200
    assert b'Desk lamp' in client.get('/').data
    assert client.get('/listing/1').status_code == 200
    assert client.get('/user/2').status_code == 200
    assert client.get('/listing/999999999999999999999999').status_code == 404
    assert db.execute_query('SELECT MAX(version) AS version FROM schema_migrations', fetchone=True)['version'] == STAGE

def test_available_get_routes(app):
    client = app.test_client() if STAGE < 2 else login(app, 'seller@must.edu.mo')
    conversation = None
    wanted = None
    if STAGE >= 6:
        buyer = login(app, 'buyer@must.edu.mo')
        post(buyer, '/listing/1/message', {'body': 'Route check'}, '/listing/1')
        conversation = db.execute_query('SELECT id FROM conversations', fetchone=True)['id']
    if STAGE >= 7:
        post(client, '/wanted/new', {'title': 'Test request', 'category_id': '3', 'max_price': '60'}, '/wanted/new')
        wanted = db.execute_query('SELECT id FROM wanted_posts', fetchone=True)['id']
    for rule in app.url_map.iter_rules():
        if 'GET' not in rule.methods or rule.endpoint in ['static', 'uploaded_image'] or rule.endpoint.startswith('moderation.'):
            continue
        values = {'product_id': 1, 'user_id': 2, 'conv_id': conversation, 'wanted_id': wanted}
        if any((values.get(argument) is None for argument in rule.arguments)):
            continue
        with app.test_request_context():
            from flask import url_for
            path = url_for(rule.endpoint, **{argument: values[argument] for argument in rule.arguments})
        response = client.get(path, follow_redirects=True)
        assert response.status_code == 200, (path, response.status_code)
    if STAGE >= 2:
        administrator = login(app, 'admin@must.edu.mo')
        assert administrator.get('/admin').status_code == 200
        assert administrator.get('/admin/users').status_code == 200

def test_upload_visibility_and_identifier_limits(app):
    client = app.test_client()
    for identifier in ('0', '2147483648', '9' * 5000, '1' + chr(178)):
        assert client.get('/listing/' + identifier).status_code == 404
    folder = Path(app.config['UPLOAD_FOLDER'])
    Image.new('RGB', (10, 10), 'blue').save(folder / 'proof.jpg')
    db.execute_query("UPDATE products SET image='proof.jpg' WHERE id=1", commit=True)
    assert client.get('/static/uploads/proof.jpg').status_code == 200
    db.execute_query('UPDATE products SET is_hidden=1 WHERE id=1', commit=True)
    for path in ['/static/uploads/proof.jpg', '/static/./uploads/proof.jpg', '/static/css/../uploads/proof.jpg', '/static/UPLOADS/proof.jpg']:
        assert client.get(path).status_code == 404, path
    if STAGE >= 2:
        seller = login(app, 'seller@must.edu.mo')
        assert seller.get('/static/uploads/proof.jpg').status_code == 200
    db.execute_query('UPDATE products SET is_hidden=0 WHERE id=1', commit=True)
    db.execute_query('UPDATE users SET is_suspended=1 WHERE id=2', commit=True)
    assert client.get('/static/uploads/proof.jpg').status_code == 404

def test_static_assets_are_served_and_javascript_parses(app):
    import shutil
    import subprocess
    import playwright
    client = app.test_client()
    project = Path(__file__).resolve().parents[1]
    for filename in ['css/style.css', 'js/main.js']:
        response = client.get('/static/' + filename)
        assert response.status_code == 200, filename
        assert response.data == (project / 'static' / filename).read_bytes(), filename
    assert b'box-sizing:border-box' in client.get('/static/css/style.css').data
    if STAGE >= 3:
        assert b'document.querySelectorAll' in client.get('/static/js/main.js').data
    node = shutil.which('node') or str(Path(playwright.__file__).parent / 'driver' / ('node.exe' if os.name == 'nt' else 'node'))
    result = subprocess.run([node, '--check', str(project / 'static' / 'js' / 'main.js')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
