"""POI endpoints."""
from flask import jsonify, request
from app.api import bp
from app.services import POIService


def error_response(code: str, message: str, status: int, details: dict = None):
    """Create standardized error response matching OpenAPI spec."""
    response = {
        'code': code,
        'message': message
    }
    if details:
        response['details'] = details
    return jsonify(response), status


@bp.route('/pois', methods=['GET'])
def list_pois():
    """
    List POIs with optional filters
    ---
    tags:
      - POIs
    parameters:
      - name: q
        in: query
        type: string
        required: false
        description: Text search (searches name and description)
      - name: category
        in: query
        type: string
        required: false
        description: Filter by category (e.g., beach, restaurant, museum)
      - name: lat
        in: query
        type: number
        required: false
        description: Latitude for proximity search
      - name: lon
        in: query
        type: number
        required: false
        description: Longitude for proximity search
      - name: radius
        in: query
        type: number
        required: false
        default: 5000
        description: Search radius in meters (used with lat/lon)
      - name: limit
        in: query
        type: integer
        required: false
        default: 50
        description: Max results (max 500)
      - name: offset
        in: query
        type: integer
        required: false
        default: 0
        description: Skip first N results
    responses:
      200:
        description: List of POIs matching the filters
        schema:
          type: object
          properties:
            query:
              type: object
              description: Echo of query parameters used
            count:
              type: integer
              description: Number of results returned
            total:
              type: integer
              description: Total matching results
            results:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  category:
                    type: string
                  description:
                    type: string
                  lat:
                    type: number
                  lon:
                    type: number
    """
    # Parse query parameters
    q = request.args.get('q')
    category = request.args.get('category')

    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', default=5000, type=float)

    limit = min(request.args.get('limit', default=50, type=int), 500)
    offset = request.args.get('offset', default=0, type=int)

    # Query POIs
    pois, total = POIService.get_all(
        q=q,
        category=category,
        lat=lat,
        lon=lon,
        radius=radius,
        limit=limit,
        offset=offset
    )

    return jsonify({
        'query': {
            'q': q,
            'category': category,
            'lat': lat,
            'lon': lon,
            'radius': radius if lat and lon else None,
            'limit': limit,
            'offset': offset
        },
        'count': len(pois),
        'total': total,
        'results': [poi.to_dict() for poi in pois]
    }), 200


@bp.route('/pois/<string:poi_id>', methods=['GET'])
def get_poi(poi_id):
    """
    Get a single POI by ID
    ---
    tags:
      - POIs
    parameters:
      - name: poi_id
        in: path
        type: string
        required: true
        description: The POI ID
    responses:
      200:
        description: POI details
        schema:
          type: object
          properties:
            id:
              type: string
            name:
              type: string
            category:
              type: string
            description:
              type: string
            lat:
              type: number
            lon:
              type: number
            osm_id:
              type: string
            tags:
              type: object
      404:
        description: POI not found
    """
    poi = POIService.get_by_id(poi_id)

    if not poi:
        return error_response('NOT_FOUND', f'POI with id {poi_id} not found', 404)

    return jsonify(poi.to_dict()), 200


@bp.route('/pois/categories', methods=['GET'])
def list_categories():
    """
    Get all available POI categories
    ---
    tags:
      - POIs
    responses:
      200:
        description: List of categories
        schema:
          type: object
          properties:
            count:
              type: integer
              description: Number of categories
            categories:
              type: array
              items:
                type: string
              example: ["beach", "restaurant", "museum", "hotel"]
    """
    categories = POIService.get_categories()

    return jsonify({
        'count': len(categories),
        'categories': categories
    }), 200
