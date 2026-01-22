"""Application configuration."""
import os
from datetime import timedelta


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database - PostgreSQL + PostGIS required
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Rate limiting defaults
    RATE_LIMIT_ENABLED = True
    DEFAULT_RATE_LIMIT = 60  # requests per minute
    RATE_LIMIT_WINDOW = 60  # seconds
    RATE_LIMIT_BLOCK_DURATION = 180  # 3 minutes

    # GraphHopper
    GRAPHHOPPER_URL = os.environ.get('GRAPHHOPPER_URL', 'http://localhost:8989')


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    # PostgreSQL + PostGIS (run: docker compose up db -d)
    # Using psycopg v3 driver
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg://poi_user:poi_password@localhost:5432/poi_db'
    )


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    # Stricter settings for production
    JWT_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    # Use DATABASE_URL from environment, or fall back to test database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        os.environ.get(
            'TEST_DATABASE_URL',
            'postgresql+psycopg://poi_user:poi_password@localhost:5432/poi_test_db'
        )
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=30)

    # Disable rate limiting for tests
    RATE_LIMIT_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
