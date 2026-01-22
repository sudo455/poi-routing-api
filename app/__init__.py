"""Application factory."""
import os
from flask import Flask, send_from_directory

from app.config import config
from app.extensions import db, migrate, jwt, swagger


def create_app(config_name=None):
    """Create and configure the Flask application."""

    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    app = Flask(__name__, static_folder='../static')
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Import models for migrations
    from app import models  # noqa: F401

    # Swagger configuration
    app.config['SWAGGER'] = {
        'title': 'POI & Routing API',
        'version': '1.0.0',
        'description': 'API for POI search and route planning in Corfu. '
                       'Use JWT authentication for protected endpoints.',
        'uiversion': 3,
        'securityDefinitions': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'Enter: Bearer <your_token>  (include the word Bearer followed by space)'
            }
        },
        'security': [{'Bearer': []}],
        'specs_route': '/apidocs/',
        'auth': {}  # Fix: prevents "None is not defined" JS error
    }
    swagger.init_app(app)

    # Register blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')

    # Register error handlers
    from app.errors import register_error_handlers
    register_error_handlers(app)

    # Register middleware
    from app.middleware import register_middleware
    register_middleware(app)

    # Health check route
    @app.route('/health')
    def health():
        return {'status': 'healthy'}

    # Serve web UI at root
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    return app
