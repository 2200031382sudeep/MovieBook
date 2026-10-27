def register_blueprints(app):
    from routes.pages import pages_bp
    from routes.auth import auth_bp
    from routes.public import public_bp
    from routes.admin import admin_bp
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
