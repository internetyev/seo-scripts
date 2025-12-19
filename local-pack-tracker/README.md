# Local Pack Tracker

This script fetches SERP data for keywords from a CSV file and extracts the position of local 3-pack results in Google SERP.

## Features

- Reads keywords from CSV file with optional location and language parameters
- Automatically looks up DataForSEO location ID from location name if not provided
- Fetches SERP data using the existing `fetch-serp-pages` module
- Saves raw JSON responses for each keyword
- Extracts local 3-pack position from SERP results
- Outputs CSV with keyword and local 3-pack position

## CSV Input Format

The input CSV file should have the following columns:

- `keyword` (required): The search keyword
- `location_id` (optional): DataForSEO location code (if not provided, will lookup from location_name)
- `language` (optional): Language code (default: "en")
- `location_name` (optional): Location name for lookup (fallback: USA)
- `lat` (optional): Latitude coordinate (replaces location_name/location_id if provided)
- `lon` (optional): Longitude coordinate (replaces location_name/location_id if provided)
- `radius` (optional): Radius in millimeters (default: 20000 = 20km, min: 199.9, max: 199999)

**Note:** If `lat` and `lon` are provided, they take priority over `location_name`/`location_id`. The coordinates use the DataForSEO `location_coordinate` parameter in the format "latitude,longitude,radius".

### Example CSV

```csv
keyword,location_id,language,location_name,lat,lon,radius
"pizza near me",,en,"New York",,
"coffee shop",2826,en,"London",,
"restaurant",,en,,40.7128,-74.0060,20000
"dentist",,en,"Los Angeles",,
"bakery",,en,,51.5074,-0.1278,15000
```

## Usage

```bash
python local-pack-tracker.py <csv_file> [options]
```

### Options

- `-o, --output`: Output CSV file path (default: `local-pack-positions.csv`)
- `--json-dir`: Directory to save raw JSON files (default: `serp-json`)
- `--depth`: Depth of search results (default: 10)

### Examples

```bash
# Basic usage
python local-pack-tracker.py sample-keywords.csv

# Custom output file and JSON directory
python local-pack-tracker.py keywords.csv -o results.csv --json-dir json-files

# With custom depth
python local-pack-tracker.py keywords.csv --depth 50
```

## Output

The script generates:

1. **CSV file** (default: `local-pack-positions.csv`) with columns:
   - `keyword`: The search keyword
   - `location_code`: DataForSEO location code used (empty if coordinates were used)
   - `location_name`: Location name (if provided)
   - `latitude`: Latitude coordinate (if provided)
   - `longitude`: Longitude coordinate (if provided)
   - `language`: Language code used
   - `local_3pack_position`: Position of local 3-pack (1-based) or "N/A" if not found

2. **JSON files** (in `serp-json/` directory by default):
   - One JSON file per keyword with the raw SERP response from DataForSEO

## Location Lookup

The script supports three methods for specifying location:

1. **Coordinates (priority)**: If `lat` and `lon` are provided, the script uses GPS coordinates with the DataForSEO `location_coordinate` parameter. This takes priority over other methods.

2. **Location ID**: If `location_id` is provided, it's used directly.

3. **Location Name**: If `location_name` is provided, the script looks up the location ID from the `dataforseo-locations.csv` file located in the `top-stories` directory.

If none of the above are provided, it defaults to USA (location code: 2840).

## Dependencies

- Python 3.6+
- `requests` library
- Access to `fetch-serp-pages/config.py` for DataForSEO API credentials

## Notes

- The script uses the existing `fetch-serp-pages` module for SERP fetching
- Local pack detection looks for various indicators including:
  - Item types: `local_pack`, `local_pack_element`, `local_results`, etc.
  - Items with 3 sub-items containing local business information
  - Items with fields like `address`, `rating`, `reviews`, `phone`
- If a local pack is not found in the SERP, the position will be marked as "N/A"

