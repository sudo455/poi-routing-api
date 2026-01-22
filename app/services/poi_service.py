"""POI Service - business logic for POI operations."""
from typing import Optional
from sqlalchemy import func, or_
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.extensions import db
from app.models import POI


class POIService:
    """Service class for POI operations."""

    @staticmethod
    def get_all(
        q: Optional[str] = None,
        category: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: float = 5000,  # meters
        limit: int = 20,
        offset: int = 0
    ) -> tuple[list[POI], int]:
        """
        Query POIs with optional filters.

        Args:
            q: Text search query (searches name and description)
            category: Filter by category
            lat, lon: Center point for proximity search
            radius: Search radius in meters (default 5000m = 5km)
            limit: Max results to return
            offset: Skip first N results

        Returns:
            Tuple of (list of POIs, total count)
        """
        query = POI.query

        # Text search
        if q:
            search_term = f'%{q}%'
            query = query.filter(
                or_(
                    POI.name.ilike(search_term),
                    POI.description.ilike(search_term)
                )
            )

        # Category filter
        if category:
            query = query.filter(POI.category == category)

        # Proximity search using PostGIS
        if lat is not None and lon is not None:
            # Create a point from coordinates
            point = func.ST_SetSRID(ST_MakePoint(lon, lat), 4326)

            # Filter by distance
            query = query.filter(
                ST_DWithin(
                    POI.location,
                    func.ST_GeogFromText(f'POINT({lon} {lat})'),
                    radius
                )
            )

            # Order by distance
            query = query.order_by(
                ST_Distance(
                    POI.location,
                    func.ST_GeogFromText(f'POINT({lon} {lat})')
                )
            )
        else:
            # Default ordering by name
            query = query.order_by(POI.name)

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        pois = query.limit(limit).offset(offset).all()

        return pois, total

    @staticmethod
    def get_by_id(poi_id: str) -> Optional[POI]:
        """Get a single POI by ID."""
        return db.session.get(POI, poi_id)

    @staticmethod
    def get_categories() -> list[str]:
        """Get all unique categories."""
        result = db.session.query(POI.category).distinct().filter(
            POI.category.isnot(None)
        ).order_by(POI.category).all()
        return [r[0] for r in result]

    @staticmethod
    def create(
        name: str,
        latitude: float,
        longitude: float,
        category: Optional[str] = None,
        description: Optional[str] = None,
        properties: Optional[dict] = None,
        osm_id: Optional[int] = None,
        osm_type: Optional[str] = None
    ) -> POI:
        """Create a new POI."""
        poi = POI(
            name=name,
            category=category,
            description=description,
            properties=properties or {},
            osm_id=osm_id,
            osm_type=osm_type
        )
        poi.set_location(latitude, longitude)

        db.session.add(poi)
        db.session.commit()

        return poi

    @staticmethod
    def bulk_create(pois_data: list[dict]) -> int:
        """
        Bulk create POIs from a list of dictionaries.

        Returns the number of POIs created.
        """
        created = 0

        for data in pois_data:
            # Skip if OSM ID already exists
            if data.get('osm_id'):
                existing = POI.query.filter_by(osm_id=data['osm_id']).first()
                if existing:
                    continue

            poi = POI(
                name=data['name'],
                category=data.get('category'),
                description=data.get('description'),
                properties=data.get('properties', {}),
                osm_id=data.get('osm_id'),
                osm_type=data.get('osm_type')
            )
            poi.set_location(data['latitude'], data['longitude'])
            db.session.add(poi)
            created += 1

        db.session.commit()
        return created
