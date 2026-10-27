import re
from flask import Blueprint, request, jsonify, session
from extensions import db
from models import User
from utils import current_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def body():
    return request.get_json(silent=True) or {}


@auth_bp.post("/register")
def register():
    data = body()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if len(name) < 2 or len(name) > 100:
        return jsonify(error="Please enter your name."), 400
    if not EMAIL_RE.match(email) or len(email) > 150:
        return jsonify(error="Please enter a valid email."), 400
    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters."), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="That email is already registered. Try logging in."), 409

    user = User(name=name, email=email)  # role defaults to "customer"
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(error="Wrong email or password."), 401
    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user.to_dict())


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@auth_bp.get("/me")
def me():
    user = current_user()
    return jsonify(user=user.to_dict() if user else None)
