"""Custom error handlers with personality."""
import json
import random
from pathlib import Path
from flask import jsonify, g


def load_json_messages(filename):
    """Load messages from JSON file."""
    path = Path(__file__).parent / filename
    with open(path) as f:
        data = json.load(f)
    return data.get('messages') or data.get('reasons', [])


NOT_FOUND_REASONS = load_json_messages('not_found_reasons.json')
TEAPOT_MESSAGES = load_json_messages('teapot_messages.json')


def get_random_404_message():
    """Get a random witty 404 message."""
    return random.choice(NOT_FOUND_REASONS)


def get_random_teapot_message(seconds=60):
    """Get a random teapot message with retry seconds."""
    message = random.choice(TEAPOT_MESSAGES)
    return message.format(seconds=seconds)


def register_error_handlers(app):
    """Register custom error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'code': 'BAD_REQUEST',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request',
            'requestId': g.get('request_id')
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'code': 'UNAUTHORIZED',
            'message': 'Authentication required',
            'requestId': g.get('request_id')
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'code': 'FORBIDDEN',
            'message': 'You do not have permission to access this resource',
            'requestId': g.get('request_id')
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'code': 'NOT_FOUND',
            'message': get_random_404_message(),
            'requestId': g.get('request_id')
        }), 404

    @app.errorhandler(418)
    def im_a_teapot(error):
        """I'm a teapot - used for rate limiting."""
        retry_after = getattr(error, 'retry_after', 60)
        response = jsonify({
            'code': 'IM_A_TEAPOT',
            'message': get_random_teapot_message(retry_after),
            'retryAfter': retry_after,
            'requestId': g.get('request_id')
        })
        response.headers['Retry-After'] = str(retry_after)
        return response, 418

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'code': 'INTERNAL_SERVER_ERROR',
            'message': 'An unexpected error occurred',
            'requestId': g.get('request_id')
        }), 500

    @app.errorhandler(501)
    def not_implemented(error):
        return jsonify({
            'code': 'NOT_IMPLEMENTED',
            'message': 'This endpoint is not yet implemented',
            'requestId': g.get('request_id')
        }), 501

    @app.errorhandler(502)
    def bad_gateway(error):
        return jsonify({
            'code': 'BAD_GATEWAY',
            'message': 'GraphHopper service unavailable',
            'requestId': g.get('request_id')
        }), 502


class TeapotError(Exception):
    """Custom exception for rate limiting (418 I'm a teapot)."""

    def __init__(self, retry_after=60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds.")
