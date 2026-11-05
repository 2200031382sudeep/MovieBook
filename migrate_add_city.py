"""Run ONCE if you already had a database before the location feature was added:
    python migrate_add_city.py
It adds the 'city' column to the theaters table. Safe to run again (it skips if already done)."""
from sqlalchemy import inspect, text

from app import app
from extensions import db

with app.app_context():
    columns = [c["name"] for c in inspect(db.engine).get_columns("theaters")]
    if "city" in columns:
        raise SystemExit("The 'city' column already exists - nothing to do.")

    with db.engine.begin() as conn:
        conn.execute(text("ALTER TABLE theaters ADD COLUMN city VARCHAR(80) NOT NULL DEFAULT 'Bengaluru'"))
        conn.execute(text("CREATE INDEX ix_theaters_city ON theaters (city)"))
    print("Done. All existing theaters were set to city 'Bengaluru'.")
    print("Change them in the Admin panel or with: UPDATE theaters SET city='Hyderabad' WHERE id=3;")
