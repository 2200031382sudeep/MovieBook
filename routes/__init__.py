def register_blueprints(app):
    from .pages import bp as pages_bp
    from .api_public import bp as api_bp
    from .api_admin import bp as admin_api_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_api_bp)
