"""API tests covering all OpenAPI spec endpoints."""
import pytest


class TestAbout:
    """Tests for /about endpoint."""

    def test_about_returns_team(self, client):
        """GET /about returns team info."""
        response = client.get('/api/v1/about')
        assert response.status_code == 200
        assert 'team' in response.json
        assert isinstance(response.json['team'], list)
        assert len(response.json['team']) > 0
        # Each team member should have id and name
        for member in response.json['team']:
            assert 'id' in member
            assert 'name' in member


class TestHealth:
    """Tests for /health endpoint."""

    def test_health(self, client):
        """GET /health returns healthy status."""
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json['status'] == 'healthy'


class TestPOIs:
    """Tests for /pois endpoints."""

    def test_pois_list(self, client):
        """GET /pois returns list of POIs."""
        response = client.get('/api/v1/pois')
        assert response.status_code == 200
        assert 'results' in response.json
        assert 'count' in response.json
        assert 'query' in response.json
        assert isinstance(response.json['results'], list)

    def test_pois_list_with_limit(self, client):
        """GET /pois with limit parameter."""
        response = client.get('/api/v1/pois?limit=5')
        assert response.status_code == 200
        assert response.json['query']['limit'] == 5

    def test_pois_list_with_offset(self, client):
        """GET /pois with offset parameter."""
        response = client.get('/api/v1/pois?offset=10')
        assert response.status_code == 200
        assert response.json['query']['offset'] == 10

    def test_pois_search_by_text(self, client):
        """GET /pois with q parameter for text search."""
        response = client.get('/api/v1/pois?q=beach')
        assert response.status_code == 200
        assert response.json['query']['q'] == 'beach'

    def test_pois_filter_by_category(self, client):
        """GET /pois with category filter."""
        response = client.get('/api/v1/pois?category=restaurant')
        assert response.status_code == 200
        assert response.json['query']['category'] == 'restaurant'

    def test_pois_proximity_search(self, client):
        """GET /pois with lat, lon, radius for proximity search."""
        response = client.get('/api/v1/pois?lat=39.62&lon=19.92&radius=5000')
        assert response.status_code == 200
        assert response.json['query']['lat'] == 39.62
        assert response.json['query']['lon'] == 19.92
        assert response.json['query']['radius'] == 5000.0

    def test_pois_categories(self, client):
        """GET /pois/categories returns available categories."""
        response = client.get('/api/v1/pois/categories')
        assert response.status_code == 200
        assert 'categories' in response.json
        assert isinstance(response.json['categories'], list)

    def test_poi_not_found(self, client):
        """GET /pois/{id} returns 404 for non-existent POI."""
        response = client.get('/api/v1/pois/nonexistent-id')
        assert response.status_code == 404
        assert response.json['code'] == 'NOT_FOUND'


class TestRoutesCompute:
    """Tests for /routes/compute endpoint."""

    def test_compute_requires_locations(self, client):
        """POST /routes/compute requires locations array."""
        response = client.post('/api/v1/routes/compute', json={
            'vehicle': 'car'
        })
        assert response.status_code == 400
        assert response.json['code'] == 'BAD_REQUEST'
        assert 'locations' in response.json['message'].lower()

    def test_compute_requires_min_2_locations(self, client):
        """POST /routes/compute requires at least 2 locations."""
        response = client.post('/api/v1/routes/compute', json={
            'locations': [{'lat': 39.6, 'lon': 19.9}]
        })
        assert response.status_code == 400
        assert 'At least 2 locations' in response.json['message']

    def test_compute_validates_location_format(self, client):
        """POST /routes/compute validates location format."""
        response = client.post('/api/v1/routes/compute', json={
            'locations': [
                {'invalid': 'data'},
                {'lat': 39.65, 'lon': 19.85}
            ]
        })
        assert response.status_code == 400


class TestRoutes:
    """Tests for /routes CRUD endpoints."""

    def get_auth_token(self, client, username='routetest'):
        """Helper to get auth token."""
        client.post('/api/v1/auth/register', json={
            'username': username,
            'email': f'{username}@example.com',
            'password': 'testpass123'
        })
        response = client.post('/api/v1/auth/login', json={
            'username': username,
            'password': 'testpass123'
        })
        return response.json['access_token']

    def test_routes_list(self, client):
        """GET /routes returns list of routes."""
        response = client.get('/api/v1/routes')
        assert response.status_code == 200
        assert 'results' in response.json
        assert 'count' in response.json

    def test_routes_list_filter_public(self, client):
        """GET /routes with public filter."""
        response = client.get('/api/v1/routes?public=true')
        assert response.status_code == 200

    def test_routes_list_with_limit_offset(self, client):
        """GET /routes with limit and offset."""
        response = client.get('/api/v1/routes?limit=5&offset=0')
        assert response.status_code == 200

    def test_routes_create_requires_auth(self, client):
        """POST /routes requires authentication."""
        response = client.post('/api/v1/routes', json={
            'name': 'Test Route',
            'public': True,
            'geometry': {'type': 'LineString', 'coordinates': [[19.92, 39.62], [19.85, 39.65]]}
        })
        assert response.status_code == 401

    def test_routes_create(self, client):
        """POST /routes creates a new route."""
        token = self.get_auth_token(client, 'createroute')
        response = client.post('/api/v1/routes',
            json={
                'name': 'Test Route',
                'public': True,
                'geometry': {'type': 'LineString', 'coordinates': [[19.92, 39.62], [19.85, 39.65]]}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 201
        assert response.json['name'] == 'Test Route'
        assert response.json['public'] == True
        assert 'id' in response.json

    def test_routes_create_requires_name(self, client):
        """POST /routes requires name."""
        token = self.get_auth_token(client, 'noname')
        response = client.post('/api/v1/routes',
            json={
                'public': True,
                'geometry': {'type': 'LineString', 'coordinates': [[19.92, 39.62], [19.85, 39.65]]}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 400

    def test_routes_create_requires_geometry(self, client):
        """POST /routes requires geometry."""
        token = self.get_auth_token(client, 'nogeom')
        response = client.post('/api/v1/routes',
            json={
                'name': 'Test Route',
                'public': True
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 400

    def test_routes_get_by_id(self, client):
        """GET /routes/{id} returns route details."""
        token = self.get_auth_token(client, 'getroute')
        # Create a route first
        create_response = client.post('/api/v1/routes',
            json={
                'name': 'Route to Get',
                'public': True,
                'geometry': {'type': 'LineString', 'coordinates': [[19.92, 39.62], [19.85, 39.65]]}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        route_id = create_response.json['id']

        # Get the route
        response = client.get(f'/api/v1/routes/{route_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        assert response.json['id'] == route_id
        assert response.json['name'] == 'Route to Get'

    def test_routes_get_not_found(self, client):
        """GET /routes/{id} returns 404 for non-existent route."""
        token = self.get_auth_token(client, 'notfound')
        response = client.get('/api/v1/routes/nonexistent-id',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 404

    def test_routes_put_update(self, client):
        """PUT /routes/{id} fully updates a route."""
        token = self.get_auth_token(client, 'putroute')
        # Create a route first
        create_response = client.post('/api/v1/routes',
            json={
                'name': 'Original Name',
                'public': False,
                'geometry': {'type': 'LineString', 'coordinates': [[19.92, 39.62], [19.85, 39.65]]}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        route_id = create_response.json['id']

        # Update the route
        response = client.put(f'/api/v1/routes/{route_id}',
            json={
                'name': 'Updated Name',
                'public': True,
                'geometry': {'type': 'LineString', 'coordinates': [[19.90, 39.60], [19.80, 39.70]]}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        assert response.json['name'] == 'Updated Name'
        assert response.json['public'] == True

    def test_routes_patch_update(self, client):
        """PATCH /routes/{id} partially updates a route."""
        token = self.get_auth_token(client, 'patchroute')
        # Create a route first
        create_response = client.post('/api/v1/routes',
            json={
                'name': 'Original Name',
                'public': False,
                'geometry': {'type': 'LineString', 'coordinates': [[19.92, 39.62], [19.85, 39.65]]}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        route_id = create_response.json['id']

        # Patch only the name
        response = client.patch(f'/api/v1/routes/{route_id}',
            json={'name': 'Patched Name'},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        assert response.json['name'] == 'Patched Name'
        assert response.json['public'] == False  # Unchanged

    def test_routes_delete(self, client):
        """DELETE /routes/{id} deletes a route."""
        token = self.get_auth_token(client, 'deleteroute')
        # Create a route first
        create_response = client.post('/api/v1/routes',
            json={
                'name': 'Route to Delete',
                'public': True,
                'geometry': {'type': 'LineString', 'coordinates': [[19.92, 39.62], [19.85, 39.65]]}
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        route_id = create_response.json['id']

        # Delete the route
        response = client.delete(f'/api/v1/routes/{route_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f'/api/v1/routes/{route_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert get_response.status_code == 404

    def test_routes_delete_not_found(self, client):
        """DELETE /routes/{id} returns 404 for non-existent route."""
        token = self.get_auth_token(client, 'deletenf')
        response = client.delete('/api/v1/routes/nonexistent-id',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 404


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_fun_message(self, client):
        """404 errors return fun messages."""
        response = client.get('/api/v1/nonexistent')
        assert response.status_code == 404
        assert 'code' in response.json
        assert response.json['code'] == 'NOT_FOUND'
        assert 'message' in response.json
        # Should be a fun message, not just "Not Found"
        assert len(response.json['message']) > 10

    def test_request_id_in_response(self, client):
        """Responses include request ID."""
        response = client.get('/api/v1/nonexistent')
        assert 'requestId' in response.json
