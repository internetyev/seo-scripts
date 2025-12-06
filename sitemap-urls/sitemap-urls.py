import argparse
import csv
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tqdm import tqdm


def normalize_domain(d):
    d = str(d).strip()
    if d.startswith('http://') or d.startswith('https://'):
        return d.rstrip('/')
    return 'https://' + d.rstrip('/')


def read_domains_from_csv(path):
    try:
        df = pd.read_csv(path)
        if 'domain' in df.columns:
            return df['domain'].dropna().astype(str).tolist()
        # fallback to first column
        return df.iloc[:, 0].dropna().astype(str).tolist()
    except Exception:
        # fallback: try reading plain lines
        with open(path, 'r') as f:
            return [l.strip() for l in f if l.strip()]


def extract_sitemaps(domain_url):
    domain_url = normalize_domain(domain_url)
    robots_url = domain_url + '/robots.txt'
    try:
        r = requests.get(robots_url, timeout=10)
    except requests.RequestException:
        return [domain_url + '/sitemap.xml']

    if r.status_code != 200:
        return [domain_url + '/sitemap.xml']

    sitemap_urls = []
    for line in r.text.splitlines():
        line = line.strip()
        if line.lower().startswith('sitemap:'):
            parts = line.split(':', 1)
            if len(parts) > 1:
                sitemap_urls.append(parts[1].strip())

    if not sitemap_urls:
        sitemap_urls = [domain_url + '/sitemap.xml']

    return sitemap_urls


def extract_sitemap_urls(sitemap_url, pbar=None):
    try:
        r = requests.get(sitemap_url, timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(r.content, 'xml')
    urls = []
    for loc in soup.find_all('loc'):
        text = loc.get_text(strip=True)
        if text:
            urls.append(text)

    # If sitemap contains sitemap indexes, follow them
    # detect if urls look like sitemap files (ending with .xml)
    if urls and all(u.endswith('.xml') for u in urls):
        expanded = []
        for u in urls:
            child = urljoin(sitemap_url, u) if not u.startswith('http') else u
            # Process nested sitemaps without progress bar, then update main bar
            child_urls = extract_sitemap_urls(child, pbar=None)
            if pbar:
                # Update progress bar with count of URLs found in nested sitemap
                pbar.update(len(child_urls))
            expanded.extend(child_urls)
        return expanded

    # Update progress bar for final URLs
    collected = []
    for u in urls:
        full_url = urljoin(sitemap_url, u) if not u.startswith('http') else u
        collected.append((full_url, sitemap_url))
        if pbar:
            pbar.update(1)
    return collected


def main():
    parser = argparse.ArgumentParser(description='Extract sitemap URLs for domains')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--domain', help='Single domain to process (e.g. example.com)')
    group.add_argument('--domains-csv', help='CSV file containing domains (column `domain` or first column)')
    parser.add_argument('--output', help='Output CSV file path', default='sitemap-urls.csv')
    parser.add_argument('-v', '--verbose', action='store_true', help='Include domain and sitemap columns in output')

    args = parser.parse_args()

    if args.domain:
        domains = [args.domain]
    else:
        domains = read_domains_from_csv(args.domains_csv)

    rows = []
    for d in domains:
        print(f"\nFetching sitemap URLs for: {d}")
        norm = normalize_domain(d)
        sitemaps = extract_sitemaps(norm)
        print(f"Found {len(sitemaps)} sitemap(s)")
        
        # Process each sitemap with progress bar
        with tqdm(total=len(sitemaps), desc="Processing sitemaps", unit="sitemap") as sitemap_pbar:
            for s in sitemaps:
                # make sitemap absolute if relative
                if not s.startswith('http'):
                    s = urljoin(norm + '/', s.lstrip('/'))
                
                # Extract URLs with progress bar
                with tqdm(desc=f"Extracting URLs from {s.split('/')[-1]}", unit="URL", leave=False) as url_pbar:
                    urls = extract_sitemap_urls(s, pbar=url_pbar)
                    for u, source_sitemap in urls:
                        if args.verbose:
                            rows.append({'domain': d, 'sitemap': source_sitemap, 'url': u})
                        else:
                            rows.append({'url': u})
                
                sitemap_pbar.update(1)

    # write CSV
    out_path = args.output
    with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['domain', 'sitemap', 'url'] if args.verbose else ['url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Saved {len(rows)} rows to {out_path}")


if __name__ == '__main__':
    main()

