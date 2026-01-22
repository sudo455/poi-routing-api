#!/bin/bash
# Download Corfu/Greece OSM data for GraphHopper

set -e

OSM_DIR="$(dirname "$0")/../data/osm"
mkdir -p "$OSM_DIR"

# Corfu extract (much smaller than all of Greece)
# Using BBBike extracts for regional data
# Approximate Corfu bounding box: 39.37,19.65,39.85,20.25
CORFU_URL="https://download.geofabrik.de/europe/greece-latest.osm.pbf"
OUTPUT="$OSM_DIR/greece-latest.osm.pbf"

# Alternative: Use osmium to extract just Corfu from Greece
# osmium extract -b 19.65,39.37,20.25,39.85 greece-latest.osm.pbf -o corfu.osm.pbf

echo "Downloading Greece OSM data..."
echo "Note: This is ~350MB. GraphHopper will index all of Greece."
echo "For production, consider extracting just Corfu."
curl -L -o "$OUTPUT" "$CORFU_URL"

echo "Downloaded to: $OUTPUT"
echo "File size: $(du -h "$OUTPUT" | cut -f1)"
echo ""
echo "GraphHopper will process this file on first startup."
echo "First startup may take several minutes to build the routing graph."
