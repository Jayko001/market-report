from googleapiclient.discovery import build
from credentials import ggl_api_key, ggl_cse_id
import requests
from bs4 import BeautifulSoup

# Google Custom Search API
def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    return res['items']


# OpenAI API
search_results = google_search("Apple About", ggl_api_key, ggl_cse_id, num=3)
for result in search_results:
    print(result['title'], result['link'])


def scrape_url_content(url):
    try:
        response = requests.get(url)

        # Check if successful
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Scrape the article body
            paragraphs = soup.find_all('p')
            text_content = ' '.join([p.get_text() for p in paragraphs])
            return text_content
        else:
            return "Failed to retrieve content"
    except Exception as e:
        return f"An error occurred: {e}"

url = 'https://www.apple.com/business/'
content = scrape_url_content(url)
print(content[:500])  # first 500 characters to check