"""API Blueprint."""
from flask import Blueprint

bp = Blueprint('api', __name__)

from app.api import about, pois, routes
