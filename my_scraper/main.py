from googleapiclient.discovery import build
from credentials import ggl_api_key, ggl_cse_id, DRIVER_PATH
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    return res['items']


search_results = google_search("Apple About", ggl_api_key, ggl_cse_id, num=3)
for result in search_results:
    print(result['title'], result['link'])


def scrape_dynamic_content(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    driver.implicitly_wait(10)
    text_content = driver.find_element(By.XPATH, "/html/body").text
    return text_content


url = 'https://www.youtube.com/'
content = scrape_dynamic_content(url)
print(content)
