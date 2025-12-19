#!/usr/bin/env python3
"""
Fetch all location IDs from DataForSEO API and save as CSV.

This script calls the DataForSEO API endpoint /v3/serp/id_list to get
all available location IDs and saves them to a CSV file.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

import requests

# Import from existing fetch-serp-pages module for credentials
sys.path.insert(0, str(Path(__file__).parent.parent / "fetch-serp-pages"))
try:
    from config import DATAFORSEO_USERNAME, DATAFORSEO_PASSWORD
except ImportError as e:
    print(f"Error importing config: {e}", file=sys.stderr)
    sys.exit(1)

# DataForSEO API endpoint for location IDs
LOCATIONS_API_URL = "https://api.dataforseo.com/v3/serp/google/locations"


def fetch_locations() -> Dict[str, Any]:
    """
    Fetch all location IDs from DataForSEO API.
    
    Returns:
        Raw JSON response from the API
        
    Raises:
        RuntimeError: On network, HTTP, or API errors
    """
    try:
        response = requests.get(
            LOCATIONS_API_URL,
            auth=(DATAFORSEO_USERNAME, DATAFORSEO_PASSWORD),
            headers={"Content-Type": "application/json"},
            timeout=300,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Network error: {e}") from e

    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP error: status {response.status_code}, body: {response.text[:500]}"
        )

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response: {e}") from e

    # DataForSEO standard success code
    if data.get("status_code") != 20000:
        raise RuntimeError(
            f"DataForSEO error: status_code={data.get('status_code')}, "
            f"status_message={data.get('status_message')}"
        )

    return data


def parse_locations_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse the API response and extract location information.
    
    Args:
        data: Raw API response JSON
        
    Returns:
        List of dictionaries with location information
    """
    locations = []
    
    # DataForSEO API structure: data -> tasks -> [0] -> result -> [array of location objects]
    items = []
    
    # Try the standard DataForSEO response structure
    tasks = data.get("tasks", [])
    if tasks and len(tasks) > 0:
        task = tasks[0]
        result = task.get("result", [])
        # result is directly an array of location objects, not nested
        if result and isinstance(result, list):
            items = result
    
    # Fallback: try other possible structures
    if not items:
        if "version" in data:
            version_data = data.get("version", [])
            if isinstance(version_data, list) and len(version_data) > 0:
                items = version_data[0].get("items", [])
        elif "items" in data:
            items = data.get("items", [])
        elif "result" in data:
            result = data.get("result", [])
            if isinstance(result, list):
                items = result
    
    # If we still don't have items, try to find any list in the response
    if not items:
        # Look for any key that contains a list of location-like objects
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                if isinstance(value[0], dict):
                    items = value
                    break
    
    # Parse items
    for item in items:
        location_info = {}
        
        # Extract common fields (field names based on actual API response)
        location_info["location_code"] = item.get("location_code") or item.get("id") or item.get("code", "")
        location_info["location_name"] = item.get("location_name") or item.get("name") or item.get("title", "")
        location_info["country_code"] = item.get("country_iso_code") or item.get("country_code") or item.get("country", "")
        location_info["country_name"] = item.get("country_name") or item.get("country", "")
        location_info["location_type"] = item.get("location_type") or item.get("type", "")
        location_info["parent_id"] = item.get("location_code_parent") or item.get("parent_id") or item.get("parent_code", "")
        
        # Add any additional fields
        for key, value in item.items():
            if key not in location_info and value is not None:
                location_info[key] = value
        
        locations.append(location_info)
    
    return locations


def save_to_csv(locations: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Save locations to CSV file.
    
    Args:
        locations: List of location dictionaries
        output_path: Path to output CSV file
    """
    if not locations:
        print("Warning: No locations to save", file=sys.stderr)
        return
    
    # Get all unique keys from all location dictionaries
    all_keys = set()
    for loc in locations:
        all_keys.update(loc.keys())
    
    # Define preferred column order
    preferred_order = [
        "location_code",
        "location_name",
        "country_code",
        "country_name",
        "location_type",
        "parent_id",
    ]
    
    # Sort keys: preferred first, then rest alphabetically
    ordered_keys = []
    for key in preferred_order:
        if key in all_keys:
            ordered_keys.append(key)
            all_keys.remove(key)
    
    ordered_keys.extend(sorted(all_keys))
    
    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(locations)


def save_json(data: Dict[str, Any], output_path: Path) -> None:
    """Save raw JSON response to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch all location IDs from DataForSEO API and save as CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="dataforseo-locations.csv",
        help="Output CSV file path (default: dataforseo-locations.csv)",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Also save raw JSON response to this file (optional)",
    )
    
    args = parser.parse_args()
    
    # Setup paths
    output_path = Path(args.output).expanduser().resolve()
    
    print("Fetching location IDs from DataForSEO API...")
    try:
        data = fetch_locations()
    except Exception as e:
        print(f"Error fetching locations: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Save raw JSON if requested
    if args.json:
        json_path = Path(args.json).expanduser().resolve()
        save_json(data, json_path)
        print(f"Raw JSON saved to: {json_path}")
    
    # Parse locations
    print("Parsing location data...")
    locations = parse_locations_data(data)
    print(f"Found {len(locations)} locations")
    
    # Save to CSV
    print(f"Saving to CSV: {output_path}")
    save_to_csv(locations, output_path)
    
    print(f"\nDone! Saved {len(locations)} locations to {output_path}")


if __name__ == "__main__":
    main()

