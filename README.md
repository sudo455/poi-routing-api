# POI & Routing API

> **Ιόνιο Πανεπιστήμιο - Τμήμα Πληροφορικής**
> Προχωρημένες Τεχνολογίες Διαδικτύου 2024-2025

## Ομάδα Ανάπτυξης

| Α.Μ. | Ονοματεπώνυμο | Ρόλος |
|------|---------------|-------|
| inf2021163 | Άγγελος Μωραΐτης | Developer, DevOps |

---

A RESTful API for Point of Interest (POI) search and route planning in Corfu, Greece. Built with Flask, PostgreSQL/PostGIS, and GraphHopper.

## Features

- **POI Search**: Text search, category filters, proximity search with PostGIS
- **Route Planning**: Compute routes between POIs or coordinates via GraphHopper
- **Route Persistence**: Save, update, and share computed routes
- **JWT Authentication**: Secure endpoints with access/refresh tokens
- **Rate Limiting**: Per-user rate limits with fun HTTP 418 "I'm a teapot" responses
- **Web UI**: Interactive map with LeafletJS for visual route planning
- **Swagger Docs**: Full OpenAPI documentation at `/apidocs`

## Quick Start

### Prerequisites
- Docker & Docker Compose
- ~4GB RAM (GraphHopper needs memory for OSM routing)

### Setup

```bash
# Clone the repository
git clone https://github.com/dr3ff1c13nt/poi-routing-api.git
cd poi-routing-api

# Download OSM data for Greece
mkdir -p data/osm
wget -O data/osm/greece-latest.osm.pbf https://download.geofabrik.de/europe/greece-latest.osm.pbf

# Start services
docker compose up -d

# Wait for GraphHopper to build routing graph (~2-3 min)
docker logs -f poi-graphhopper

# Import POIs (run once)
docker compose exec api python scripts/import_pois.py
```

### Access

- **Web UI**: http://localhost:5000
- **Swagger UI**: http://localhost:5000/apidocs
- **API Base**: http://localhost:5000/api/v1

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Get current user |

### POIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/pois` | List/search POIs |
| GET | `/api/v1/pois/{id}` | Get single POI |
| GET | `/api/v1/pois/categories` | List categories |

### Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/routes/compute` | Compute route |
| GET | `/api/v1/routes` | List saved routes |
| POST | `/api/v1/routes` | Save route |
| GET | `/api/v1/routes/{id}` | Get route details |
| PUT | `/api/v1/routes/{id}` | Update route |
| DELETE | `/api/v1/routes/{id}` | Delete route |

### Info
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/about` | Team info |
| GET | `/health` | Health check |

## Examples

### Register & Login
```bash
# Register
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "email": "demo@example.com", "password": "secret123"}'

# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "secret123"}'
```

### Search POIs
```bash
# Text search
curl "http://localhost:5000/api/v1/pois?q=beach"

# By category
curl "http://localhost:5000/api/v1/pois?category=restaurant"

# Proximity search (5km radius around Corfu Town)
curl "http://localhost:5000/api/v1/pois?lat=39.6243&lon=19.9217&radius=5000"
```

### Compute Route
```bash
# Route between POIs
curl -X POST http://localhost:5000/api/v1/routes/compute \
  -H "Content-Type: application/json" \
  -d '{"poi_ids": ["poi-id-1", "poi-id-2"]}'

# Route between coordinates
curl -X POST http://localhost:5000/api/v1/routes/compute \
  -H "Content-Type: application/json" \
  -d '{"points": [[39.6243, 19.9217], [39.5833, 19.8500]]}'
```

## Tech Stack

- **Framework**: Flask + Flasgger
- **Database**: PostgreSQL + PostGIS
- **Routing**: GraphHopper (self-hosted)
- **Auth**: Flask-JWT-Extended
- **Frontend**: LeafletJS
- **Containerization**: Docker
- **CI/CD**: GitHub Actions + GHCR

## Project Structure

```
poi-routing-api/
├── app/
│   ├── api/           # API endpoints (pois, routes, about)
│   ├── auth/          # Authentication endpoints
│   ├── models/        # Database models (User, POI, Route)
│   ├── services/      # Business logic (GraphHopper, POI service)
│   ├── middleware/    # Rate limiting, request ID
│   └── errors.py      # Error handlers with fun messages
├── static/            # Web UI (HTML, CSS, JS)
├── scripts/           # Import scripts
├── tests/             # Test suite
├── docker-compose.yml # Development setup
└── docker-compose.prod.yml # Production with Traefik
```

## Rate Limiting

Exceeded your rate limit? You'll get a friendly HTTP 418 response:

```json
{
  "error": "I'm a teapot",
  "message": "Darjeeling demands patience. 42 more seconds.",
  "status": 418,
  "retry_after": 42
}
```

Rate limits are configurable per user (default: 60 req/min).

## Credits & Inspiration

- **Error Messages**: Inspired by [No-as-a-Service](https://github.com/mxssl/no-as-a-service) for witty 404 responses
- **HTTP 418**: RFC 2324 "Hyper Text Coffee Pot Control Protocol" easter egg
- **OSM Data**: [Geofabrik](https://download.geofabrik.de/) for OpenStreetMap extracts
- **Routing**: [GraphHopper](https://www.graphhopper.com/) open source routing engine

## Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally (requires PostgreSQL + GraphHopper)
FLASK_APP=run.py FLASK_ENV=development flask run

# Run tests
pytest tests/ -v
```

## Deployment

The project includes GitHub Actions CI/CD for automatic deployment:

1. Push to `main` triggers build
2. Docker image pushed to GitHub Container Registry
3. Deployed to VPS via Tailscale

See `.github/workflows/ci.yml` and `docker-compose.prod.yml` for details.

## Submission Scripts

```bash
# Export database for submission
./scripts/export_db.sh

# Import database after docker compose up
./scripts/import_db.sh
```

## License

MIT License - see LICENSE file.

---

Built for Ionian University - Προχωρημένες Τεχνολογίες Διαδικτύου 2024-2025.
