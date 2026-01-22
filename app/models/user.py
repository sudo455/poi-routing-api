"""User model with authentication."""
import uuid
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    """User model for authentication and route ownership."""

    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # Rate limiting
    rate_limit = db.Column(db.Integer, default=60)  # requests per minute

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    routes = db.relationship('Route', backref='owner', lazy='dynamic')

    def set_password(self, password: str) -> None:
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Convert to dictionary (without sensitive data)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'rateLimit': self.rate_limit,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f'<User {self.username}>'
