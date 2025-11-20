#!/usr/bin/env python3
"""Generate Googlebot log reports with UA and URL grouping."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence

Config = Dict[str, Any]

CHROME_VERSION_PATTERN = re.compile(r"Chrome/(\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Augment Googlebot logs with UA and URL grouping metadata."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the source CSV file.",
    )
    parser.add_argument(
        "--output",
        required=False,
        help="Destination path for the augmented CSV file. If omitted, the input file is updated in place.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the JSON file with UA and URL grouping configuration.",
    )
    parser.add_argument(
        "--sitemap",
        required=False,
        help="Optional path to a sitemap file (txt list of URLs or CSV with a 'URL' column).",
    )
    parser.add_argument(
        "--ua-summary-output",
        required=False,
        help="Destination path for the UA summary CSV. If omitted, defaults to <input>-ua-summary.csv.",
    )
    parser.add_argument(
        "--url-summary-output",
        required=False,
        help="Destination path for the URL summary CSV. If omitted, defaults to <input>-url-summary.csv.",
    )
    return parser.parse_args()


def load_config(path: Path) -> Config:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_sitemap_urls(path: Path | None) -> set[str]:
    """Load URLs from a txt (one per line) or CSV file containing a 'URL' column."""
    if path is None or not path.exists():
        return set()

    suffix = path.suffix.lower()
    urls: set[str] = set()

    if suffix == ".txt":
        with path.open(encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if url:
                    urls.add(url)
        return urls

    try:
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except OSError:
        return set()

    if not rows:
        return set()

    header = rows[0]
    try:
        url_idx = header.index("URL")
    except ValueError:
        return set()

    for row in rows[1:]:
        if url_idx < len(row):
            url = row[url_idx].strip()
            if url:
                urls.add(url)

    return urls


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if str(item)]


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_version_range(value: Any) -> tuple[int | None, int | None]:
    if value is None:
        return (None, None)
    if isinstance(value, dict):
        return to_int(value.get("min")), to_int(value.get("max"))
    if isinstance(value, (list, tuple)):
        min_val = to_int(value[0]) if len(value) > 0 else None
        max_val = to_int(value[1]) if len(value) > 1 else None
        return (min_val, max_val)
    if isinstance(value, str) and "-" in value:
        start, end = value.split("-", 1)
        return to_int(start), to_int(end)
    version = to_int(value)
    return (version, version)


def _string_conditions_match(
    value: str,
    value_lower: str,
    conditions: Dict[str, Any],
) -> bool:
    normalized = {str(key).lower(): val for key, val in conditions.items()}

    for pattern in _ensure_list(normalized.get("regex")):
        try:
            if not re.search(pattern, value, flags=re.IGNORECASE):
                return False
        except re.error:
            return False

    for prefix in _ensure_list(normalized.get("starts-with")):
        if not value_lower.startswith(prefix.lower()):
            return False

    contains_terms = _ensure_list(normalized.get("contains"))
    for term in contains_terms:
        if term.lower() not in value_lower:
            return False

    not_contains_terms = _ensure_list(normalized.get("not-contains"))
    for term in not_contains_terms:
        if term.lower() in value_lower:
            return False

    equal_terms = _ensure_list(normalized.get("equals")) + _ensure_list(
        normalized.get("equal")
    )
    for term in equal_terms:
        if value != term:
            return False

    not_equal_terms = _ensure_list(normalized.get("not-equals")) + _ensure_list(
        normalized.get("not-equal")
    )
    for term in not_equal_terms:
        if value == term:
            return False

    return True


def extract_chrome_version(user_agent: str) -> int | None:
    match = CHROME_VERSION_PATTERN.search(user_agent)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def rule_conditions_match(
    ua: str,
    ua_lower: str,
    chrome_version: int | None,
    conditions: Dict[str, Any],
    default_chrome_min: int | None,
) -> bool:
    normalized_conditions = {str(key).lower(): value for key, value in conditions.items()}

    if not _string_conditions_match(ua, ua_lower, normalized_conditions):
        return False

    min_version = to_int(normalized_conditions.get("chrome_min_version"))
    max_version = to_int(normalized_conditions.get("chrome_max_version"))
    exact_version = to_int(normalized_conditions.get("chrome_version"))
    range_min, range_max = _parse_version_range(
        normalized_conditions.get("chrome_version_range")
    )

    if exact_version is not None:
        min_version = exact_version
        max_version = exact_version

    if range_min is not None:
        if min_version is None:
            min_version = range_min
        else:
            min_version = max(min_version, range_min)

    if range_max is not None:
        if max_version is None:
            max_version = range_max
        else:
            max_version = min(max_version, range_max)

    if min_version is None and max_version is None:
        min_version = default_chrome_min

    if min_version is not None or max_version is not None:
        if chrome_version is None:
            return False

        if min_version is not None and chrome_version < min_version:
            return False

        if max_version is not None and chrome_version > max_version:
            return False

    return True


def classify_user_agent(user_agent: str, config: Config) -> str:
    if not user_agent:
        return "unknown"

    ua_lower = user_agent.lower()

    chrome_version = extract_chrome_version(user_agent)
    parameters = config.get("parameters", {})
    default_chrome_min = to_int(parameters.get("chrome_min_version"))

    rules: Sequence[Dict[str, Any]] = config.get("ua_rules") or config.get("rules", [])
    for rule in rules:
        conditions = rule.get("conditions", {})
        if rule_conditions_match(
            user_agent, ua_lower, chrome_version, conditions, default_chrome_min
        ):
            groups = rule.get("groups", [])
            if isinstance(groups, str):
                groups = [groups]
            groups = [g for g in groups if g]
            if groups:
                return ";".join(groups)

    default_groups = config.get("default_groups", ["other"])
    if isinstance(default_groups, str):
        default_groups = [default_groups]
    default_groups = [g for g in default_groups if g]
    if default_groups:
        return ";".join(default_groups)

    return "unknown"


def _normalize_condition_sets(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_conditions = rule.get("conditions")
    if raw_conditions is None:
        raw_conditions = rule.get("rules")

    if raw_conditions is None:
        return []

    if isinstance(raw_conditions, list):
        return [cond for cond in raw_conditions if isinstance(cond, dict)]

    if isinstance(raw_conditions, dict):
        return [raw_conditions]

    return []


def classify_url(url: str, config: Config) -> str:
    if not url:
        return "unknown"

    url_lower = url.lower()
    url_rules: Sequence[Dict[str, Any]] = config.get("url_rules", [])

    matched_groups: List[str] = []

    for rule in url_rules:
        condition_sets = _normalize_condition_sets(rule)
        if not condition_sets:
            continue

        if all(
            _string_conditions_match(url, url_lower, {str(k).lower(): v for k, v in cond.items()})
            for cond in condition_sets
        ):
            groups = rule.get("groups", [])
            if isinstance(groups, str):
                groups = [groups]
            for group in (g for g in groups if g):
                if group not in matched_groups:
                    matched_groups.append(group)

    if matched_groups:
        return ";".join(matched_groups)

    return "unknown"


def locate_header(rows: List[List[str]]) -> int:
    for idx, row in enumerate(rows):
        if row and row[0] == "URL":
            return idx
    raise RuntimeError("Could not locate the data header (row starting with 'URL').")


def find_date_column(header: List[str]) -> int | None:
    """Find the date column; assume it is named 'Timestamp'."""
    try:
        return header.index("Timestamp")
    except ValueError:
        return None


def parse_date(date_str: str) -> str | None:
    """Parse a date string and return it in YYYY-MM-DD format."""
    if not date_str or not date_str.strip():
        return None
    
    # Normalize the typical Unicode narrow/non-breaking spaces used by SF exports.
    date_str = (
        date_str.strip()
        .replace("\u202f", " ")
        .replace("\xa0", " ")
    )
    
    # Try common date formats
    date_formats = [
        "%b %d, %Y, %I:%M:%S %p",  # e.g. Nov 17, 2025, 4:31:08 AM
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def collect_config_url_groups(config: Config) -> List[str]:
    """Return url-group names defined in the config, preserving order."""
    url_rules: Sequence[Dict[str, Any]] = config.get("url_rules", [])
    seen = set()
    groups: List[str] = []

    for rule in url_rules:
        raw_groups = rule.get("groups", [])
        if isinstance(raw_groups, str):
            raw_groups = [raw_groups]
        for group in raw_groups:
            if group and group not in seen:
                seen.add(group)
                groups.append(group)

    return groups


def generate_daily_ua_group_report(
    data_rows: List[List[str]],
    ua_group_idx: int,
    date_idx: int | None,
    output_path: Path,
) -> None:
    """Generate a daily report of UA groups by date."""
    # Count events per day per ua-group
    daily_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    all_dates: set[str] = set()
    all_ua_groups: set[str] = set()
    
    for row in data_rows:
        if ua_group_idx >= len(row):
            continue
        
        ua_group = row[ua_group_idx] if ua_group_idx < len(row) else "unknown"
        if not ua_group:
            ua_group = "unknown"
        
        # Handle multiple groups (semicolon-separated)
        ua_groups = [g.strip() for g in ua_group.split(";") if g.strip()]
        if not ua_groups:
            ua_groups = ["unknown"]
        
        date_str = None
        if date_idx is not None and date_idx < len(row):
            date_str = parse_date(row[date_idx])
        
        if date_str:
            all_dates.add(date_str)
            for group in ua_groups:
                all_ua_groups.add(group)
                daily_counts[date_str][group] += 1
        else:
            # If no date found, use "unknown" date
            all_dates.add("unknown")
            for group in ua_groups:
                all_ua_groups.add(group)
                daily_counts["unknown"][group] += 1
    
    if not all_dates:
        # No dates found, skip report
        return
    
    # Sort dates
    sorted_dates = sorted([d for d in all_dates if d != "unknown"])
    if "unknown" in all_dates:
        sorted_dates.append("unknown")
    
    # Sort UA groups
    sorted_ua_groups = sorted(all_ua_groups)
    
    # Write report
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        
        # Header row
        header_row = ["ua-group"] + sorted_dates
        writer.writerow(header_row)
        
        # Data rows for each UA group
        for ua_group in sorted_ua_groups:
            row = [ua_group]
            for date in sorted_dates:
                count = daily_counts[date].get(ua_group, 0)
                row.append(count)
            writer.writerow(row)
        
        # TOTAL row
        total_row = ["TOTAL"]
        for date in sorted_dates:
            total = sum(daily_counts[date].values())
            total_row.append(total)
        writer.writerow(total_row)


def generate_daily_url_group_report(
    data_rows: List[List[str]],
    url_group_idx: int,
    date_idx: int | None,
    sitemap_idx: int | None,
    output_path: Path,
    configured_groups: List[str],
) -> None:
    """Generate a daily report of URL groups by date using config-defined groups."""
    daily_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    daily_event_counts: Dict[str, int] = defaultdict(int)
    daily_sitemap_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    all_dates: set[str] = set()

    observed_extra_groups: set[str] = set()

    for row in data_rows:
        if url_group_idx >= len(row):
            continue

        url_group_value = row[url_group_idx] if url_group_idx < len(row) else "unknown"
        if not url_group_value:
            url_group_value = "unknown"

        url_groups = [g.strip() for g in url_group_value.split(";") if g.strip()]
        if not url_groups:
            url_groups = ["unknown"]

        date_str = None
        if date_idx is not None and date_idx < len(row):
            date_str = parse_date(row[date_idx])

        if date_str is None:
            date_str = "unknown"
        all_dates.add(date_str)
        daily_event_counts[date_str] += 1
        sitemap_flag = "0"
        if sitemap_idx is not None and sitemap_idx < len(row):
            if str(row[sitemap_idx]).strip() == "1":
                sitemap_flag = "1"
        daily_sitemap_counts[date_str][sitemap_flag] += 1

        for url_group in url_groups:
            daily_counts[date_str][url_group] += 1
            if url_group not in configured_groups:
                observed_extra_groups.add(url_group)

    if not all_dates:
        return

    sorted_dates = sorted([d for d in all_dates if d != "unknown"])
    if "unknown" in all_dates:
        sorted_dates.append("unknown")

    # Include configured groups first, then any observed extras to avoid losing counts.
    group_rows = list(configured_groups)
    for group in sorted(observed_extra_groups):
        if group not in group_rows:
            group_rows.append(group)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["url-group"] + sorted_dates)

        for url_group in group_rows:
            row = [url_group]
            for date in sorted_dates:
                row.append(daily_counts[date].get(url_group, 0))
            writer.writerow(row)

        sitemap_row = ["sitemap"]
        for date in sorted_dates:
            sitemap_row.append(daily_sitemap_counts[date].get("1", 0))
        writer.writerow(sitemap_row)

        not_in_sitemap_row = ["not in sitemap"]
        for date in sorted_dates:
            not_in_sitemap_row.append(daily_sitemap_counts[date].get("0", 0))
        writer.writerow(not_in_sitemap_row)

        total_row = ["TOTAL"]
        for date in sorted_dates:
            total_row.append(daily_event_counts.get(date, 0))
        writer.writerow(total_row)


def process_logs(
    input_path: Path,
    output_path: Path,
    summary_path: Path | None,
    url_summary_path: Path | None,
    config_path: Path,
    config: Config,
    sitemap_urls: set[str],
) -> None:
    with input_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    header_idx = locate_header(rows)
    prefix_rows = rows[:header_idx]
    header = rows[header_idx]
    data_rows = rows[header_idx + 1 :]
    total_rows = len(data_rows)

    csv_name = str(input_path.resolve())
    config_name = str(config_path.resolve())
    print(f"Processing {csv_name}, {total_rows:,} lines")
    print(f"Assigning User Agent groups based on rules in {config_name}")

    def remove_column(rows: List[List[str]], idx: int) -> List[List[str]]:
        trimmed: List[List[str]] = []
        for row in rows:
            if len(row) > idx:
                trimmed.append(row[:idx] + row[idx + 1 :])
            else:
                padded = row + [""] * (idx + 1 - len(row))
                trimmed.append(padded[:idx] + padded[idx + 1 :])
        return trimmed

    while "ua-group" in header:
        group_idx = header.index("ua-group")
        header = header[:group_idx] + header[group_idx + 1 :]
        data_rows = remove_column(data_rows, group_idx)

    while "url-group" in header:
        group_idx = header.index("url-group")
        header = header[:group_idx] + header[group_idx + 1 :]
        data_rows = remove_column(data_rows, group_idx)

    while "sitemap" in header:
        group_idx = header.index("sitemap")
        header = header[:group_idx] + header[group_idx + 1 :]
        data_rows = remove_column(data_rows, group_idx)

    try:
        ua_idx = header.index("User Agent")
    except ValueError as exc:
        raise RuntimeError("'User Agent' column not found in header.") from exc

    try:
        url_idx = header.index("URL")
    except ValueError as exc:
        raise RuntimeError("'URL' column not found in header.") from exc

    source_date_idx = find_date_column(header)
    header_with_groups = header + ["ua-group", "url-group", "sitemap", "date"]

    summary_counts: Dict[tuple[str, str], int] = {}
    url_summary_counts: Dict[tuple[str, str], int] = {}
    progress_width = 40

    def render_progress(current: int) -> None:
        if total_rows == 0:
            return
        filled = int(progress_width * current / total_rows)
        bar = "#" * filled + "-" * (progress_width - filled)
        print(f"\r[{bar}] {current}/{total_rows}", end="", flush=True)

    updated_data = []
    for idx, row in enumerate(data_rows, start=1):
        ua_value = row[ua_idx] if ua_idx < len(row) else ""
        url_value = row[url_idx] if url_idx < len(row) else ""
        ua_group = classify_user_agent(ua_value, config)
        url_group = classify_url(url_value, config)
        sitemap_flag = "1" if url_value in sitemap_urls else "0"
        date_value = ""
        if source_date_idx is not None and source_date_idx < len(row):
            parsed_date = parse_date(row[source_date_idx])
            if parsed_date:
                date_value = parsed_date
        updated_row = row + [ua_group, url_group, sitemap_flag, date_value]
        updated_data.append(updated_row)
        key = (ua_value, ua_group)
        summary_counts[key] = summary_counts.get(key, 0) + 1
        url_key = (url_value, url_group)
        url_summary_counts[url_key] = url_summary_counts.get(url_key, 0) + 1
        render_progress(idx)

    if total_rows > 0:
        print()

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(prefix_rows)
        writer.writerow(header_with_groups)
        writer.writerows(updated_data)

    if summary_path is not None:
        with summary_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["User Agent", "ua-group", "count"])
            for (ua_value, ua_group), count in sorted(
                summary_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
            ):
                writer.writerow([ua_value, ua_group, count])
        print(f"Saved UA summary CSV to {summary_path.resolve()}")

    if url_summary_path is not None:
        with url_summary_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "url-group", "count"])
            for (url_value, url_group), count in sorted(
                url_summary_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
            ):
                writer.writerow([url_value, url_group, count])
        print(f"Saved URL summary CSV to {url_summary_path.resolve()}")
    
    # Generate daily UA group report
    date_idx = header_with_groups.index("date")
    ua_group_idx = header_with_groups.index("ua-group")
    report_filename = f"{input_path.stem}-report-ua-groups.csv"
    report_path = input_path.parent / report_filename
    generate_daily_ua_group_report(updated_data, ua_group_idx, date_idx, report_path)

    # Generate daily URL group report using config-defined groups
    url_group_idx = header_with_groups.index("url-group")
    url_report_filename = f"{input_path.stem}-report-url-groups.csv"
    url_report_path = input_path.parent / url_report_filename
    configured_url_groups = collect_config_url_groups(config)
    sitemap_idx = header_with_groups.index("sitemap")
    generate_daily_url_group_report(
        updated_data,
        url_group_idx,
        date_idx,
        sitemap_idx,
        url_report_path,
        configured_url_groups,
    )
    
    print(f"Saved augmented CSV to {output_path.resolve()}")
    print(f"Saved daily UA group report to {report_path.resolve()}")
    print(f"Saved daily URL group report to {url_report_path.resolve()}")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path
    config_path = Path(args.config)
    sitemap_path = Path(args.sitemap) if args.sitemap else None
    config = load_config(config_path)
    sitemap_urls = load_sitemap_urls(sitemap_path)
    summary_output_path = (
        Path(args.ua_summary_output)
        if args.ua_summary_output
        else input_path.with_name(f"{input_path.stem}-ua-summary.csv")
    )
    url_summary_output_path = (
        Path(args.url_summary_output)
        if args.url_summary_output
        else input_path.with_name(f"{input_path.stem}-url-summary.csv")
    )
    process_logs(
        input_path,
        output_path,
        summary_output_path,
        url_summary_output_path,
        config_path,
        config,
        sitemap_urls,
    )


if __name__ == "__main__":
    main()
