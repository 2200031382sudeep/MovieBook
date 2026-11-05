from functools import wraps
from flask import session, redirect, url_for, request, g, jsonify, abort
from extensions import db
from models import User


def current_user():
    """Returns the logged-in User, or None."""
    if "user" not in g:
        uid = session.get("user_id")
        g.user = db.session.get(User, uid) if uid else None
    return g.user


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return jsonify(error="Please log in first."), 401
        return view(*args, **kwargs)
    return wrapped


def api_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify(error="Please log in first."), 401
        if not user.is_admin:
            return jsonify(error="Admins only."), 403
        return view(*args, **kwargs)
    return wrapped


def page_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("pages.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def page_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("pages.login", next=request.path))
        if not user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped
