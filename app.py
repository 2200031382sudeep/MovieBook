from flask import Flask, render_template, request, jsonify

from config import Config
from extensions import db
from routes import register_blueprints
from utils import current_user


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    import models  # noqa: F401  (so SQLAlchemy knows the tables)
    register_blueprints(app)

    from theater_search import bp as theater_search_bp  # theater search page + API
    app.register_blueprint(theater_search_bp)

    # Create the tables in MySQL the first time (does nothing if they already exist).
    with app.app_context():
        try:
            db.create_all()
        except Exception as exc:
            print("\n*** Could not connect to MySQL. Check DB_PASSWORD in your .env file,")
            print("*** that MySQL is running, and that the database exists. Details:\n", exc)
            raise

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    @app.before_request
    def api_writes_must_be_json():
        """Simple CSRF protection: another website cannot send JSON to our API with your cookie."""
        if request.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if not request.is_json:
                return jsonify(error="Requests must be JSON."), 415

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return jsonify(error="Not found."), 404
        return render_template("error.html", code=404, message="We couldn't find that page."), 404

    @app.errorhandler(403)
    def forbidden(_):
        if request.path.startswith("/api/"):
            return jsonify(error="Not allowed."), 403
        return render_template("error.html", code=403, message="You don't have permission to open this page."), 403

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
