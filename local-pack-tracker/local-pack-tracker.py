#!/usr/bin/env python3
"""
Fetch SERP data for keywords and extract local 3-pack positions.

This script:
1. Reads keywords from a CSV file (keyword, location_id (optional), language, location_name)
2. Looks up location ID from location name if not provided (fallback: USA)
3. Fetches SERP data via DataForSEO API using existing fetch_serp_raw function
4. Saves raw JSON files
5. Extracts local 3-pack position from SERP results
6. Outputs CSV with keyword and local 3-pack position
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import from existing fetch-serp-pages module
sys.path.insert(0, str(Path(__file__).parent.parent / "fetch-serp-pages"))
try:
    import importlib.util
    # Import fetch_serp_raw function from fetch-serp.py
    fetch_serp_path = Path(__file__).parent.parent / "fetch-serp-pages" / "fetch-serp.py"
    spec = importlib.util.spec_from_file_location("fetch_serp", fetch_serp_path)
    fetch_serp_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch_serp_module)
    fetch_serp_raw = fetch_serp_module.fetch_serp_raw
except ImportError as e:
    print(f"Error importing fetch_serp_raw from fetch-serp.py: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error loading fetch-serp-pages module: {e}", file=sys.stderr)
    sys.exit(1)


# Path to locations CSV (relative to this script)
LOCATIONS_CSV_PATH = Path(__file__).parent.parent / "top-stories" / "dataforseo-locations.csv"

# Fallback values
FALLBACK_LOCATION_CODE = 2840  # United States
FALLBACK_LANGUAGE_CODE = "en"  # English


def load_locations_map(csv_path: Path) -> Dict[str, int]:
    """
    Load location name to location_code mapping from CSV.
    
    Args:
        csv_path: Path to the locations CSV file
        
    Returns:
        Dictionary mapping location_name (case-insensitive) to location_code
    """
    locations_map = {}
    
    if not csv_path.exists():
        print(f"Warning: Locations CSV not found at {csv_path}", file=sys.stderr)
        return locations_map
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                location_name = row.get("location_name", "").strip()
                location_code_str = row.get("location_code", "").strip()
                
                if location_name and location_code_str:
                    try:
                        location_code = int(location_code_str)
                        # Store both original case and lowercase for flexible lookup
                        locations_map[location_name.lower()] = location_code
                        locations_map[location_name] = location_code  # Also store original case
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error loading locations CSV: {e}", file=sys.stderr)
    
    return locations_map


def lookup_location_code(location_name: Optional[str], location_id: Optional[str], 
                        locations_map: Dict[str, int]) -> int:
    """
    Lookup location code from location name or use provided location_id.
    
    Args:
        location_name: Location name string (optional)
        location_id: Location ID string (optional, can be empty)
        locations_map: Dictionary mapping location names to codes
        
    Returns:
        Location code integer (fallback: USA)
    """
    # If location_id is provided and valid, use it
    if location_id and location_id.strip():
        try:
            return int(location_id.strip())
        except ValueError:
            pass
    
    # If location_name is provided, try to lookup
    if location_name and location_name.strip():
        location_name_clean = location_name.strip()
        # Try exact match first
        if location_name_clean in locations_map:
            return locations_map[location_name_clean]
        # Try case-insensitive match
        if location_name_clean.lower() in locations_map:
            return locations_map[location_name_clean.lower()]
    
    # Fallback to USA
    return FALLBACK_LOCATION_CODE


def sanitize_keyword_for_filename(keyword: str) -> str:
    """Create a filesystem-friendly filename from a keyword."""
    sanitized = keyword.strip().lower()
    # Replace problematic characters
    for ch in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>', "'", "#", " "]:
        sanitized = sanitized.replace(ch, "-")
    # Remove multiple dashes
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    sanitized = sanitized.strip("-")
    if not sanitized:
        sanitized = "keyword"
    return sanitized


def extract_local_pack_position(serp_data: Dict[str, Any]) -> Optional[int]:
    """
    Extract the position/rank of local pack (local 3-pack) in SERP.
    
    The local pack position is determined by its rank_group or rank_absolute
    relative to other SERP items. We need to find where it appears in the
    overall SERP order.
    
    Args:
        serp_data: Raw SERP JSON response from DataForSEO
        
    Returns:
        Position/rank of local pack (1-based), or None if not found
    """
    try:
        tasks = serp_data.get("tasks", [])
        for task in tasks:
            results = task.get("result", [])
            for result in results:
                items = result.get("items", [])
                
                # Track all items with their positions
                all_items_with_positions = []
                
                for item in items:
                    item_type = item.get("type", "")
                    rank_group = item.get("rank_group")
                    rank_absolute = item.get("rank_absolute")
                    
                    # Use rank_absolute if available, otherwise rank_group
                    # If neither is available, we'll skip it or use a default
                    position = rank_absolute if rank_absolute is not None else rank_group
                    
                    if position is not None:
                        all_items_with_positions.append((position, item_type, item))
                    else:
                        # Some items might not have rank, but we still want to track them
                        # Use a high number to put them at the end
                        all_items_with_positions.append((999999, item_type, item))
                
                # Sort by position to find where local pack appears
                all_items_with_positions.sort(key=lambda x: x[0])
                
                # Look for local pack types (common DataForSEO types)
                local_pack_types = [
                    "local_pack",
                    "local_pack_element", 
                    "local_results",
                    "local",
                    "map",
                    "google_maps",
                ]
                
                for idx, (position, item_type, item) in enumerate(all_items_with_positions):
                    # Check if this is a local pack by type
                    if item_type in local_pack_types:
                        # Return 1-based position in the sorted list
                        return idx + 1
                    
                    # Check if item has nested local pack items
                    if "items" in item:
                        sub_items = item.get("items", [])
                        # If it has 3 items, it might be a local pack
                        if len(sub_items) == 3:
                            # Check if sub-items look like local pack entries
                            has_local_indicators = False
                            for sub_item in sub_items:
                                sub_type = sub_item.get("type", "")
                                if sub_type in local_pack_types or "local" in sub_type.lower():
                                    has_local_indicators = True
                                    break
                                # Check for common local pack fields
                                if any(key in sub_item for key in ["address", "rating", "reviews", "phone"]):
                                    has_local_indicators = True
                                    break
                            
                            if has_local_indicators:
                                return idx + 1
                
                # Alternative: look for items with "local" in type (case-insensitive)
                for idx, (position, item_type, item) in enumerate(all_items_with_positions):
                    if "local" in item_type.lower():
                        return idx + 1
                    
                    # Check if item has structure that suggests local pack
                    # (e.g., has items with address, rating, phone fields)
                    if "items" in item:
                        sub_items = item.get("items", [])
                        if len(sub_items) >= 1:
                            # Check first sub-item for local pack characteristics
                            first_sub = sub_items[0]
                            local_fields = ["address", "rating", "reviews", "phone", "website"]
                            if any(key in first_sub for key in local_fields):
                                # This looks like a local pack
                                return idx + 1
        
        return None
    except Exception as e:
        print(f"Error extracting local pack position: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def read_keywords_from_csv(csv_path: Path) -> List[Dict[str, str]]:
    """
    Read keywords from CSV file.
    
    Expected columns: keyword, location_id (optional), language, location_name
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of dictionaries with keyword data
    """
    keywords = []
    
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                keyword = row.get("keyword", "").strip()
                if not keyword:
                    print(f"Warning: Row {row_num} has empty keyword, skipping", file=sys.stderr)
                    continue
                
                keywords.append({
                    "keyword": keyword,
                    "location_id": row.get("location_id", "").strip(),
                    "language": row.get("language", "").strip() or FALLBACK_LANGUAGE_CODE,
                    "location_name": row.get("location_name", "").strip(),
                })
    except Exception as e:
        print(f"Error reading CSV file: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not keywords:
        print("Error: No valid keywords found in CSV file", file=sys.stderr)
        sys.exit(1)
    
    return keywords


def save_json(data: Dict[str, Any], path: Path) -> None:
    """Save JSON data to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch SERP data and extract local 3-pack positions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Input Format:
  keyword,location_id,language,location_name
  
  - keyword: Required, the search keyword
  - location_id: Optional, DataForSEO location code (if not provided, will lookup from location_name)
  - language: Optional, language code (default: en)
  - location_name: Optional, location name for lookup (fallback: USA)

Example CSV:
  keyword,location_id,language,location_name
  "pizza near me",,en,"New York"
  "coffee shop",2826,en,"London"
  "restaurant",,en,
        """,
    )
    
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to CSV file with keywords",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="local-pack-positions.csv",
        help="Output CSV file path (default: local-pack-positions.csv)",
    )
    parser.add_argument(
        "--json-dir",
        type=str,
        default="serp-json",
        help="Directory to save raw JSON files (default: serp-json)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=100,
        help="Depth of search results (default: 100)",
    )
    
    args = parser.parse_args()
    
    # Setup paths
    script_dir = Path(__file__).parent
    csv_path = Path(args.csv_file).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    json_dir = Path(args.json_dir).expanduser().resolve()
    
    # Load locations map
    print("Loading locations map...")
    locations_map = load_locations_map(LOCATIONS_CSV_PATH)
    print(f"Loaded {len(locations_map)} location mappings")
    
    # Read keywords from CSV
    print(f"Reading keywords from {csv_path}...")
    keywords_data = read_keywords_from_csv(csv_path)
    print(f"Found {len(keywords_data)} keywords")
    
    # Process each keyword
    results = []
    
    for idx, kw_data in enumerate(keywords_data, 1):
        keyword = kw_data["keyword"]
        location_id = kw_data["location_id"]
        language = kw_data["language"] or FALLBACK_LANGUAGE_CODE
        location_name = kw_data["location_name"]
        
        print(f"\n[{idx}/{len(keywords_data)}] Processing: {keyword}")
        
        # Lookup location code
        location_code = lookup_location_code(location_name, location_id, locations_map)
        print(f"  Location: {location_name or 'N/A'} (code: {location_code})")
        print(f"  Language: {language}")
        
        # Fetch SERP data
        try:
            serp_data = fetch_serp_raw(
                query=keyword,
                depth=args.depth,
                language_code=language,
                location_code=location_code,
            )
        except Exception as e:
            print(f"  Error fetching SERP: {e}", file=sys.stderr)
            results.append({
                "keyword": keyword,
                "location_code": location_code,
                "location_name": location_name or "",
                "language": language,
                "local_3pack_position": "ERROR",
            })
            continue
        
        # Save JSON file
        json_filename = sanitize_keyword_for_filename(keyword) + ".json"
        json_path = json_dir / json_filename
        save_json(serp_data, json_path)
        print(f"  Saved JSON: {json_path}")
        
        # Extract local pack position
        local_pack_position = extract_local_pack_position(serp_data)
        
        if local_pack_position is not None:
            print(f"  Local 3-pack position: {local_pack_position}")
        else:
            print(f"  Local 3-pack: Not found")
        
        results.append({
            "keyword": keyword,
            "location_code": location_code,
            "location_name": location_name or "",
            "language": language,
            "local_3pack_position": local_pack_position if local_pack_position is not None else "N/A",
        })
    
    # Write output CSV
    print(f"\nWriting results to {output_path}...")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["keyword", "location_code", "location_name", "language", "local_3pack_position"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\nDone! Processed {len(results)} keywords")
    print(f"Results saved to: {output_path}")
    print(f"JSON files saved to: {json_dir}")


if __name__ == "__main__":
    main()

