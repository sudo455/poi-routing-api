"""GraphHopper routing service client."""
import requests
from typing import Optional
from flask import current_app


class GraphHopperError(Exception):
    """Custom exception for GraphHopper errors."""

    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GraphHopperClient:
    """Client for GraphHopper routing API."""

    SUPPORTED_VEHICLES = ['car', 'bike', 'foot', 'hike', 'mtb', 'racingbike']

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize GraphHopper client.

        Args:
            base_url: GraphHopper server URL (default from config)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or current_app.config.get(
            'GRAPHHOPPER_URL', 'http://localhost:8989'
        )
        self.timeout = timeout
        self.session = requests.Session()

    def health_check(self) -> bool:
        """Check if GraphHopper is available."""
        try:
            response = self.session.get(
                f'{self.base_url}/health',
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def compute_route(
        self,
        points: list[tuple[float, float]],
        vehicle: str = 'car',
        instructions: bool = True,
        points_encoded: bool = False
    ) -> dict:
        """
        Compute a route between points.

        Args:
            points: List of (latitude, longitude) tuples
            vehicle: Vehicle profile (car, bike, foot, etc.)
            instructions: Include turn-by-turn instructions
            points_encoded: Return encoded polyline instead of coordinates

        Returns:
            GraphHopper routing response with paths

        Raises:
            GraphHopperError: If routing fails
        """
        if len(points) < 2:
            raise GraphHopperError("At least 2 points required for routing", 400)

        if vehicle not in self.SUPPORTED_VEHICLES:
            raise GraphHopperError(
                f"Unsupported vehicle: {vehicle}. "
                f"Supported: {', '.join(self.SUPPORTED_VEHICLES)}",
                400
            )

        # Build query parameters
        # Note: GraphHopper 8.x+ uses 'profile' instead of 'vehicle'
        params = {
            'profile': vehicle,
            'instructions': str(instructions).lower(),
            'points_encoded': str(points_encoded).lower(),
            'locale': 'en',
            'type': 'json'
        }

        # Add points (GraphHopper expects point=lat,lon for each point)
        for lat, lon in points:
            params.setdefault('point', []).append(f'{lat},{lon}')

        try:
            response = self.session.get(
                f'{self.base_url}/route',
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()

            # Handle GraphHopper errors
            try:
                error_data = response.json()
                message = error_data.get('message', 'Unknown routing error')
            except Exception:
                message = f"GraphHopper returned status {response.status_code}"

            raise GraphHopperError(message, response.status_code)

        except requests.Timeout:
            raise GraphHopperError("GraphHopper request timed out", 504)
        except requests.ConnectionError:
            raise GraphHopperError("Cannot connect to GraphHopper service", 502)
        except requests.RequestException as e:
            raise GraphHopperError(f"Request failed: {str(e)}", 502)

    def route_from_pois(
        self,
        poi_ids: list[str],
        vehicle: str = 'car'
    ) -> dict:
        """
        Compute a route between POIs by their IDs.

        Args:
            poi_ids: List of POI IDs to route between
            vehicle: Vehicle profile

        Returns:
            GraphHopper routing response
        """
        from app.models import POI
        from app.extensions import db

        if len(poi_ids) < 2:
            raise GraphHopperError("At least 2 POIs required for routing", 400)

        points = []
        for poi_id in poi_ids:
            poi = db.session.get(POI, poi_id)
            if not poi:
                raise GraphHopperError(f"POI not found: {poi_id}", 404)
            points.append((poi.latitude, poi.longitude))

        return self.compute_route(points, vehicle=vehicle)

    def extract_route_geometry(self, routing_response: dict) -> dict:
        """
        Extract GeoJSON geometry from GraphHopper response.

        Args:
            routing_response: GraphHopper routing response

        Returns:
            Dict with GeoJSON LineString and metadata
        """
        if not routing_response.get('paths'):
            raise GraphHopperError("No route found", 404)

        path = routing_response['paths'][0]

        # Extract coordinates from points
        points = path.get('points', {})
        if isinstance(points, dict):
            # GeoJSON format
            coordinates = points.get('coordinates', [])
        else:
            # Encoded polyline - shouldn't happen if points_encoded=False
            raise GraphHopperError("Unexpected points format", 500)

        return {
            'type': 'LineString',
            'coordinates': coordinates,
            'properties': {
                'distance_meters': path.get('distance', 0),
                'duration_millis': path.get('time', 0),
                'ascend': path.get('ascend', 0),
                'descend': path.get('descend', 0)
            }
        }
