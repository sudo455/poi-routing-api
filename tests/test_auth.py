"""Authentication tests covering all OpenAPI spec auth endpoints."""
import pytest


class TestRegister:
    """Tests for POST /auth/register endpoint."""

    def test_register_success(self, client):
        """POST /auth/register creates a new user."""
        response = client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        assert response.status_code == 201
        assert 'access_token' in response.json
        assert 'refresh_token' in response.json
        assert 'user' in response.json
        assert response.json['user']['username'] == 'testuser'
        assert response.json['user']['email'] == 'test@example.com'
        assert 'id' in response.json['user']

    def test_register_duplicate_username(self, client):
        """POST /auth/register rejects duplicate username."""
        # First registration
        client.post('/api/v1/auth/register', json={
            'username': 'duplicate',
            'email': 'first@example.com',
            'password': 'testpass123'
        })

        # Try to register with same username
        response = client.post('/api/v1/auth/register', json={
            'username': 'duplicate',
            'email': 'second@example.com',
            'password': 'testpass123'
        })
        assert response.status_code == 409
        assert response.json['code'] == 'CONFLICT'

    def test_register_duplicate_email(self, client):
        """POST /auth/register rejects duplicate email."""
        # First registration
        client.post('/api/v1/auth/register', json={
            'username': 'first',
            'email': 'duplicate@example.com',
            'password': 'testpass123'
        })

        # Try to register with same email
        response = client.post('/api/v1/auth/register', json={
            'username': 'second',
            'email': 'duplicate@example.com',
            'password': 'testpass123'
        })
        assert response.status_code == 409
        assert response.json['code'] == 'CONFLICT'

    def test_register_missing_username(self, client):
        """POST /auth/register requires username."""
        response = client.post('/api/v1/auth/register', json={
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        assert response.status_code == 400

    def test_register_missing_email(self, client):
        """POST /auth/register requires email."""
        response = client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'password': 'testpass123'
        })
        assert response.status_code == 400

    def test_register_missing_password(self, client):
        """POST /auth/register requires password."""
        response = client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com'
        })
        assert response.status_code == 400

    def test_register_short_username(self, client):
        """POST /auth/register rejects username shorter than 3 chars."""
        response = client.post('/api/v1/auth/register', json={
            'username': 'ab',
            'email': 'short@example.com',
            'password': 'testpass123'
        })
        assert response.status_code == 400
        assert 'Username' in response.json['message']

    def test_register_invalid_email(self, client):
        """POST /auth/register rejects invalid email."""
        response = client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'invalidemail',
            'password': 'testpass123'
        })
        assert response.status_code == 400
        assert 'email' in response.json['message'].lower()

    def test_register_short_password(self, client):
        """POST /auth/register rejects password shorter than 6 chars."""
        response = client.post('/api/v1/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '12345'
        })
        assert response.status_code == 400
        assert 'Password' in response.json['message']


class TestLogin:
    """Tests for POST /auth/login endpoint."""

    def test_login_success(self, client):
        """POST /auth/login with valid credentials."""
        # Register first
        client.post('/api/v1/auth/register', json={
            'username': 'logintest',
            'email': 'login@example.com',
            'password': 'testpass123'
        })

        # Login
        response = client.post('/api/v1/auth/login', json={
            'username': 'logintest',
            'password': 'testpass123'
        })
        assert response.status_code == 200
        assert 'access_token' in response.json
        assert 'refresh_token' in response.json
        assert 'user' in response.json
        assert response.json['user']['username'] == 'logintest'

    def test_login_with_email(self, client):
        """POST /auth/login works with email instead of username."""
        # Register first
        client.post('/api/v1/auth/register', json={
            'username': 'emaillogin',
            'email': 'emaillogin@example.com',
            'password': 'testpass123'
        })

        # Login with email
        response = client.post('/api/v1/auth/login', json={
            'username': 'emaillogin@example.com',
            'password': 'testpass123'
        })
        assert response.status_code == 200
        assert 'access_token' in response.json

    def test_login_invalid_password(self, client):
        """POST /auth/login rejects wrong password."""
        # Register first
        client.post('/api/v1/auth/register', json={
            'username': 'wrongpass',
            'email': 'wrong@example.com',
            'password': 'testpass123'
        })

        # Login with wrong password
        response = client.post('/api/v1/auth/login', json={
            'username': 'wrongpass',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401
        assert response.json['code'] == 'UNAUTHORIZED'

    def test_login_nonexistent_user(self, client):
        """POST /auth/login rejects non-existent user."""
        response = client.post('/api/v1/auth/login', json={
            'username': 'nonexistent',
            'password': 'testpass123'
        })
        assert response.status_code == 401
        assert response.json['code'] == 'UNAUTHORIZED'

    def test_login_missing_username(self, client):
        """POST /auth/login requires username."""
        response = client.post('/api/v1/auth/login', json={
            'password': 'testpass123'
        })
        assert response.status_code == 400

    def test_login_missing_password(self, client):
        """POST /auth/login requires password."""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser'
        })
        assert response.status_code == 400


class TestRefresh:
    """Tests for POST /auth/refresh endpoint."""

    def test_refresh_success(self, client):
        """POST /auth/refresh returns new access token."""
        # Register and get tokens
        reg_response = client.post('/api/v1/auth/register', json={
            'username': 'refreshtest',
            'email': 'refresh@example.com',
            'password': 'testpass123'
        })
        refresh_token = reg_response.json['refresh_token']

        # Refresh
        response = client.post('/api/v1/auth/refresh',
            headers={'Authorization': f'Bearer {refresh_token}'}
        )
        assert response.status_code == 200
        assert 'access_token' in response.json

    def test_refresh_with_access_token_fails(self, client):
        """POST /auth/refresh fails with access token (needs refresh token)."""
        # Register and get tokens
        reg_response = client.post('/api/v1/auth/register', json={
            'username': 'refreshfail',
            'email': 'refreshfail@example.com',
            'password': 'testpass123'
        })
        access_token = reg_response.json['access_token']

        # Try to refresh with access token
        response = client.post('/api/v1/auth/refresh',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        assert response.status_code == 422  # JWT type mismatch

    def test_refresh_without_token(self, client):
        """POST /auth/refresh requires authorization header."""
        response = client.post('/api/v1/auth/refresh')
        assert response.status_code == 401


class TestMe:
    """Tests for GET /auth/me endpoint."""

    def test_me_authenticated(self, client):
        """GET /auth/me returns user info with valid token."""
        # Register and get token
        reg_response = client.post('/api/v1/auth/register', json={
            'username': 'metest',
            'email': 'me@example.com',
            'password': 'testpass123'
        })
        token = reg_response.json['access_token']

        # Access /me with token
        response = client.get('/api/v1/auth/me',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        assert response.json['username'] == 'metest'
        assert response.json['email'] == 'me@example.com'
        assert 'id' in response.json
        assert 'rateLimit' in response.json

    def test_me_unauthenticated(self, client):
        """GET /auth/me requires authentication."""
        response = client.get('/api/v1/auth/me')
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        """GET /auth/me rejects invalid token."""
        response = client.get('/api/v1/auth/me',
            headers={'Authorization': 'Bearer invalidtoken123'}
        )
        assert response.status_code == 422  # Invalid token format
