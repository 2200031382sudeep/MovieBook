from flask import Flask, render_template, request, jsonify

from config import Config
from extensions import db
from routes import register_blueprints
from utils import current_user


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    import models  # noqa: F401  (ensure SQLAlchemy models are registered)
    register_blueprints(app)

    # Initialize tables if they do not exist
    with app.app_context():
        try:
            db.create_all()
        except Exception as exc:
            print("\n*** Could not connect to MySQL. Check your .env file credentials and MySQL service.")
            print("*** Details:\n", exc)
            raise

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    @app.before_request
    def api_writes_must_be_json():
        """CSRF protection: write requests to API must supply a JSON content-type."""
        if request.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            # Only enforce if request carries a body payload
            if request.content_length and not request.is_json:
                return jsonify(error="API requests with body must be JSON format."), 415

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return jsonify(error="Resource not found."), 404
        return render_template("error.html", code=404, message="We couldn't find that page."), 404

    @app.errorhandler(403)
    def forbidden(_):
        if request.path.startswith("/api/"):
            return jsonify(error="Permission denied."), 403
        return render_template("error.html", code=403, message="You don't have permission to view this page."), 403

    @app.errorhandler(500)
    def server_error(_):
        if request.path.startswith("/api/"):
            return jsonify(error="An internal server error occurred."), 500
        return render_template("error.html", code=500, message="An internal server error occurred. Please try again later."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
