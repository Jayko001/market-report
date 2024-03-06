from googleapiclient.discovery import build
from credentials import ggl_api_key, ggl_cse_id, DRIVER_PATH, OPENAI_API_KEY
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from openai import OpenAI
import os
import time

client = OpenAI(api_key=OPENAI_API_KEY)

def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    return res['items']
  


def scrape_dynamic_content(url, max_length=20000):
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    driver.implicitly_wait(10)
    text_content = driver.find_element(By.XPATH, "/html/body").text
    driver.quit()

    # Trim the content if it exceeds max_length
    if len(text_content) > max_length:
        return text_content[:max_length]  # Return the first max_length characters
    else:
        return text_content

def get_company_info(company_name, competitors):
    company_info = {}

    for competitor in competitors:
        about_intro = f"Summarize the about section for {competitor} based on the following content and find why it's a competitor for {company_name}."
        customers_intro = "Summarize the target customer(s) for the company based on the following content:"
        pricing_intro = "Summarize the pricing information for the company based on the following content:"

        # About
        about_search_results = google_search(f"{competitor} About", ggl_api_key, ggl_cse_id, num=3)
        about_content = ' '.join([scrape_dynamic_content(result['link'], max_length=20000) for result in about_search_results])
        print(about_content)
        about_summary = interpret_with_gpt(client, about_content, about_intro)

        # Customers
        customers_summary = interpret_with_gpt(client, about_content, customers_intro)

        # Pricing
        pricing_search_results = google_search(f"{competitor} pricing", ggl_api_key, ggl_cse_id, num=1)
        pricing_content = ' '.join([scrape_dynamic_content(result['link'], max_length=20000) for result in pricing_search_results])
        print(pricing_content)
        pricing_summary = interpret_with_gpt(client, pricing_content, pricing_intro)

        # Store the results in the dictionary
        company_info[competitor] = {
            'about': about_summary,
            'customers': customers_summary,
            'pricing': pricing_summary
        }

    return company_info

def interpret_with_gpt(client, text, prompt_intro, retries=3):
  print("\n")
  print(client)
  print("\n")
  print(text)
  print("\n")
  print(prompt_intro)
  print("\n")

  full_prompt = f"{prompt_intro}\n\n{text}"
  for attempt in range(retries):
    try:
      response = client.chat.completions.create(
          model="gpt-4",
          messages=[
              {
                  "role": "user",
                  "content": full_prompt
              }
          ]
      )
      return response.choices[0].message.content.strip()
    except Exception as e:
      if 'insufficient_quota' in str(e) and attempt < retries - 1:
        print(f"Quota exceeded, retrying in {2 ** attempt} seconds...")
        time.sleep(2 ** attempt)
      else:
        print(f"An error occurred: {e}")
        return ""

