# Googlebot Log Reports

This script augments Googlebot log CSV exports (from Screaming Frog Log Analyzer) with `ua-group`, `url-group`, sitemap presence flags, and date normalization, and generates daily/summary reports.

## Usage

```bash
python botlog-reports/googlebot-log-reports.py \
  --input <path-to-input-csv> \
  --output <path-to-output-csv> \
  --config <path-to-config-json> \
  --ua-summary-output <path-to-ua-summary-csv> \
  --url-summary-output <path-to-url-summary-csv> \
  --sitemap <path-to-sitemap-txt-or-csv>
```

Omit `--output` to overwrite the input file in place.

### Arguments

- `--input` (required): Path to the source CSV file exported from Screaming Frog Log Analyzer
- `--output` (optional): Path where the augmented CSV will be saved (with grouping metadata added). Defaults to overwriting the input file.
- `--config` (required): Path to the JSON configuration file containing UA and URL grouping rules
- `--ua-summary-output` (optional): Path where the UA summary CSV will be saved (listing unique user agents with their groups and counts). Defaults to `<input>-ua-summary.csv`.
- `--url-summary-output` (optional): Path where the URL summary CSV will be saved (URL, url-group, count). Defaults to `<input>-url-summary.csv`.
- `--sitemap` (optional): Path to a sitemap file. Accepts a TXT with one URL per line or a CSV containing a `URL` column. Used to flag rows whose `URL` exists in the sitemap (if omitted, all rows will have `sitemap=0`).

## Configuration

The configuration file (`botlogs-config.json`) defines two types of rules. See `botlogs-helper/sample-config.json` for a starter template you can copy and adjust:

### UA Rules (`ua_rules`)

Rules for classifying user agents. Each rule can match based on:
- String conditions: `contains`, `not-contains`, `equals`, `starts-with`, `regex`
- Chrome version constraints: `chrome_min_version`, `chrome_max_version`, `chrome_version`, `chrome_version_range`

Rules are evaluated in order, and the first matching rule determines the `ua-group` value.

### URL Rules (`url_rules`)

Rules for classifying URLs. Each rule can match based on:
- String conditions: `contains`, `not-contains`, `equals`, `not-equal`, `regex`

**Important**: Multiple URL rules can match a single URL. All matching groups are combined into a semicolon-separated `url-group` value (e.g., `kharkiv;go;ru`).

Within a single rule, multiple conditions are treated as AND (all must match).

## Output

The script produces multiple files:

1. **Augmented CSV** (`--output`): The original CSV with new columns:
   - `ua-group`: Semicolon-separated list of user agent groups
   - `url-group`: Semicolon-separated list of URL groups (or `unknown` if no rules match)
   - `sitemap`: `1` if the URL is present in the provided sitemap file, otherwise `0`
   - `date`: Normalized date (YYYY-MM-DD) derived from the `Timestamp` column, when present
   - Pre-existing `ua-group`, `url-group`, or `sitemap` columns are removed before writing to avoid duplication.

2. **UA Summary CSV** (`--ua-summary-output`): A summary report with columns:
   - `User Agent`: The full user agent string
   - `ua-group`: The assigned group(s)
   - `count`: Number of log entries with this user agent/group combination

3. **URL Summary CSV** (`--url-summary-output`): A summary report with columns:
   - `URL`: The URL from the log
   - `url-group`: The assigned URL group(s)
   - `count`: Number of log entries for the URL/group combination

4. **Daily UA Group Report** (`<input>-report-ua-groups.csv`): Rows per UA group with daily counts plus a `TOTAL` row.

5. **Daily URL Group Report** (`<input>-report-url-groups.csv`): Rows per URL group with daily counts (includes config-defined groups and any observed extras), plus `sitemap`, `not in sitemap`, and `TOTAL` rollups (totals reflect event counts per day).

## Example

```bash
python botlog-reports/googlebot-log-reports.py \
  --input bodo/botlogs/Events-2025-11.csv \
  --output botlog-reports/Events-2025-11-with-groups.csv \
  --config botlog-reports/botlogs-config.json \
  --ua-summary-output botlog-reports/Events-2025-11-ua-summary.csv \
  --url-summary-output botlog-reports/Events-2025-11-url-summary.csv \
  --sitemap bodo/botlogs/sitemap-urls.txt
```

## Progress Output

The script displays:
- Full path of the CSV being processed
- Full path of the configuration file
- Progress bar during processing
- Full paths of all generated output files upon completion

## Sample Config

- A starter config lives at `botlogs-helper/sample-config.json`; copy and adjust it for your site before running the script.
