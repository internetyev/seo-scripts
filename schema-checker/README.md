## Schema.org Markup Checker

This script checks which **schema.org markup types** are present on one or more URLs and outputs a CSV presence matrix.

Each row represents a URL, and each column (after `URL`) is a schema.org type name (`Article`, `Product`, etc.) with `1`/`0` indicating presence.

### Requirements

Install dependencies (ideally in a virtualenv):

```bash
pip install requests beautifulsoup4
```

### Usage

Change into the project root (where the `schema-checker` folder is), then run:

#### From a file of URLs

- **TXT file**: one URL per line (blank lines and lines starting with `#` are ignored).
- **CSV file**: the first column of each row is treated as the URL; header rows starting with `URL` are skipped.

```bash
python schema-checker/schema-checker.py --file urls.txt --output schema_results.csv
python schema-checker/schema-checker.py --file urls.csv --output schema_results.csv
```

If `--output` is omitted when using `--file`, the script writes `schema_results.csv` in the current directory.

#### Single URL

Analyze a single URL and **print results to the terminal**:

```bash
python schema-checker/schema-checker.py --url https://www.example.com
```

Analyze a single URL and **write results to a CSV**:

```bash
python schema-checker/schema-checker.py --url https://www.example.com --output example_schema.csv
```

### How it detects schema.org markup

For each URL, the script:

- Fetches HTML using `requests`.
- Parses the page with `BeautifulSoup`.
- Looks for:
  - **JSON-LD**: `<script type="application/ld+json">` and recursively collects all `@type` values.
  - **Microdata**: elements with `itemtype` attributes containing `schema.org/...`.
  - **Basic RDFa**: elements with `typeof` attributes containing `schema.org/...`.

Only the last path segment of a schema URL is used as the type name (e.g. `https://schema.org/Article` → `Article`).


