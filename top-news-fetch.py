import csv
from datetime import datetime
import os
import json

# Assuming RestClient is correctly implemented elsewhere
from client import RestClient

def fetch_and_save_data(keyword, location_code, country_code, language_code, device):
    client = RestClient("your@email.com", "***DATAFORSEO-API***")
    
    post_data = [{
        'language_code': language_code,
        'location_code': location_code,  # Specify if needed. either location_name or location_code
        'device': device,
        'keyword': keyword
    }]

    response = client.post("/v3/serp/google/organic/live/advanced", post_data)

    # Save JSON for troubleshooting
    filename = 'dataforseo_response.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(response, f, ensure_ascii=False, indent=4)

    if response["status_code"] == 20000:
        results = []
        for task in response.get('tasks', []):
            if task is not None:
                for result_item in task.get('result', []):
                    if 'items' in result_item:
                        for item in result_item['items']:
                            if item['type'] == 'top_stories':
                                rank_group = 0
                                for top_story in item['items']:
                                    timestamp_of_url = datetime.strptime(top_story.get('timestamp'), '%Y-%m-%d %H:%M:%S +00:00').strftime('%Y-%m-%d %H:%M')
                                    fetched_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                                    rank_group += 1
                                    results.append([
                                        rank_group,
                                        top_story.get('url', ''),
                                        top_story.get('title', ''),
                                        top_story.get('source', ''),
                                        top_story.get('date', ''),
                                        timestamp_of_url,
                                        fetched_timestamp
                                    ])

        filename = f"top_stories_results_{keyword.replace(' ', '-').replace(':', '-')}_{country_code}_{language_code}_{device}.csv"
        mode = 'a' if os.path.exists(filename) else 'w'
        with open(filename, mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if mode == 'w':
                writer.writerow(['Position', 'URL', 'Title', 'Source', 'Date', 'URL Timestamp', 'Fetched Timestamp'])
            writer.writerows(results)
    else:
        print(f"Error for keyword '{keyword}': {response['status_code']} {response.get('status_message', 'No message')}")

def read_keywords_from_csv(filename):
    """Read sets of parameters from a CSV file."""
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield row

def main():
    csv_filename = "news-keywords-tracking.csv"
    for params in read_keywords_from_csv(csv_filename):
        fetch_and_save_data(
            params['keyword'],
            params['location_code'],
            params['country_code'],
            params['language_code'],
            params['device']
        )

if __name__ == "__main__":
    main()
