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

### Example CSV

```csv
keyword,location_id,language,location_name
"pizza near me",,en,"New York"
"coffee shop",2826,en,"London"
"restaurant",,en,
"dentist",,en,"Los Angeles"
```

## Usage

```bash
python local-pack-tracker.py <csv_file> [options]
```

### Options

- `-o, --output`: Output CSV file path (default: `local-pack-positions.csv`)
- `--json-dir`: Directory to save raw JSON files (default: `serp-json`)
- `--depth`: Depth of search results (default: 100)

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
   - `location_code`: DataForSEO location code used
   - `location_name`: Location name (if provided)
   - `language`: Language code used
   - `local_3pack_position`: Position of local 3-pack (1-based) or "N/A" if not found

2. **JSON files** (in `serp-json/` directory by default):
   - One JSON file per keyword with the raw SERP response from DataForSEO

## Location Lookup

The script automatically looks up location IDs from the `dataforseo-locations.csv` file located in the `top-stories` directory. If a location name is not found or not provided, it defaults to USA (location code: 2840).

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

