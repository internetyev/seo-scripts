import argparse
import csv
import json
import sys
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup


@dataclass
class UrlSchemas:
    url: str
    status_code: int
    schemas: Set[str]


def fetch_html(url: str, timeout: int = 15) -> Tuple[str, int]:
    """Fetch a URL and return its HTML content and HTTP status code."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text, resp.status_code


def _collect_types_from_jsonld_obj(obj, types: Set[str]) -> None:
    """Recursively collect @type values from a JSON-LD object."""
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, str):
            types.add(t)
        elif isinstance(t, list):
            for item in t:
                if isinstance(item, str):
                    types.add(item)
        for v in obj.values():
            _collect_types_from_jsonld_obj(v, types)
    elif isinstance(obj, list):
        for item in obj:
            _collect_types_from_jsonld_obj(item, types)


def extract_schema_types(html: str) -> Set[str]:
    """
    Extract schema.org types from HTML.

    - JSON-LD in <script type="application/ld+json">
    - Microdata via itemtype attributes that contain 'schema.org'
    - RDFa-ish via typeof attributes that contain 'schema.org'
    """
    soup = BeautifulSoup(html, "html.parser")
    types: Set[str] = set()

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            # Some sites include invalid JSON-LD; ignore errors.
            continue
        _collect_types_from_jsonld_obj(data, types)

    # Microdata itemtype attributes
    for tag in soup.find_all(attrs={"itemtype": True}):
        itemtype_val = tag.get("itemtype", "")
        if not itemtype_val:
            continue
        for token in str(itemtype_val).split():
            if "schema.org" in token:
                # Take the last path segment as the type name
                type_name = token.rstrip("/").split("/")[-1]
                if type_name:
                    types.add(type_name)

    # RDFa typeof attributes (basic heuristic)
    for tag in soup.find_all(attrs={"typeof": True}):
        typeof_val = tag.get("typeof", "")
        if not typeof_val:
            continue
        for token in str(typeof_val).split():
            if "schema.org" in token:
                type_name = token.rstrip("/").split("/")[-1]
                if type_name:
                    types.add(type_name)

    return types


def analyze_url(url: str) -> UrlSchemas:
    """Fetch a URL and return detected schema.org types."""
    try:
        html, status_code = fetch_html(url)
    except Exception as exc:  # noqa: BLE001
        print(f"Error fetching {url}: {exc}", file=sys.stderr)
        # Use status_code 0 to indicate that the page was not readable / no response.
        return UrlSchemas(url=url, status_code=0, schemas=set())

    schemas = extract_schema_types(html)
    return UrlSchemas(url=url, status_code=status_code, schemas=schemas)


def load_urls_from_file(path: str) -> List[str]:
    """
    Load URLs from a TXT or CSV file.

    - TXT: one URL per line (ignores blank lines and comments starting with '#')
    - CSV: takes the first column of each row (ignores header if present)
    """
    lower = path.lower()
    urls: List[str] = []

    if lower.endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                urls.append(line)
    elif lower.endswith(".csv"):
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                first = row[0].strip()
                if not first or first.lower().startswith("url"):
                    # Skip empty and 'URL' header-like rows
                    continue
                urls.append(first)
    else:
        raise ValueError("Unsupported file type. Use .txt or .csv")

    return urls


def write_results_to_csv(results: List[UrlSchemas], output_path: str) -> None:
    """Write the collected schema data to a CSV file."""
    # Collect all unique schema types across all URLs
    all_types: Set[str] = set()
    for res in results:
        all_types.update(res.schemas)

    sorted_types = sorted(all_types)
    header: List[str] = ["URL", "status_code"] + sorted_types

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for res in results:
            row = [res.url, str(res.status_code)]
            present = res.schemas
            for t in sorted_types:
                row.append("1" if t in present else "0")
            writer.writerow(row)


def results_to_table(results: List[UrlSchemas]) -> Tuple[List[str], List[List[str]]]:
    """
    Build a CSV-like table (header + rows) from results, for printing.
    """
    all_types: Set[str] = set()
    for res in results:
        all_types.update(res.schemas)

    sorted_types = sorted(all_types)
    header: List[str] = ["URL", "status_code"] + sorted_types

    rows: List[List[str]] = []
    for res in results:
        row = [res.url, str(res.status_code)]
        for t in sorted_types:
            row.append("1" if t in res.schemas else "0")
        rows.append(row)

    return header, rows


def print_table_as_csv_like(header: List[str], rows: List[List[str]]) -> None:
    """Print a simple CSV-like table to stdout."""
    print(",".join(header))
    for row in rows:
        print(",".join(row))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check which schema.org markup types are present on one or more URLs "
            "and output a CSV presence matrix."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file",
        dest="file",
        help="Path to TXT (one URL per line) or CSV (take first column) file with URLs.",
    )
    group.add_argument(
        "--url",
        dest="url",
        help="Single URL to analyze.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        help=(
            "Output CSV filename (with or without path). "
            "If not specified for --url, results are printed to the terminal."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    if args.file:
        urls = load_urls_from_file(args.file)
        if not urls:
            print("No URLs found in input file.", file=sys.stderr)
            sys.exit(1)

        results: List[UrlSchemas] = []
        for url in urls:
            print(f"Processing {url}...", file=sys.stderr)
            results.append(analyze_url(url))

        output_path = args.output or "schema_results.csv"
        write_results_to_csv(results, output_path)
        print(f"Results written to {output_path}")
    else:
        # Single URL mode
        result = analyze_url(args.url)
        results = [result]
        header, rows = results_to_table(results)

        if args.output:
            write_results_to_csv(results, args.output)
            print(f"Results written to {args.output}")
        else:
            # Print as CSV-style text to terminal
            print_table_as_csv_like(header, rows)


if __name__ == "__main__":
    main()


