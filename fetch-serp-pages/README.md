## fetch-serp-pages

`fetch-serp.py` is a small CLI helper that fetches full Google SERP pages from the DataForSEO API and saves:

- **Raw JSON** responses (one file per query)
- **Plain-text SERP snippets** (organic results, AI overviews, People Also Ask, related searches, knowledge panels, etc.)

It is modeled after `paa-fetch/paa-fetch.py` but focused on full SERP capture.

---

### Requirements & installation

- Python 3.8+ recommended
- Dependencies:
  - `requests`

From the project root:

```bash
pip install -r paa-fetch/requirements.txt
```

*(The same `requirements.txt` used for `paa-fetch.py` includes `requests`.)*

---

### Configuration (`config.py`)

`fetch-serp.py` reads DataForSEO credentials and defaults from `config.py` in the same folder:

- **Credentials**
  - `DATAFORSEO_USERNAME`
  - `DATAFORSEO_PASSWORD`
- **Defaults**
  - `DEFAULT_LOCATION_CODE` – DataForSEO `location_code` (e.g. `2840` for US)
  - `DEFAULT_LANGUAGE_CODE` – language code (e.g. `"en"`)
  - `DEFAULT_DEPTH` – fallback depth for SERP results
- **Endpoint**
  - `SERP_API_URL` – currently `https://api.dataforseo.com/v3/serp/google/organic/live/regular`

Make sure these values are set correctly before running the script.

---

### CLI usage

Run from the `fetch-serp-pages` directory:

```bash
cd fetch-serp-pages
python3 fetch-serp.py [options]
```

**Input options (at least one is required):**

- `-q`, `--query` **\<string\>**  
  Single query string.

- `-f`, `--file` **\<path\>**  
  Path to a text file with **one query per line**.  
  You can combine `-q` and `-f`; all queries will be processed.

**Output options:**

- `--json`  
  Save raw JSON response file(s).  
  - If **neither** `--json` nor `--txt` are provided, **JSON is saved by default**.

- `--txt`  
  Save extracted SERP **text-only** file(s). Texts may include:
  - Organic result titles, snippets, URLs
  - People Also Ask questions and snippets
  - Related searches
  - Knowledge panel / knowledge graph titles and descriptions
  - AI overview snippets (best-effort)

- `--silent`  
  Do not print JSON to stdout.  
  - Without `--silent`, for a **single query** the full JSON is printed in addition to being saved to disk.

**Depth:**

- `--depth` **\<int\>**  
  Depth of search results; passed as `depth` to the DataForSEO request.  
  - Default: `10`  
  - Allowed range: **10–100** (validated by the script).

---

### Output files

Files are saved in the **same directory as `fetch-serp.py`**.

For a query like:

```bash
python3 fetch-serp.py -q "best running shoes" --depth 10 --json --txt
```

You will typically get:

- `best-running-shoes_serp_depth10.json` – raw DataForSEO response
- `best-running-shoes_serp_depth10.txt` – extracted SERP text

Filenames are generated from the query:

- Lowercased
- Special characters removed
- Spaces collapsed into `-`

---

### Common examples

- **Single query, JSON only (default behaviour):**

```bash
python3 fetch-serp.py -q "best running shoes"
```

- **Single query, JSON + TXT, depth 50, silent:**

```bash
python3 fetch-serp.py -q "best running shoes" --depth 50 --json --txt --silent
```

- **Multiple queries from a file, TXT only:**

```bash
python3 fetch-serp.py -f queries.txt --txt
```

- **Single query, text-only (no JSON):**

```bash
python3 fetch-serp.py -q "seo tools" --txt
```

---

### Notes & tips

- Depth values above 100 are not allowed and will cause an error; DataForSEO also enforces its own limits.
- For large query lists, consider using `--silent` to avoid huge JSON dumps in the terminal.
- You can further customize which SERP blocks are included in the TXT output by editing the `extract_text_from_serp` function inside `fetch-serp.py`.


