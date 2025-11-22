# sitemap-urls

Small helper script to discover sitemap locations for one or many domains and extract all URLs listed in those sitemaps.

This repository file: `sitemap-urls/sitemap-urls.py`

**What it does**
- Reads either a single domain or a CSV file containing domains.
- Checks `robots.txt` for `Sitemap:` entries (falls back to `/sitemap.xml`).
- Follows sitemap index files and collects `<loc>` entries from sitemap XMLs.
- Writes an output CSV with two columns: `domain` and `url`.

**Requirements**
- Python 3.7+
- Packages: `requests`, `pandas`, `beautifulsoup4`, `lxml` (optional but recommended)

Install dependencies:

```bash
python -m pip install --user requests pandas beautifulsoup4 lxml
```

**File structure**
- `sitemap-urls/sitemap-urls.py` — the main script
- `sitemap-urls/domains.csv` — example CSV (not required)

**Usage**

- Process a single domain and write to `out.csv`:

```bash
python sitemap-urls/sitemap-urls.py --domain example.com --output out.csv
```

- Process multiple domains from a CSV (CSV may have a header `domain` or domains in the first column):

```bash
python sitemap-urls/sitemap-urls.py --domains-csv domains.csv --output sitemap-urls.csv
```

- If `--output` is omitted, the script writes to `sitemap-urls.csv` in the current working directory.

**Input CSV format**
- If you pass `--domains-csv`, the script will try to read a `domain` column first. If not present, it will use the first column as the domain list.

Example `domains.csv`:

```csv
domain
example.com
anotherdomain.com
```

or plain list (no header):

```csv
example.com
anotherdomain.com
```

**Output**
- The output CSV contains the columns `domain` and `url`. Each row represents one URL found in that domain's sitemap(s).

**Notes & tips**
- The script uses a small timeout and simple error handling — network failures will skip that sitemap rather than crash the script.
- The script follows sitemap index files (sitemaps that contain links to other sitemaps).
- For large domain lists you may want to add concurrency (threading/async) and retries.

**Troubleshooting**
- If you get zero rows for a domain, check that the domain is reachable and that `robots.txt` or `/sitemap.xml` is accessible.
- If you see malformed XML errors, installing `lxml` often helps (BeautifulSoup will use it when available).

If you'd like, I can:
- Run the script on your existing `sitemap-urls/domains.csv` and save the results.
- Add a `requirements.txt` or a small wrapper to run in parallel.
