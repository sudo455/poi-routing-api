"""Flask extensions initialization."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flasgger import Swagger

# Database
db = SQLAlchemy()

# Migrations
migrate = Migrate()

# JWT Authentication
jwt = JWTManager()

# Swagger/OpenAPI
swagger = Swagger()
