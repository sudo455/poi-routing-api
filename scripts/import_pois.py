#!/usr/bin/env python3
"""
Import POIs from OpenStreetMap for Corfu (Κέρκυρα).

Uses Overpass API to fetch various POI categories.
"""
import sys
import os
import requests
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services import POIService


# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Corfu bounding box (approximate)
# SW: 39.37, 19.65 | NE: 39.85, 20.25
CORFU_BBOX = "39.37,19.65,39.85,20.25"

# POI categories to fetch (OSM key-value pairs)
POI_CATEGORIES = {
    'restaurant': ['amenity=restaurant', 'amenity=taverna'],
    'cafe': ['amenity=cafe'],
    'bar': ['amenity=bar', 'amenity=pub'],
    'hotel': ['tourism=hotel'],
    'hostel': ['tourism=hostel'],
    'guest_house': ['tourism=guest_house'],
    'apartment': ['tourism=apartment'],
    'beach': ['natural=beach'],
    'museum': ['tourism=museum'],
    'church': ['amenity=place_of_worship', 'building=church'],
    'monastery': ['amenity=monastery', 'building=monastery'],
    'castle': ['historic=castle', 'historic=fort'],
    'archaeological_site': ['historic=archaeological_site'],
    'viewpoint': ['tourism=viewpoint'],
    'parking': ['amenity=parking'],
    'fuel': ['amenity=fuel'],
    'pharmacy': ['amenity=pharmacy'],
    'hospital': ['amenity=hospital'],
    'clinic': ['amenity=clinic', 'amenity=doctors'],
    'supermarket': ['shop=supermarket'],
    'bank': ['amenity=bank'],
    'atm': ['amenity=atm'],
    'post_office': ['amenity=post_office'],
    'bus_station': ['amenity=bus_station', 'public_transport=station'],
    'ferry_terminal': ['amenity=ferry_terminal'],
    'airport': ['aeroway=aerodrome'],
    'attraction': ['tourism=attraction'],
    'monument': ['historic=monument', 'historic=memorial'],
    'park': ['leisure=park'],
    'garden': ['leisure=garden'],
    'swimming_pool': ['leisure=swimming_pool'],
    'marina': ['leisure=marina'],
}


def build_overpass_query(category: str, tags: list[str]) -> str:
    """Build Overpass QL query for given tags in Corfu."""
    tag_queries = []
    for tag in tags:
        key, value = tag.split('=')
        # Query nodes, ways, and relations
        tag_queries.append(f'node["{key}"="{value}"]({CORFU_BBOX});')
        tag_queries.append(f'way["{key}"="{value}"]({CORFU_BBOX});')
        tag_queries.append(f'relation["{key}"="{value}"]({CORFU_BBOX});')

    query = f"""
    [out:json][timeout:60];
    (
        {''.join(tag_queries)}
    );
    out center;
    """
    return query


def fetch_pois_for_category(category: str, tags: list[str]) -> list[dict]:
    """Fetch POIs from Overpass API for a category."""
    query = build_overpass_query(category, tags)

    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, timeout=120)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  Error fetching {category}: {e}")
        return []

    pois = []
    for element in data.get('elements', []):
        # Get coordinates (center for ways/relations)
        if element['type'] == 'node':
            lat = element['lat']
            lon = element['lon']
        elif 'center' in element:
            lat = element['center']['lat']
            lon = element['center']['lon']
        else:
            continue

        tags = element.get('tags', {})
        name = tags.get('name', tags.get('name:en', tags.get('name:el', '')))

        if not name:
            # Skip unnamed POIs for most categories
            if category not in ['beach', 'viewpoint', 'parking']:
                continue
            # Generate name for unnamed natural features
            name = f"Unnamed {category.replace('_', ' ').title()}"

        # Build properties from useful tags
        properties = {}
        useful_tags = [
            'phone', 'website', 'email', 'opening_hours',
            'cuisine', 'stars', 'rooms', 'addr:street',
            'addr:housenumber', 'addr:city', 'wikidata', 'wikipedia'
        ]
        for tag in useful_tags:
            if tag in tags:
                properties[tag.replace(':', '_')] = tags[tag]

        # Add description from OSM if available
        description = tags.get('description', tags.get('description:en', ''))

        pois.append({
            'name': name,
            'category': category,
            'latitude': lat,
            'longitude': lon,
            'description': description,
            'properties': properties,
            'osm_id': element['id'],
            'osm_type': element['type']
        })

    return pois


def main():
    """Import all POIs from Corfu."""
    print("=" * 60)
    print("POI Import Script for Corfu (Κέρκυρα)")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        total_imported = 0

        for category, tags in POI_CATEGORIES.items():
            print(f"\nFetching {category}...")
            pois = fetch_pois_for_category(category, tags)
            print(f"  Found {len(pois)} POIs")

            if pois:
                created = POIService.bulk_create(pois)
                print(f"  Imported {created} new POIs")
                total_imported += created

            # Be nice to Overpass API
            time.sleep(1)

        print("\n" + "=" * 60)
        print(f"Total POIs imported: {total_imported}")
        print("=" * 60)


if __name__ == '__main__':
    main()
