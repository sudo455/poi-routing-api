"""POI (Point of Interest) model with PostGIS support."""
import uuid
from datetime import datetime, timezone
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point
from app.extensions import db


class POI(db.Model):
    """Point of Interest model with PostGIS GEOGRAPHY."""

    __tablename__ = 'pois'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(50), index=True)
    description = db.Column(db.Text)

    # PostGIS GEOGRAPHY type for accurate distance calculations
    # SRID 4326 = WGS84 (standard GPS coordinates)
    location = db.Column(
        Geography(geometry_type='POINT', srid=4326),
        nullable=False
    )

    # Additional properties as JSON
    properties = db.Column(db.JSON, default=dict)

    # OSM reference (if imported from OpenStreetMap)
    osm_id = db.Column(db.BigInteger, index=True)
    osm_type = db.Column(db.String(10))  # node, way, relation

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Spatial index is automatically created for Geography columns

    @property
    def latitude(self) -> float:
        """Get latitude from PostGIS point."""
        if self.location:
            point = to_shape(self.location)
            return point.y
        return None

    @property
    def longitude(self) -> float:
        """Get longitude from PostGIS point."""
        if self.location:
            point = to_shape(self.location)
            return point.x
        return None

    @classmethod
    def create_point(cls, lat: float, lon: float):
        """Create a PostGIS GEOGRAPHY point from lat/lon."""
        point = Point(lon, lat)  # Note: PostGIS uses (lon, lat) order
        return from_shape(point, srid=4326)

    def set_location(self, lat: float, lon: float) -> None:
        """Set location from lat/lon coordinates."""
        self.location = self.create_point(lat, lon)

    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'location': {
                'lat': self.latitude,
                'lon': self.longitude
            },
            'properties': self.properties or {}
        }

    def __repr__(self) -> str:
        return f'<POI {self.name}>'
