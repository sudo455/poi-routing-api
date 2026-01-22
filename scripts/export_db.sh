#!/bin/bash
# Export PostgreSQL database for submission
# Creates a SQL dump file that can be imported with docker compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_FILE="${PROJECT_DIR}/data/db_export.sql"

echo "Exporting database from poi-db container..."

# Create data directory if it doesn't exist
mkdir -p "${PROJECT_DIR}/data"

# Export database using pg_dump inside the container
docker compose exec -T db pg_dump -U poi_user -d poi_db --clean --if-exists > "$OUTPUT_FILE"

echo "Database exported to: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
