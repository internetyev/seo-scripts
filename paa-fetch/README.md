# PAA Fetch - People Also Ask Questions Fetcher

A CLI Python tool that fetches People Also Ask (PAA) questions from the DataForSEO Google Organic Live Advanced endpoint for one or multiple keywords and outputs the results as CSV or JSON.

## Features

- Fetch PAA questions for single or multiple keywords
- Recursive PAA fetching (fetch PAA questions from PAA questions, multiple levels deep)
- Support for CSV and JSON output formats
- Automatic country code to location mapping
- Progress reporting with progress bars for multiple keywords
- Comprehensive error handling
- Flexible output file naming

## Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install requests tqdm
```

2. Set up your DataForSEO API credentials:

Create a JSON config file in the same directory as the script (default: `.dataforseo.json` in the script directory, or use `--config` to specify a different path):

```json
{
  "api_login": "your_login_here",
  "api_password": "your_password_here"
}
```

You can use the provided `.dataforseo.json.example` as a template.

## Usage

### Basic Examples

**Single keyword:**

```bash
python3 paa-fetch.py --keyword "best gifts for men"
# or using short option:
python3 paa-fetch.py -k "best gifts for men"
```

**Multiple keywords from file:**

```bash
python3 paa-fetch.py --file keywords.txt
# or using short option:
python3 paa-fetch.py -f keywords.txt
```

**Combine single keyword and keywords file:**

```bash
python3 paa-fetch.py -k "test keyword" -f keywords.txt
```

**Specify country and language:**

```bash
python3 paa-fetch.py -f keywords.txt -c UA -l uk
```

**Recursive PAA fetching (depth 2):**

```bash
python3 paa-fetch.py -k "best gifts" -d 2
```

**Output as JSON:**

```bash
python3 paa-fetch.py -k "best gifts" --json
```

**Explicit output path:**

```bash
python3 paa-fetch.py -k "best gifts" --output /path/to/output.csv
```

**Overwrite existing file without prompt:**

```bash
python3 paa-fetch.py -k "best gifts" --overwrite
```

### Command-Line Arguments

#### Input (at least one required)

- `-k, --keyword "your keyword here"` - Single keyword string
- `-f, --file /path/to/keywords.txt` - Path to text file with one keyword per line

**Note:** Either `--keyword` or `--file` (or both) must be provided.

#### Other Parameters

- `-l, --lang, --language CODE` - Language code used for DataForSEO (default: `en`)
- `-c, --country CODE` - ISO 2-letter country code (default: `US`)
- `--config PATH` - Path to JSON config file with DataForSEO credentials (default: `.dataforseo.json` in script directory)
- `--output PATH` - Explicit output file path (if omitted, default naming rules apply)
- `--csv` - Output format: CSV (default if neither --csv nor --json is specified)
- `--json` - Output format: JSON
- `--silent` - Silent mode: do not prompt for overwrite confirmation
- `-o, --overwrite` - Overwrite existing output file without prompting
- `-d, --depth DEPTH` - Maximum depth for recursive PAA fetching (1 = only original keyword, 2 = original + PAA questions, etc.) (default: `1`)
- `-q, --questions N` - Maximum number of unique questions to collect per root keyword (default: `20`)
- `-r, --requests N` - Maximum number of API requests per root keyword (safety cap) (default: `15`)
- `-h, --help` - Show help message

## Configuration

### Config File Format

The config file must be a JSON file with the following structure:

```json
{
  "api_login": "your_dataforseo_login",
  "api_password": "your_dataforseo_password"
}
```

Default location: `.dataforseo.json` in the same directory as the script.

You can override the config path using the `--config` argument.

### Country Codes

The script supports common ISO 2-letter country codes. Some examples:

- `US` - United States (default, location_code: 2840)
- `GB` - United Kingdom
- `UA` - Ukraine
- `DE` - Germany
- `FR` - France
- `CA` - Canada
- `AU` - Australia

If you use an unsupported country code, the script will display an error message with instructions.

## Output Formats

### CSV Format

CSV output contains one row per PAA question:

```csv
keyword,question
russia is a terrorist state,Why Russia is a high risk country?
russia is a terrorist state,Is Russia an aggressive state?
```

### JSON Format

JSON output groups questions by keyword:

```json
[
  {
    "keyword": "russia is a terrorist state",
    "question": [
      "Why Russia is a high risk country?",
      "Is Russia an aggressive state?"
    ]
  }
]
```

Keywords with no PAA questions are included with an empty `question` array.

## Output File Naming

### Default Naming Rules

1. **If `--output` is provided:** Uses the exact path specified.

2. **If `--file` is used:** 
   - Output directory: Same as the keywords file directory
   - Filename: `{keywords-filename}_questions.{csv|json}`
   - Example: `keywords.txt` → `keywords_questions.csv`

3. **If `--keyword` is used:**
   - Output directory: Same as the script directory
   - Filename: `{sanitized-keyword}_questions.{csv|json}`
   - Keyword is sanitized: lowercase, spaces → dashes, special chars removed
   - Example: `"best gifts for men"` → `best-gifts-for-men_questions.csv`

### File Overwrite Behavior

- If the output file already exists and neither `--overwrite` nor `--silent` is used, the script will prompt: `"filename already exists. Overwrite? (Y/N)"`
- Use `--overwrite` to automatically overwrite without prompting
- Use `--silent` to suppress the prompt (will still prompt unless `--overwrite` is also used)

## Recursive PAA Fetching

The script supports recursive PAA fetching, allowing you to fetch PAA questions from PAA questions themselves, creating a multi-level tree of questions.

### Depth Parameter

- `--depth 1` (default): Only fetch PAA questions for the original keyword
- `--depth 2`: Fetch PAA for the original keyword, then also fetch PAA for each of those questions
- `--depth 3`: Continue one level deeper, and so on

### Limits

- `--questions N`: Maximum number of unique questions to collect per root keyword (default: `20`)
- `--requests N`: Maximum number of API requests per root keyword (safety cap, default: `15`)

### Example

With `--depth 2`, if the original keyword "best gifts for men" returns:
- "What are good birthday gifts for men?"
- "What do men actually want as gifts?"

The script will then also fetch PAA questions for each of those questions, aggregating all unique questions under the root keyword.

## Progress Reporting

### Single Keyword

For a single keyword, the script displays:

```
Sending request for keyword: "best gifts for men"...
Done in 12.3s – 5 PAA questions found
Output saved to best-gifts-for-men_questions.csv
```

### Multiple Keywords

For multiple keywords, the script shows a progress bar with detailed status:

```
Processing keywords: 100%|████████████| 3/3 [00:45<00:00, 15.2s/keyword]
[1/3] Done in 12.3s – 5 PAA questions found
[2/3] Done in 14.1s – 3 PAA questions found
[3/3] Done in 11.8s – 0 PAA questions found (no PAA block)
No PAA for 'keyword with no results'
```

### Recursive Mode

When using `--depth > 1`, the script shows detailed progress for each API request:

```
Processing root keyword: "best gifts for men"...
Sending request (depth=0, request 1/15) for keyword: "best gifts for men" (root: "best gifts for men")...
Done in 3.2s – 4 PAA questions found (depth=0, current total=4)
Sending request (depth=1, request 2/15) for keyword: "What are good birthday gifts for men?" (root: "best gifts for men")...
Done in 2.8s – 3 PAA questions found (depth=1, current total=7)
Root keyword 'best gifts for men' completed in 12.5s – 15 unique PAA questions collected
```

## Error Handling

The script handles various error scenarios:

- **Config errors:** Missing config file or missing credentials → exits with error message
- **Location mapping errors:** Unknown country code → exits with error message
- **Network errors:** Connection issues → logs error and continues to next keyword
- **HTTP errors:** Non-200 status codes → logs error and continues
- **DataForSEO API errors:** Invalid status codes → logs error and continues

In recursive mode, errors at any depth level are logged with context (showing which keyword failed and its root keyword), and the script continues processing remaining items.

If all keywords fail, the script still creates an output file (empty or with header only) and displays a warning.

## Examples

### Example 1: Fetch PAA for Ukrainian keywords

```bash
python3 paa-fetch.py \
  -f keywords-sample.txt \
  -c UA \
  -l uk \
  --json
```

### Example 2: Single keyword with custom output

```bash
python3 paa-fetch.py \
  -k "best coffee makers" \
  -c US \
  --output /tmp/coffee-paa.csv \
  --overwrite
```

### Example 3: Multiple keywords with progress tracking

```bash
python3 paa-fetch.py \
  -f my-keywords.txt \
  -c GB \
  -l en \
  --csv
```

### Example 4: Recursive PAA fetching (depth 2)

```bash
python3 paa-fetch.py \
  -k "best gifts for men" \
  -d 2 \
  -q 30 \
  -r 20
```

This will:
- Fetch PAA questions for "best gifts for men"
- Then fetch PAA questions for each of those questions
- Collect up to 30 unique questions total
- Use up to 20 API requests maximum

### Example 5: Using short options

```bash
python3 paa-fetch.py -k "test" -f keywords.txt -c GB -l en -d 2 -q 25 -r 18
```

## Requirements

- Python 3.6+
- `requests` library
- `tqdm` library

## DataForSEO API

This script uses the DataForSEO Google Organic Live Advanced API endpoint:

- **Endpoint:** `https://api.dataforseo.com/v3/serp/google/organic/live/advanced`
- **Method:** POST
- **Authentication:** HTTP Basic Auth
- **Request timeout:** 300 seconds (5 minutes)

For more information about the DataForSEO API, visit: https://docs.dataforseo.com/

## License

This script is part of the seo-scripts-private repository.

