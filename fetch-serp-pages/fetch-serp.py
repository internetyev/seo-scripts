#!/usr/bin/env python3
"""
Fetch full Google SERP pages from the DataForSEO API.

This script is inspired by `paa-fetch/paa-fetch.py` and is focused on saving
raw JSON responses and/or plain-text SERP content for one or more queries.

Features:
- -q / --query       : single query
- -f / --file        : text file with one query per line
- --json             : save raw JSON response (default behaviour)
- --txt              : save only extracted textual content from SERP
- --silent           : do not print JSON to stdout
- --depth            : depth of search results (10 by default, up to 100)

JSON files are stored in the same directory as this script by default,
one file per query.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests

from config import (
    DATAFORSEO_USERNAME,
    DATAFORSEO_PASSWORD,
    DEFAULT_LANGUAGE_CODE,
    DEFAULT_LOCATION_CODE,
    DEFAULT_DEPTH,
    SERP_API_URL,
)


def sanitize_query_for_filename(query: str) -> str:
    """Create a filesystem-friendly filename part from a query string."""
    sanitized = query.strip().lower()
    # Replace spaces with dashes and remove problematic characters
    for ch in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>', "'", "#"]:
        sanitized = sanitized.replace(ch, " ")
    sanitized = "-".join(part for part in sanitized.split() if part)
    if not sanitized:
        sanitized = "query"
    return sanitized


def read_queries_from_file(file_path: str) -> List[str]:
    """Read queries from a text file (one per line)."""
    if not os.path.exists(file_path):
        print(f"Error: queries file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    queries: List[str] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            q = line.strip()
            if q:
                queries.append(q)

    if not queries:
        print("Error: no non-empty queries found in file", file=sys.stderr)
        sys.exit(1)

    return queries


def fetch_serp_raw(
    query: str,
    depth: int,
    language_code: str,
    location_code: int,
) -> Dict[str, Any]:
    """Call DataForSEO SERP API for a single query and return raw JSON."""
    payload = [
        {
            "keyword": query,
            "language_code": language_code,
            "location_code": location_code,
            "device": "desktop",
            "depth": depth,
        }
    ]

    try:
        response = requests.post(
            SERP_API_URL,
            auth=(DATAFORSEO_USERNAME, DATAFORSEO_PASSWORD),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Network error: {e}") from e

    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP error: status {response.status_code}, body: {response.text[:500]}"
        )

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response: {e}") from e

    # DataForSEO standard success code
    if data.get("status_code") != 20000:
        raise RuntimeError(
            f"DataForSEO error: status_code={data.get('status_code')}, "
            f"status_message={data.get('status_message')}"
        )

    return data


def extract_text_from_serp(data: Dict[str, Any]) -> str:
    """
    Extract human-readable text from SERP JSON for:
    - organic results
    - AI overviews (if present)
    - People Also Ask
    - related searches
    - knowledge panels / knowledge graph

    This is best-effort and tolerant to missing fields / schema changes.
    """
    lines: List[str] = []

    tasks = data.get("tasks", [])
    for task in tasks:
        results = task.get("result", [])
        for result in results:
            items = result.get("items", [])
            for item in items:
                itype = item.get("type")

                # Organic results
                if itype == "organic":
                    title = item.get("title")
                    snippet = item.get("description") or item.get("snippet")
                    url = item.get("url")
                    if title:
                        lines.append(f"[ORGANIC] {title}")
                    if snippet:
                        lines.append(snippet)
                    if url:
                        lines.append(f"URL: {url}")
                    lines.append("")

                # People Also Ask
                elif itype == "people_also_ask":
                    paa_items = item.get("items", [])
                    for paa in paa_items:
                        if paa.get("type") == "people_also_ask_element":
                            title = paa.get("title")
                            snippet = paa.get("snippet")
                            if title:
                                lines.append(f"[PAA] {title}")
                            if snippet:
                                lines.append(snippet)
                            lines.append("")

                # Related searches
                elif itype == "related_searches":
                    related_items = item.get("items", [])
                    for rel in related_items:
                        kw = rel.get("keyword") or rel.get("title")
                        if kw:
                            lines.append(f"[RELATED] {kw}")
                    lines.append("")

                # Knowledge graph / panel
                elif itype in {"knowledge_graph", "knowledge_panel"}:
                    title = item.get("title")
                    desc = item.get("description")
                    if title:
                        lines.append(f"[KNOWLEDGE] {title}")
                    if desc:
                        lines.append(desc)
                    lines.append("")

                # AI overview (name may vary, be defensive)
                elif itype in {"ai_overview", "ai_overview_extended", "ai_overview_element"}:
                    title = item.get("title")
                    summary = item.get("snippet") or item.get("description") or item.get(
                        "answer"
                    )
                    if title:
                        lines.append(f"[AI OVERVIEW] {title}")
                    if summary:
                        lines.append(summary)
                    lines.append("")

    return "\n".join(line for line in lines if line is not None)


def save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(text)


def main() -> None:
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(
        description="Fetch Google SERP pages from DataForSEO and save raw JSON and/or text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fetch-serp.py -q "best running shoes"
  fetch-serp.py -q "best running shoes" --txt
  fetch-serp.py -f queries.txt --depth 50 --txt --json

Notes:
  - By default JSON is saved (one file per query) in the same directory as this script.
  - Depth must be between 10 and 100 (inclusive), default is 10.
""",
    )

    input_group = parser.add_argument_group("Input (at least one required)")
    input_group.add_argument(
        "-q",
        "--query",
        type=str,
        help="Single query string",
    )
    input_group.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path to text file with one query per line",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=10,
        help="Depth of search results (10 by default, up to 100)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Save raw JSON file(s) (enabled by default if neither --json nor --txt is given).",
    )
    parser.add_argument(
        "--txt",
        action="store_true",
        help="Save only texts from Google SERP (AI overviews, PAA, related searches, knowledge panel, etc.).",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Do not print JSON response to stdout.",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.query and not args.file:
        parser.error("Either --query or --file (or both) must be provided.")

    if args.depth < 10 or args.depth > 100:
        parser.error("--depth must be between 10 and 100 (inclusive).")

    # Determine what to save: default is JSON if nothing explicitly selected
    save_json_flag = args.json or not args.txt
    save_txt_flag = args.txt

    # Collect queries
    queries: List[str] = []
    if args.query:
        queries.append(args.query)
    if args.file:
        queries.extend(read_queries_from_file(args.file))

    for q in queries:
        q_label = q[:60] + ("..." if len(q) > 60 else "")
        try:
            data = fetch_serp_raw(
                q,
                depth=args.depth or DEFAULT_DEPTH,
                language_code=DEFAULT_LANGUAGE_CODE,
                location_code=DEFAULT_LOCATION_CODE,
            )
        except Exception as e:
            print(f"Error fetching SERP for '{q_label}': {e}", file=sys.stderr)
            continue

        base_name = sanitize_query_for_filename(q)
        json_path = script_dir / f"{base_name}_serp_depth{args.depth}.json"
        txt_path = script_dir / f"{base_name}_serp_depth{args.depth}.txt"

        if save_json_flag:
            save_json(data, json_path)
            if not args.silent:
                # Print JSON to stdout only for single query to avoid huge output with many
                if len(queries) == 1:
                    print(json.dumps(data, ensure_ascii=False, indent=2))

        if save_txt_flag:
            text = extract_text_from_serp(data)
            save_text(text, txt_path)

        if not args.silent:
            saved_parts = []
            if save_json_flag:
                saved_parts.append(f"JSON -> {json_path}")
            if save_txt_flag:
                saved_parts.append(f"TXT -> {txt_path}")
            summary = "; ".join(saved_parts) if saved_parts else "no output files requested"
            print(f"Query '{q_label}' processed: {summary}")


if __name__ == "__main__":
    main()


