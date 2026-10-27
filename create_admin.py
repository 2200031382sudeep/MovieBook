from getpass import getpass
from app import app
from extensions import db
from models import User

with app.app_context():
    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass("Admin password (min 6 chars): ")

    if len(password) < 6:
        raise SystemExit("Password too short.")

    user = User.query.filter_by(email=email).first()
    if user:
        user.role = "admin"          # promote an existing account
        print("Existing user promoted to admin.")
    else:
        user = User(name=name, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        print("Admin created.")
    db.session.commit()
