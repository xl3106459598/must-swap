from flask import Blueprint, abort, g, render_template
from db import execute_query
bp = Blueprint('browse', __name__)
SELECT = 'SELECT p.*, c.name AS category_name, u.name AS seller_name FROM products p JOIN categories c ON p.category_id=c.id JOIN users u ON p.seller_id=u.id '
@bp.route('/')
def index():
    products=execute_query(SELECT + "WHERE p.status IN ('available','reserved') AND p.is_hidden=0 AND u.is_suspended=0 AND u.is_verified=1 ORDER BY p.created_at DESC,p.id DESC",fetchall=True)
    return render_template('browse/index.html',products=products)
@bp.route('/listing/<int:product_id>')
def detail(product_id):
    p=execute_query(SELECT + "WHERE p.id=%s AND p.status<>'deleted' AND p.is_hidden=0 AND u.is_suspended=0 AND u.is_verified=1",(product_id,),fetchone=True)
    if not p: abort(404)
    if not g.user: p['meeting_place']=None
    return render_template('browse/detail.html',p=p,is_owner=bool(g.user and g.user['id']==p['seller_id']))
@bp.route('/user/<int:user_id>')
def seller(user_id):
    u=execute_query('SELECT id,name FROM users WHERE id=%s AND is_suspended=0 AND is_verified=1',(user_id,),fetchone=True)
    if not u: abort(404)
    items=execute_query(SELECT + "WHERE p.seller_id=%s AND p.status IN ('available','reserved') AND p.is_hidden=0",(user_id,),fetchall=True)
    return render_template('browse/seller.html',u=u,items=items)
