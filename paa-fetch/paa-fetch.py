#!/usr/bin/env python3
"""
Fetch People Also Ask (PAA) questions from DataForSEO Google Organic Live Advanced endpoint.

This script accepts keywords via --keyword or --file and outputs PAA questions
in CSV or JSON format.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from tqdm import tqdm

# DataForSEO API endpoint
API_URL = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"

# Country code to location_code mapping
# Common countries with their DataForSEO location codes
COUNTRY_TO_LOCATION_CODE: Dict[str, int] = {
    "US": 2840,  # United States
    "GB": 2826,  # United Kingdom
    "CA": 2124,  # Canada
    "AU": 2036,  # Australia
    "DE": 2276,  # Germany
    "FR": 2250,  # France
    "ES": 2724,  # Spain
    "IT": 2380,  # Italy
    "NL": 2528,  # Netherlands
    "BE": 2056,  # Belgium
    "CH": 2756,  # Switzerland
    "AT": 2040,  # Austria
    "SE": 2752,  # Sweden
    "NO": 2578,  # Norway
    "DK": 2208,  # Denmark
    "FI": 2246,  # Finland
    "PL": 2616,  # Poland
    "IE": 2372,  # Ireland
    "NZ": 2554,  # New Zealand
    "JP": 2392,  # Japan
    "KR": 2410,  # South Korea
    "IN": 2356,  # India
    "BR": 2076,  # Brazil
    "MX": 2484,  # Mexico
    "AR": 2032,  # Argentina
    "CL": 2152,  # Chile
    "CO": 2170,  # Colombia
    "ZA": 2710,  # South Africa
    "AE": 2784,  # United Arab Emirates
    "SG": 2702,  # Singapore
    "MY": 2458,  # Malaysia
    "TH": 2764,  # Thailand
    "PH": 2608,  # Philippines
    "ID": 2360,  # Indonesia
    "VN": 2704,  # Vietnam
    "TW": 2158,  # Taiwan
    "HK": 2344,  # Hong Kong
    "CN": 2156,  # China
    "RU": 2642,  # Russia
    "TR": 2792,  # Turkey
    "GR": 2300,  # Greece
    "PT": 2620,  # Portugal
    "CZ": 2203,  # Czech Republic
    "HU": 2348,  # Hungary
    "RO": 2642,  # Romania
    "UA": 2804,  # Ukraine
}


def load_config(config_path: str) -> Tuple[str, str]:
    """
    Load and validate DataForSEO config file.
    
    Args:
        config_path: Path to JSON config file
        
    Returns:
        Tuple of (api_login, api_password)
        
    Raises:
        SystemExit: If config file is missing or invalid
    """
    expanded_path = os.path.expanduser(config_path)
    
    if not os.path.exists(expanded_path):
        print(f"Error: Config file not found: {expanded_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(expanded_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read config file: {e}", file=sys.stderr)
        sys.exit(1)
    
    api_login = config.get("api_login")
    api_password = config.get("api_password")
    
    if not api_login or not api_password:
        print(
            "Error: Config file must contain 'api_login' and 'api_password' fields",
            file=sys.stderr
        )
        sys.exit(1)
    
    return api_login, api_password


def dfs_country_to_location_code(country: str) -> int:
    """
    Convert ISO 2-letter country code to DataForSEO location_code.
    
    Args:
        country: ISO 2-letter country code (e.g., "US", "GB")
        
    Returns:
        DataForSEO location_code integer
        
    Raises:
        SystemExit: If country code is not in the mapping
    """
    country_upper = country.upper()
    
    if country_upper not in COUNTRY_TO_LOCATION_CODE:
        print(
            f"Unknown country code {country}. Please update location mapping or use a supported code.",
            file=sys.stderr
        )
        sys.exit(1)
    
    return COUNTRY_TO_LOCATION_CODE[country_upper]


def read_keywords_from_file(file_path: str) -> List[str]:
    """
    Read keywords from a text file (one per line).
    
    Args:
        file_path: Path to keywords file
        
    Returns:
        List of keyword strings (empty lines and whitespace-only lines are ignored)
    """
    keywords = []
    
    if not os.path.exists(file_path):
        print(f"Error: Keywords file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                keyword = line.strip()
                if keyword:  # Skip empty lines
                    keywords.append(keyword)
    except Exception as e:
        print(f"Error: Failed to read keywords file: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not keywords:
        print("Error: No valid keywords found in file", file=sys.stderr)
        sys.exit(1)
    
    return keywords


def sanitize_keyword_for_filename(keyword: str) -> str:
    """
    Sanitize a keyword string for use in a filename.
    
    Args:
        keyword: Keyword string
        
    Returns:
        Sanitized string (lowercase, spaces to dashes, only alphanumeric and dashes)
    """
    # Convert to lowercase
    sanitized = keyword.lower()
    # Replace spaces with dashes
    sanitized = sanitized.replace(" ", "-")
    # Remove all characters except lowercase letters, digits, and dashes
    sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)
    # Remove multiple consecutive dashes
    sanitized = re.sub(r"-+", "-", sanitized)
    # Remove leading/trailing dashes
    sanitized = sanitized.strip("-")
    
    return sanitized


def fetch_paa_single(
    keyword: str,
    language_code: str,
    location_code: int,
    api_login: str,
    api_password: str,
) -> List[str]:
    """
    Fetch PAA questions for a single keyword from DataForSEO (single-level only).
    
    Args:
        keyword: Search keyword string
        language_code: Language code (e.g., "en")
        location_code: DataForSEO location code
        api_login: DataForSEO API login
        api_password: DataForSEO API password
        
    Returns:
        List of PAA question strings (empty list if none found or error)
        
    Raises:
        Exception: On network, HTTP, or DataForSEO API errors
    """
    payload = [
        {
            "keyword": keyword,
            "language_code": language_code,
            "location_code": location_code,
            "device": "desktop",
        }
    ]
    
    try:
        response = requests.post(
            API_URL,
            auth=(api_login, api_password),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,  # 5 minutes timeout for long requests
        )
    except requests.exceptions.RequestException as e:
        # Network error - return empty list, error will be logged by caller
        raise Exception(f"Network error: {str(e)}")
    
    if response.status_code != 200:
        raise Exception(
            f"HTTP error: status {response.status_code}, body: {response.text[:200]}"
        )
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON response: {str(e)}")
    
    # Check top-level status_code
    if data.get("status_code") != 20000:
        status_message = data.get("status_message", "Unknown error")
        raise Exception(
            f"DataForSEO error: status_code={data.get('status_code')}, "
            f"status_message={status_message}"
        )
    
    questions = []
    
    # Parse tasks
    tasks = data.get("tasks", [])
    for task in tasks:
        # Check task status_code
        if task.get("status_code") != 20000:
            status_message = task.get("status_message", "Unknown error")
            raise Exception(
                f"DataForSEO task error: status_code={task.get('status_code')}, "
                f"status_message={status_message}"
            )
        
        # Parse results
        results = task.get("result", [])
        for result in results:
            items = result.get("items", [])
            for item in items:
                if item.get("type") == "people_also_ask":
                    paa_items = item.get("items", [])
                    for paa_item in paa_items:
                        if paa_item.get("type") == "people_also_ask_element":
                            title = paa_item.get("title")
                            if title:
                                questions.append(title)
    
    return questions


# Backward compatibility alias
fetch_paa_for_keyword = fetch_paa_single


def collect_paa_recursive(
    root_keyword: str,
    language_code: str,
    location_code: int,
    api_login: str,
    api_password: str,
    paa_depth: int,
    max_questions: int,
    max_requests: int,
    log_callback=None,
) -> List[str]:
    """
    Collect PAA questions recursively using BFS traversal up to specified depth.
    
    Args:
        root_keyword: The original root keyword string
        language_code: Language code (e.g., "en")
        location_code: DataForSEO location code
        api_login: DataForSEO API login
        api_password: DataForSEO API password
        paa_depth: Maximum depth to recurse (1 = only root keyword)
        max_questions: Maximum number of unique questions to collect per root keyword
        max_requests: Maximum number of API requests per root keyword
        log_callback: Optional callback function(current_keyword, depth, request_num, max_requests, root_keyword, elapsed, questions_found, total_questions)
        
    Returns:
        List of unique PAA question strings (sorted for deterministic output)
    """
    visited_keywords: set = {root_keyword}
    questions: set = set()
    requests_used = 0
    queue: List[Tuple[str, int]] = [(root_keyword, 0)]  # (keyword_string, depth)
    
    while queue:
        current_keyword, depth = queue.pop(0)
        
        # Check max requests limit
        if requests_used >= max_requests:
            if log_callback:
                log_callback(
                    current_keyword, depth, requests_used, max_requests, root_keyword,
                    None, None, len(questions), warning=f"Max requests per keyword reached for '{root_keyword}' (requests_used={requests_used}, max={max_requests})"
                )
            break
        
        # Check if we've reached max questions
        if len(questions) >= max_questions:
            break
        
        # Send request
        request_start = time.time()
        if log_callback:
            log_callback(
                current_keyword, depth, requests_used + 1, max_requests, root_keyword,
                None, None, len(questions), sending=True
            )
        
        try:
            question_titles = fetch_paa_single(
                current_keyword,
                language_code,
                location_code,
                api_login,
                api_password,
            )
            elapsed = time.time() - request_start
            requests_used += 1
            
            # Process questions from this request
            for question_title in question_titles:
                # Normalize: strip whitespace
                normalized = question_title.strip()
                if not normalized:
                    continue
                
                # Add to questions set if not already present
                if normalized not in questions:
                    questions.add(normalized)
                    
                    # Check if we've reached max questions
                    if len(questions) >= max_questions:
                        break
            
            # Log success
            if log_callback:
                log_callback(
                    current_keyword, depth, requests_used, max_requests, root_keyword,
                    elapsed, len(question_titles), len(questions), sending=False
                )
            
            # If we've reached max questions, stop
            if len(questions) >= max_questions:
                break
            
            # Enqueue children if depth allows
            if depth + 1 < paa_depth:
                for question_title in question_titles:
                    normalized = question_title.strip()
                    if normalized and normalized not in visited_keywords:
                        visited_keywords.add(normalized)
                        queue.append((normalized, depth + 1))
        
        except Exception as e:
            elapsed = time.time() - request_start
            requests_used += 1
            error_msg = str(e)
            
            # Log error
            if log_callback:
                log_callback(
                    current_keyword, depth, requests_used, max_requests, root_keyword,
                    elapsed, None, len(questions), error=error_msg
                )
            
            # Continue with next item in queue (don't enqueue children from failed request)
            continue
    
    # Return sorted list for deterministic output
    return sorted(list(questions))


def write_csv(rows: List[Dict[str, str]], output_path: str) -> None:
    """
    Write results to CSV file.
    
    Args:
        rows: List of dicts with "keyword" and "question" keys
        output_path: Output file path
    """
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["keyword", "question"])
        for row in rows:
            writer.writerow([row["keyword"], row["question"]])


def write_json(
    rows: List[Dict[str, str]], 
    all_keywords: List[str],
    output_path: str
) -> None:
    """
    Write results to JSON file.
    
    Args:
        rows: List of dicts with "keyword" and "question" keys
        all_keywords: List of all keywords that were processed (including those with no questions)
        output_path: Output file path
    """
    # Group by keyword
    keyword_to_questions: Dict[str, List[str]] = {}
    for row in rows:
        keyword = row["keyword"]
        question = row["question"]
        if keyword not in keyword_to_questions:
            keyword_to_questions[keyword] = []
        keyword_to_questions[keyword].append(question)
    
    # Convert to list of objects, including keywords with no questions
    output_data = []
    for keyword in all_keywords:
        questions = keyword_to_questions.get(keyword, [])
        output_data.append({"keyword": keyword, "question": questions})
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)


def determine_output_path(
    keyword: Optional[str],
    keywords_file: Optional[str],
    output: Optional[str],
    output_format: str,
    script_dir: str,
) -> str:
    """
    Determine the output file path based on input and parameters.
    
    Args:
        keyword: Single keyword string (if provided)
        keywords_file: Path to keywords file (if provided)
        output: Explicit output path (if provided)
        output_format: "csv" or "json"
        script_dir: Directory containing the script
        
    Returns:
        Output file path
    """
    if output:
        return output
    
    extension = output_format
    
    if keywords_file:
        # Use keywords file name as base
        keywords_path = Path(keywords_file)
        keywords_dir = keywords_path.parent
        keywords_stem = keywords_path.stem
        output_filename = f"{keywords_stem}_questions.{extension}"
        return str(keywords_dir / output_filename)
    elif keyword:
        # Use sanitized keyword as base
        sanitized = sanitize_keyword_for_filename(keyword)
        output_filename = f"{sanitized}_questions.{extension}"
        return str(Path(script_dir) / output_filename)
    else:
        # Fallback (should not happen)
        return f"output.{extension}"


def main() -> None:
    """Main entry point."""
    # Get script directory for default config path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_config_path = os.path.join(script_dir, ".dataforseo.json")
    
    parser = argparse.ArgumentParser(
        description="Fetch People Also Ask (PAA) questions from DataForSEO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s --keyword "best gifts for men"
  %(prog)s --file keywords.txt --json
  %(prog)s -k "test" -f keywords.txt -c GB -l en

Input Requirements:
  Either --keyword or --file (or both) must be provided.

Default Output Filenames:
  - If --output is provided: use the exact path given
  - If --file is used: {{keywords-filename}}_questions.{{csv|json}}
  - If --keyword is used: {{sanitized-keyword}}_questions.{{csv|json}}
  Example: "best gifts for men" -> best-gifts-for-men_questions.csv

Defaults:
  --language: en
  --country: US
  --config: {default_config_path}
  Output format: CSV (use --json for JSON output)
  --depth: 1
  --questions: 20
  --requests: 15
        """,
    )
    
    # Input arguments (mutually exclusive group, but can be combined)
    input_group = parser.add_argument_group("Input (at least one required)")
    input_group.add_argument(
        "-k",
        "--keyword",
        type=str,
        help="Single keyword string",
    )
    input_group.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path to text file with one keyword per line",
    )
    
    # Other parameters
    parser.add_argument(
        "-l",
        "--lang",
        "--language",
        type=str,
        default="en",
        dest="language",
        help='Language code (default: "en")',
    )
    parser.add_argument(
        "-c",
        "--country",
        type=str,
        default="US",
        help='ISO 2-letter country code (default: "US")',
    )
    parser.add_argument(
        "--config",
        type=str,
        default=default_config_path,
        help=f'Path to JSON config file with api_login and api_password (default: "{default_config_path}")',
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Explicit output file path (if omitted, default naming rules apply)",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--csv",
        action="store_true",
        help="Output format: CSV (default)",
    )
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output format: JSON",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Silent mode: do not prompt for overwrite confirmation",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Overwrite existing output file without prompting",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=1,
        dest="paa_depth",
        help="Maximum depth for recursive PAA fetching (1 = only original keyword, 2 = original + PAA questions, etc.) (default: 1)",
    )
    parser.add_argument(
        "-q",
        "--questions",
        type=int,
        default=20,
        dest="max_questions_per_keyword",
        help="Maximum number of unique questions to collect per root keyword (default: 20)",
    )
    parser.add_argument(
        "-r",
        "--requests",
        type=int,
        default=15,
        dest="max_requests_per_keyword",
        help="Maximum number of API requests per root keyword (safety cap) (default: 15)",
    )
    
    args = parser.parse_args()
    
    # Validate depth
    if args.paa_depth < 1:
        parser.error("--depth must be >= 1")
    
    # Validate that at least one input is provided
    if not args.keyword and not args.file:
        parser.error("Either --keyword or --file (or both) must be provided")
    
    # Determine output format (default to csv if neither is specified)
    if args.json:
        output_format = "json"
    else:
        output_format = "csv"  # Default
    
    # Load config
    api_login, api_password = load_config(args.config)
    
    # Get location code
    location_code = dfs_country_to_location_code(args.country)
    
    # Collect keywords
    keywords = []
    if args.keyword:
        keywords.append(args.keyword)
    if args.file:
        keywords.extend(read_keywords_from_file(args.file))
    
    # Determine output path
    output_path = determine_output_path(
        args.keyword if not args.file else None,
        args.file,
        args.output,
        output_format,
        script_dir,
    )
    
    # Check if output file exists
    if os.path.exists(output_path) and not args.overwrite and not args.silent:
        response = input(f"{output_path} already exists. Overwrite? (Y/N): ")
        if response.upper() != "Y":
            print("Aborted.", file=sys.stderr)
            sys.exit(0)
    
    # Collect all results
    all_rows: List[Dict[str, str]] = []
    successfully_processed_keywords: List[str] = []  # For JSON output (includes keywords with no questions)
    total_keywords = len(keywords)
    failed_keywords = 0
    
    # Progress reporting
    use_progress_bar = total_keywords > 1
    progress_bar = None
    if use_progress_bar:
        progress_bar = tqdm(total=total_keywords, desc="Processing keywords", unit="keyword")
    
    for i, root_keyword in enumerate(keywords, 1):
        keyword_num = f"[{i}/{total_keywords}]" if total_keywords > 1 else ""
        
        # Define log callback for recursive collection (closure over i, keyword_num, etc.)
        def log_callback(
            current_keyword, depth, request_num, max_requests, root_keyword_inner,
            elapsed, questions_found, total_questions, sending=False, error=None, warning=None
        ):
            if sending:
                # Before sending request
                if not use_progress_bar:
                    print(
                        f'Sending request (depth={depth}, request {request_num}/{max_requests}) '
                        f'for keyword: "{current_keyword[:60]}" (root: "{root_keyword_inner[:40]}")...'
                    )
                else:
                    progress_bar.set_description(
                        f'{keyword_num} depth={depth}, req={request_num}/{max_requests}: "{current_keyword[:40]}"'
                    )
            elif error:
                # Error occurred
                if not use_progress_bar:
                    print(f"ERROR – {error}")
                else:
                    progress_bar.set_postfix({"status": "ERROR"})
                print(
                    f"{keyword_num} ERROR for '{current_keyword}' (root '{root_keyword_inner}'): {error}",
                    file=sys.stderr
                )
            elif warning:
                # Warning (e.g., max requests reached)
                print(f"{keyword_num} WARNING: {warning}", file=sys.stderr)
            else:
                # Request completed successfully
                if not use_progress_bar:
                    print(
                        f"Done in {elapsed:.1f}s – {questions_found} PAA questions found "
                        f"(depth={depth}, current total={total_questions})"
                    )
                else:
                    progress_bar.set_postfix(
                        {
                            "status": f"{total_questions} questions",
                            "depth": depth,
                            "req": f"{request_num}/{max_requests}"
                        }
                    )
        
        if not use_progress_bar:
            print(f'Processing root keyword: "{root_keyword}"...')
        else:
            progress_bar.set_description(f'{keyword_num} Processing: "{root_keyword[:50]}"')
        
        root_start_time = time.time()
        
        try:
            # Use recursive collection if depth > 1, otherwise use single-level
            if args.paa_depth > 1:
                questions = collect_paa_recursive(
                    root_keyword,
                    args.language,
                    location_code,
                    api_login,
                    api_password,
                    args.paa_depth,
                    args.max_questions_per_keyword,
                    args.max_requests_per_keyword,
                    log_callback=log_callback,
                )
            else:
                # Single-level (backward compatible behavior)
                if not use_progress_bar:
                    print(f'Sending request for keyword: "{root_keyword}"...')
                else:
                    progress_bar.set_description(f'{keyword_num} Processing: "{root_keyword[:50]}"')
                
                request_start = time.time()
                questions = fetch_paa_single(
                    root_keyword,
                    args.language,
                    location_code,
                    api_login,
                    api_password,
                )
                elapsed = time.time() - request_start
                
                if not use_progress_bar:
                    print(f"Done in {elapsed:.1f}s – {len(questions)} PAA questions found")
                else:
                    progress_bar.set_postfix(
                        {"status": f"{len(questions)} questions", "time": f"{elapsed:.1f}s"}
                    )
            
            root_elapsed = time.time() - root_start_time
            
            # Track successfully processed keyword (even if no questions)
            successfully_processed_keywords.append(root_keyword)
            
            if questions:
                for question in questions:
                    all_rows.append({"keyword": root_keyword, "question": question})
                
                if args.paa_depth > 1:
                    # Summary for recursive mode
                    if not use_progress_bar:
                        print(
                            f"Root keyword '{root_keyword}' completed in {root_elapsed:.1f}s – "
                            f"{len(questions)} unique PAA questions collected"
                        )
            else:
                if not use_progress_bar:
                    print(f"Done in {root_elapsed:.1f}s – 0 PAA questions found (no PAA block)")
                else:
                    progress_bar.set_postfix(
                        {"status": "No PAA", "time": f"{root_elapsed:.1f}s"}
                    )
                print(f"No PAA for '{root_keyword}'")
        
        except Exception as e:
            failed_keywords += 1
            root_elapsed = time.time() - root_start_time
            error_msg = str(e)
            
            if not use_progress_bar:
                print(f"ERROR – {error_msg}")
            else:
                progress_bar.set_postfix({"status": "ERROR", "time": f"{root_elapsed:.1f}s"})
            
            print(f"{keyword_num} ERROR for '{root_keyword}': {error_msg}", file=sys.stderr)
        
        if progress_bar:
            progress_bar.update(1)
    
    if progress_bar:
        progress_bar.close()
    
    # Write output
    if output_format == "csv":
        write_csv(all_rows, output_path)
    else:
        write_json(all_rows, successfully_processed_keywords, output_path)
    
    # Final summary
    if not use_progress_bar:
        print(f"Output saved to {output_path}")
    
    # Check if no questions were collected
    if not all_rows:
        if failed_keywords == total_keywords:
            print(
                f"Warning: All {total_keywords} keywords failed. Output file created with available data.",
                file=sys.stderr
            )
        else:
            print("Warning: No questions collected for any keyword.", file=sys.stderr)
    elif failed_keywords > 0:
        if failed_keywords == total_keywords:
            print(
                f"Warning: All {total_keywords} keywords failed. Output file created with available data.",
                file=sys.stderr
            )
        else:
            print(
                f"Warning: {failed_keywords} out of {total_keywords} keywords failed.",
                file=sys.stderr
            )


if __name__ == "__main__":
    main()

