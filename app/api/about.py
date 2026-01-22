"""About endpoint - team information."""
from flask import jsonify
from app.api import bp


@bp.route('/about', methods=['GET'])
def about():
    """
    Get API development team information.
    ---
    tags:
      - About
    responses:
      200:
        description: Development team information
        content:
          application/json:
            schema:
              type: object
              properties:
                team:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                      name:
                        type: string
                      role:
                        type: string
    """
    return jsonify({
        'team': [
            {
                'id': 'inf2021163',
                'name': 'Angelos Moraitis',
                'role': 'Developer, DevOps'
            }
        ]
    }), 200
