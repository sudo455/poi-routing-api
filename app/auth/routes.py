"""Authentication routes."""
from flask import jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from app.auth import bp
from app.extensions import db
from app.models import User


def error_response(code: str, message: str, status: int, details: dict = None):
    """Create standardized error response matching OpenAPI spec."""
    response = {
        'code': code,
        'message': message
    }
    if details:
        response['details'] = details
    return jsonify(response), status


@bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
              description: Unique username (3-50 characters)
              example: johndoe
            email:
              type: string
              description: Valid email address
              example: john@example.com
            password:
              type: string
              description: Password (min 6 characters)
              example: secretpassword
    responses:
      201:
        description: User registered successfully
        schema:
          type: object
          properties:
            message:
              type: string
            user:
              type: object
              properties:
                id:
                  type: string
                username:
                  type: string
                email:
                  type: string
            accessToken:
              type: string
              description: JWT access token (15 min expiry)
            refreshToken:
              type: string
              description: JWT refresh token (30 day expiry)
      400:
        description: Bad request (invalid username/email/password)
      409:
        description: Conflict (username or email already exists)
    """
    data = request.get_json()

    if not data:
        return error_response('BAD_REQUEST', 'Request body is required', 400)

    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    # Validate username
    if not username or len(username) < 3 or len(username) > 50:
        return error_response('BAD_REQUEST', 'Username must be 3-50 characters', 400)

    # Validate email
    if not email or '@' not in email:
        return error_response('BAD_REQUEST', 'Valid email is required', 400)

    # Validate password
    if not password or len(password) < 6:
        return error_response('BAD_REQUEST', 'Password must be at least 6 characters', 400)

    # Check if username exists
    if User.query.filter_by(username=username).first():
        return error_response('CONFLICT', 'Username already taken', 409)

    # Check if email exists
    if User.query.filter_by(email=email).first():
        return error_response('CONFLICT', 'Email already registered', 409)

    # Create user
    user = User(username=username, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Generate tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201


@bp.route('/login', methods=['POST'])
def login():
    """
    Login and get JWT tokens
    ---
    tags:
      - Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: Username or email
              example: johndoe
            password:
              type: string
              description: Password
              example: secretpassword
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            message:
              type: string
            user:
              type: object
            accessToken:
              type: string
              description: JWT access token (15 min expiry)
            refreshToken:
              type: string
              description: JWT refresh token (30 day expiry)
      400:
        description: Bad request (missing credentials)
      401:
        description: Unauthorized (invalid credentials)
    """
    data = request.get_json()

    if not data:
        return error_response('BAD_REQUEST', 'Request body is required', 400)

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return error_response('BAD_REQUEST', 'Username and password are required', 400)

    # Find user by username or email
    user = User.query.filter(
        (User.username == username) | (User.email == username.lower())
    ).first()

    if not user or not user.check_password(password):
        return error_response('UNAUTHORIZED', 'Invalid username or password', 401)

    # Generate tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    description: |
      Use the refresh token in the Authorization header to get a new access token.
      Format: Authorization: Bearer <refresh_token>
    responses:
      200:
        description: New access token
        schema:
          type: object
          properties:
            accessToken:
              type: string
              description: New JWT access token (15 min expiry)
      401:
        description: Unauthorized (invalid/expired refresh token)
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return error_response('UNAUTHORIZED', 'User not found', 401)

    access_token = create_access_token(identity=user_id)

    return jsonify({
        'access_token': access_token
    }), 200


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    description: |
      Returns the currently authenticated user's information.
      Requires access token in Authorization header.
    responses:
      200:
        description: Current user info
        schema:
          type: object
          properties:
            id:
              type: string
            username:
              type: string
            email:
              type: string
            rateLimit:
              type: integer
              description: Requests per minute allowed
            createdAt:
              type: string
              format: date-time
      401:
        description: Unauthorized (missing/invalid token)
      404:
        description: User not found
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return error_response('NOT_FOUND', 'User not found', 404)

    return jsonify(user.to_dict()), 200
