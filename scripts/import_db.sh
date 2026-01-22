#!/bin/bash
# Import PostgreSQL database from export
# Use this after docker compose up to restore data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INPUT_FILE="${PROJECT_DIR}/data/db_export.sql"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Database export file not found: $INPUT_FILE"
    echo "Run export_db.sh first or ensure the file exists."
    exit 1
fi

echo "Importing database to poi-db container..."

# Import database using psql inside the container
docker compose exec -T db psql -U poi_user -d poi_db < "$INPUT_FILE"

echo "Database imported successfully!"
