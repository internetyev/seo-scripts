# Fetch DataForSEO Locations

This script fetches all location IDs from the DataForSEO API endpoint `/v3/serp/id_list` and saves them as a CSV file.

## Usage

```bash
python fetch-locations.py [options]
```

### Options

- `-o, --output`: Output CSV file path (default: `dataforseo-locations.csv`)
- `--json`: Optional path to save raw JSON response

### Examples

```bash
# Basic usage - save to default file
python fetch-locations.py

# Custom output file
python fetch-locations.py -o locations.csv

# Save both CSV and raw JSON
python fetch-locations.py -o locations.csv --json locations.json
```

## Output

The script generates a CSV file with the following columns (may vary based on API response):

- `location_code`: DataForSEO location code/ID
- `location_name`: Name of the location
- `country_code`: Country code (ISO)
- `country_name`: Country name
- `location_type`: Type of location (Country, Region, City, etc.)
- `parent_id`: Parent location ID (if applicable)
- Additional fields as provided by the API

## Dependencies

- Python 3.6+
- `requests` library
- Access to `fetch-serp-pages/config.py` for DataForSEO API credentials

## Notes

- The script uses the same API credentials as the other DataForSEO scripts
- The API response structure may vary, so the script attempts to handle different formats
- If the API response structure changes, you may need to adjust the parsing logic in `parse_locations_data()`

