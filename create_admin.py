"""Creates an admin login, or resets the password of an existing account and makes it admin.
Run:  python create_admin.py"""
from getpass import getpass

from app import app
from extensions import db
from models import User

with app.app_context():
    print("Using database:", db.engine.url.database)

    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass("Admin password (min 6 chars): ")

    if len(password) < 6:
        raise SystemExit("Password too short.")

    user = User.query.filter_by(email=email).first()
    if user:
        user.role = "admin"            # promote an existing account
        user.set_password(password)    # ALWAYS set the new password too
        if name:
            user.name = name
        print("Existing account updated: now an admin, password changed.")
    else:
        user = User(name=name or "Admin", email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        print("Admin created.")
    db.session.commit()

    # Double-check by reading it back from the database.
    saved = User.query.filter_by(email=email).first()
    print("Saved ->", saved.email, "| role:", saved.role,
          "| password works:", saved.check_password(password))
    print("Now log in with this exact email (all lowercase) and the password you just typed.")