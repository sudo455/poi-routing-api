"""Middleware for request handling."""
import uuid
from flask import g, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.services.rate_limiter import rate_limiter


# Endpoints that don't require rate limiting
RATE_LIMIT_EXEMPT = {
    '/health',
    '/api/v1/about',
    '/apidocs',
    '/apispec_1.json',
    '/flasgger_static',
}


def register_middleware(app):
    """Register middleware functions."""

    @app.before_request
    def add_request_id():
        """Add a unique request ID to each request."""
        request_id = request.headers.get('X-Request-ID')
        if not request_id:
            request_id = str(uuid.uuid4())
        g.request_id = request_id

    @app.before_request
    def check_rate_limit():
        """Check rate limit for authenticated users."""
        # Skip if rate limiting is disabled (e.g., in testing)
        if not app.config.get('RATE_LIMIT_ENABLED', True):
            return None

        # Skip rate limiting for exempt endpoints
        path = request.path
        if any(path.startswith(exempt) for exempt in RATE_LIMIT_EXEMPT):
            return None

        # Skip OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return None

        # Try to get authenticated user
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
        except Exception:
            user_id = None

        if not user_id:
            # No authenticated user, use IP-based limiting with default limit
            user_id = f"ip:{request.remote_addr}"
            user_rate_limit = 30  # Lower limit for unauthenticated requests
        else:
            # Get user's configured rate limit
            from app.models import User
            from app.extensions import db
            user = db.session.get(User, user_id)
            if user:
                user_rate_limit = user.rate_limit
            else:
                user_rate_limit = 60  # Default

        # Check rate limit
        allowed, retry_after = rate_limiter.check(user_id, user_rate_limit)

        if not allowed:
            # HTTP 418 I'm a teapot
            message = rate_limiter.get_teapot_message(retry_after)
            response = jsonify({
                'code': 'IM_A_TEAPOT',
                'message': message,
                'retryAfter': retry_after,
                'requestId': g.get('request_id')
            })
            response.status_code = 418
            response.headers['Retry-After'] = str(retry_after)
            return response

        # Store remaining requests for header
        g.rate_limit_remaining = rate_limiter.get_remaining(user_id, user_rate_limit)
        g.rate_limit_limit = user_rate_limit

        return None

    @app.after_request
    def add_request_id_header(response):
        """Add request ID to response headers."""
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        return response

    @app.after_request
    def add_rate_limit_headers(response):
        """Add rate limit info to response headers."""
        if hasattr(g, 'rate_limit_remaining'):
            response.headers['X-RateLimit-Limit'] = str(g.rate_limit_limit)
            response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
        return response

    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers for development."""
        if app.config.get('DEBUG'):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Request-ID'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response.headers['Access-Control-Expose-Headers'] = 'X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After'
        return response
