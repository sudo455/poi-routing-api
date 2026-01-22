"""Route model for persisted routes with PostGIS support."""
import uuid
from datetime import datetime, timezone
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import LineString, mapping
from app.extensions import db


class RoutePOI(db.Model):
    """Association table for Route-POI relationship with ordering."""

    __tablename__ = 'route_pois'

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.String(36), db.ForeignKey('routes.id', ondelete='CASCADE'), nullable=False)
    poi_id = db.Column(db.String(36), db.ForeignKey('pois.id', ondelete='SET NULL'), nullable=True)

    # Position in the route sequence
    sequence_order = db.Column(db.Integer, nullable=False)

    # Cached POI name (in case POI is deleted)
    cached_name = db.Column(db.String(200))

    __table_args__ = (
        db.Index('idx_route_poi_order', 'route_id', 'sequence_order'),
    )


class Route(db.Model):
    """Persisted route model with PostGIS geometry."""

    __tablename__ = 'routes'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    public = db.Column(db.Boolean, default=False, index=True)
    vehicle = db.Column(db.String(20), default='car')

    # Owner relationship
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='SET NULL'), index=True)

    # PostGIS GEOGRAPHY LineString for route geometry
    geometry = db.Column(
        Geography(geometry_type='LINESTRING', srid=4326),
        nullable=False
    )

    # Optional encoded polyline for compact transfer
    encoded_polyline = db.Column(db.Text)

    # Route metadata from GraphHopper
    distance_meters = db.Column(db.Float)
    duration_millis = db.Column(db.Integer)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    poi_associations = db.relationship(
        'RoutePOI',
        backref='route',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='RoutePOI.sequence_order'
    )

    @classmethod
    def create_linestring(cls, coordinates: list):
        """
        Create PostGIS GEOGRAPHY LineString from coordinates.
        coordinates: list of [lon, lat] pairs (GeoJSON format)
        """
        line = LineString(coordinates)
        return from_shape(line, srid=4326)

    def get_geometry_geojson(self) -> dict:
        """Get geometry as GeoJSON."""
        if self.geometry:
            shape = to_shape(self.geometry)
            return mapping(shape)
        return None

    def set_geometry_from_geojson(self, geojson: dict) -> None:
        """Set geometry from GeoJSON LineString."""
        if geojson.get('type') == 'LineString':
            self.geometry = self.create_linestring(geojson['coordinates'])

    def set_geometry_from_coordinates(self, coordinates: list) -> None:
        """Set geometry from list of [lon, lat] coordinate pairs."""
        self.geometry = self.create_linestring(coordinates)

    def get_poi_sequence(self) -> list:
        """Get ordered list of POI references."""
        return [
            {
                'poiId': assoc.poi_id,
                'name': assoc.cached_name
            }
            for assoc in self.poi_associations.order_by(RoutePOI.sequence_order).all()
        ]

    def set_poi_sequence(self, poi_ids: list) -> None:
        """
        Set POI sequence from list of POI IDs.

        Args:
            poi_ids: List of POI ID strings
        """
        from app.models import POI

        # Clear existing
        RoutePOI.query.filter_by(route_id=self.id).delete()

        # Add new associations
        for i, poi_id in enumerate(poi_ids or []):
            # Get POI name for caching
            poi = db.session.get(POI, poi_id)
            cached_name = poi.name if poi else None

            assoc = RoutePOI(
                route_id=self.id,
                poi_id=poi_id,
                sequence_order=i,
                cached_name=cached_name
            )
            db.session.add(assoc)

    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            'id': self.id,
            'name': self.name,
            'public': self.public,
            'vehicle': self.vehicle,
            'ownerId': self.owner_id,
            'poiSequence': self.get_poi_sequence(),
            'geometry': self.get_geometry_geojson(),
            'encodedPolyline': self.encoded_polyline,
            'distanceMeters': self.distance_meters,
            'durationMillis': self.duration_millis,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self) -> str:
        return f'<Route {self.name}>'
