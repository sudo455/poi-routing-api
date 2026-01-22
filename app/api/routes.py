"""Routes endpoints."""
from flask import jsonify, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api import bp
from app.extensions import db
from app.models import Route, RoutePOI, POI
from app.services import GraphHopperClient, GraphHopperError


def error_response(code: str, message: str, status: int, details: dict = None):
    """Create standardized error response matching OpenAPI spec."""
    response = {
        'code': code,
        'message': message
    }
    if details:
        response['details'] = details
    return jsonify(response), status


@bp.route('/routes/compute', methods=['POST'])
def compute_route():
    """
    Compute a route between locations
    ---
    tags:
      - Routes
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - locations
          properties:
            locations:
              type: array
              minItems: 2
              description: Array of locations (each with poiId OR lat/lon)
              items:
                type: object
                properties:
                  poiId:
                    type: string
                    description: POI ID (alternative to coordinates)
                  lat:
                    type: number
                    description: Latitude (required if no poiId)
                  lon:
                    type: number
                    description: Longitude (required if no poiId)
              example:
                - poiId: "abc123"
                - lat: 39.6243
                  lon: 19.9217
            vehicle:
              type: string
              description: Vehicle profile
              enum: [car, bike, foot]
              default: car
            algorithm:
              type: string
              description: Routing algorithm
              enum: [shortest, fastest]
              default: shortest
            format:
              type: string
              description: Response geometry format
              enum: [geojson, encodedpolyline]
              default: geojson
    responses:
      200:
        description: Computed route
        schema:
          type: object
          properties:
            vehicle:
              type: string
            algorithm:
              type: string
            format:
              type: string
            locations:
              type: array
              description: Resolved locations with coordinates
            geometry:
              type: object
              description: GeoJSON LineString (if format=geojson)
            encodedPolyline:
              type: string
              description: Encoded polyline (if format=encodedpolyline)
            distanceMeters:
              type: number
            durationMillis:
              type: number
      400:
        description: Bad request (missing/invalid parameters)
      404:
        description: POI not found
      502:
        description: GraphHopper routing error
    """
    data = request.get_json()

    if not data:
        return error_response('BAD_REQUEST', 'Request body is required', 400)

    locations = data.get('locations')
    vehicle = data.get('vehicle', 'car')
    algorithm = data.get('algorithm', 'shortest')
    response_format = data.get('format', 'geojson')

    # Validate locations
    if not locations:
        return error_response('BAD_REQUEST', 'locations array is required', 400)

    if not isinstance(locations, list):
        return error_response('BAD_REQUEST', 'locations must be an array', 400)

    if len(locations) < 2:
        return error_response('BAD_REQUEST', 'At least 2 locations required for routing', 400)

    # Validate format
    if response_format not in ('geojson', 'encodedpolyline'):
        return error_response('BAD_REQUEST', 'format must be geojson or encodedpolyline', 400)

    # Validate algorithm
    if algorithm not in ('shortest', 'fastest'):
        return error_response('BAD_REQUEST', 'algorithm must be shortest or fastest', 400)

    # Validate vehicle
    if vehicle not in ('car', 'bike', 'foot'):
        return error_response('BAD_REQUEST', 'vehicle must be car, bike, or foot', 400)

    try:
        client = GraphHopperClient()
        route_points = []
        resolved_locations = []

        for i, loc in enumerate(locations):
            if not isinstance(loc, dict):
                return error_response('BAD_REQUEST', f'Location {i} must be an object', 400)

            poi_id = loc.get('poiId')
            lat = loc.get('lat')
            lon = loc.get('lon')

            # Must have either poiId OR (lat AND lon)
            if poi_id:
                # Resolve POI to coordinates
                poi = db.session.get(POI,poi_id)
                if not poi:
                    return error_response('NOT_FOUND', f'POI not found: {poi_id}', 404)
                route_points.append((poi.latitude, poi.longitude))
                resolved_locations.append({
                    'poiId': poi_id,
                    'name': poi.name,
                    'lat': poi.latitude,
                    'lon': poi.longitude
                })
            elif lat is not None and lon is not None:
                # Use direct coordinates
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                except (ValueError, TypeError):
                    return error_response('BAD_REQUEST', f'Location {i}: lat/lon must be numbers', 400)
                route_points.append((lat_f, lon_f))
                resolved_locations.append({
                    'lat': lat_f,
                    'lon': lon_f
                })
            else:
                return error_response(
                    'BAD_REQUEST',
                    f'Location {i}: must have either poiId or both lat and lon',
                    400
                )

        # Compute route with GraphHopper
        response = client.compute_route(route_points, vehicle=vehicle)
        geometry = client.extract_route_geometry(response)

        # Build response
        result = {
            'vehicle': vehicle,
            'algorithm': algorithm,
            'format': response_format,
            'locations': resolved_locations,
            'distanceMeters': geometry['properties']['distance_meters'],
            'durationMillis': geometry['properties']['duration_millis']
        }

        if response_format == 'geojson':
            result['geometry'] = {
                'type': 'LineString',
                'coordinates': geometry['coordinates']
            }
        else:
            # encodedpolyline - get from GraphHopper if available
            result['encodedPolyline'] = response.get('paths', [{}])[0].get('points', '')

        return jsonify(result), 200

    except GraphHopperError as e:
        return error_response('ROUTING_ERROR', e.message, e.status_code)


@bp.route('/routes', methods=['GET'])
def list_routes():
    """
    List saved routes
    ---
    tags:
      - Routes
    parameters:
      - name: public
        in: query
        type: boolean
        required: false
        description: Filter by public/private status
      - name: ownerId
        in: query
        type: string
        required: false
        description: Filter by owner ID
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
        description: List of saved routes
        schema:
          type: object
          properties:
            count:
              type: integer
            total:
              type: integer
            results:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  public:
                    type: boolean
                  vehicle:
                    type: string
                  distanceMeters:
                    type: number
                  durationMillis:
                    type: number
    """
    # Filter by public status
    public = request.args.get('public', type=lambda x: x.lower() == 'true')
    owner_id = request.args.get('ownerId')

    limit = min(request.args.get('limit', default=50, type=int), 500)
    offset = request.args.get('offset', default=0, type=int)

    query = Route.query

    if public is not None:
        query = query.filter(Route.public == public)

    if owner_id:
        query = query.filter(Route.owner_id == owner_id)

    total = query.count()
    routes = query.order_by(Route.created_at.desc()).limit(limit).offset(offset).all()

    return jsonify({
        'count': len(routes),
        'total': total,
        'results': [route.to_dict() for route in routes]
    }), 200


@bp.route('/routes', methods=['POST'])
@jwt_required()
def create_route():
    """
    Save a computed route
    ---
    tags:
      - Routes
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
            - geometry
          properties:
            name:
              type: string
              description: Route name
            geometry:
              type: object
              description: GeoJSON LineString
              properties:
                type:
                  type: string
                  enum: [LineString]
                coordinates:
                  type: array
                  items:
                    type: array
                    items:
                      type: number
            poiSequence:
              type: array
              description: POI IDs in route sequence
              items:
                type: string
            public:
              type: boolean
              default: false
            vehicle:
              type: string
              default: car
            distanceMeters:
              type: number
            durationMillis:
              type: number
    responses:
      201:
        description: Route created
      400:
        description: Bad request (missing/invalid fields)
    """
    data = request.get_json()

    if not data:
        return error_response('BAD_REQUEST', 'Request body is required', 400)

    name = data.get('name')
    geometry = data.get('geometry')

    if not name:
        return error_response('BAD_REQUEST', 'Route name is required', 400)

    if not geometry:
        return error_response('BAD_REQUEST', 'Route geometry is required', 400)

    # Validate geometry is a LineString
    if geometry.get('type') != 'LineString':
        return error_response('BAD_REQUEST', 'Geometry must be a GeoJSON LineString', 400)

    coordinates = geometry.get('coordinates', [])
    if len(coordinates) < 2:
        return error_response('BAD_REQUEST', 'LineString must have at least 2 coordinates', 400)

    # Create route
    route = Route(
        name=name,
        public=data.get('public', False),
        vehicle=data.get('vehicle', 'car'),
        distance_meters=data.get('distanceMeters'),
        duration_millis=data.get('durationMillis'),
        owner_id=get_jwt_identity()  # Set from JWT
    )

    # Set geometry from coordinates
    route.set_geometry_from_coordinates(coordinates)

    db.session.add(route)

    # Handle POI sequence if provided (using poiSequence, not poi_ids)
    poi_sequence = data.get('poiSequence', [])
    if poi_sequence:
        route.set_poi_sequence(poi_sequence)

    db.session.commit()

    return jsonify(route.to_dict()), 201


@bp.route('/routes/<string:route_id>', methods=['GET'])
def get_route(route_id):
    """
    Get a single route by ID
    ---
    tags:
      - Routes
    parameters:
      - name: route_id
        in: path
        type: string
        required: true
        description: The route ID
    responses:
      200:
        description: Route details with geometry
        schema:
          type: object
          properties:
            id:
              type: string
            name:
              type: string
            public:
              type: boolean
            vehicle:
              type: string
            distanceMeters:
              type: number
            durationMillis:
              type: number
            geometry:
              type: object
            poiSequence:
              type: array
      404:
        description: Route not found
    """
    route = db.session.get(Route,route_id)

    if not route:
        return error_response('NOT_FOUND', f'Route with id {route_id} not found', 404)

    return jsonify(route.to_dict()), 200


@bp.route('/routes/<string:route_id>', methods=['PUT'])
def update_route(route_id):
    """
    Update a route (full replacement)
    ---
    tags:
      - Routes
    parameters:
      - name: route_id
        in: path
        type: string
        required: true
        description: The route ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            geometry:
              type: object
            poiSequence:
              type: array
              items:
                type: string
            public:
              type: boolean
            vehicle:
              type: string
            distanceMeters:
              type: number
            durationMillis:
              type: number
    responses:
      200:
        description: Route updated
      400:
        description: Bad request
      404:
        description: Route not found
    """
    route = db.session.get(Route,route_id)

    if not route:
        return error_response('NOT_FOUND', f'Route with id {route_id} not found', 404)

    data = request.get_json()

    if not data:
        return error_response('BAD_REQUEST', 'Request body is required', 400)

    # Update fields
    if 'name' in data:
        route.name = data['name']

    if 'public' in data:
        route.public = data['public']

    if 'vehicle' in data:
        route.vehicle = data['vehicle']

    if 'distanceMeters' in data:
        route.distance_meters = data['distanceMeters']

    if 'durationMillis' in data:
        route.duration_millis = data['durationMillis']

    if 'geometry' in data:
        geometry = data['geometry']
        if geometry.get('type') != 'LineString':
            return error_response('BAD_REQUEST', 'Geometry must be a GeoJSON LineString', 400)
        route.set_geometry_from_coordinates(geometry.get('coordinates', []))

    if 'poiSequence' in data:
        route.set_poi_sequence(data['poiSequence'])

    db.session.commit()

    return jsonify(route.to_dict()), 200


@bp.route('/routes/<string:route_id>', methods=['PATCH'])
def patch_route(route_id):
    """
    Partially update a route
    ---
    tags:
      - Routes
    parameters:
      - name: route_id
        in: path
        type: string
        required: true
        description: The route ID
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            public:
              type: boolean
            vehicle:
              type: string
    responses:
      200:
        description: Route updated
      400:
        description: Bad request
      404:
        description: Route not found
    """
    # PATCH is the same as PUT for our purposes
    return update_route(route_id)


@bp.route('/routes/<string:route_id>', methods=['DELETE'])
def delete_route(route_id):
    """
    Delete a route
    ---
    tags:
      - Routes
    parameters:
      - name: route_id
        in: path
        type: string
        required: true
        description: The route ID
    responses:
      204:
        description: Route deleted
      404:
        description: Route not found
    """
    route = db.session.get(Route,route_id)

    if not route:
        return error_response('NOT_FOUND', f'Route with id {route_id} not found', 404)

    db.session.delete(route)
    db.session.commit()

    return '', 204
