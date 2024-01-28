import os
from googleapiclient.discovery import build
from credentials import ggl_api_key, ggl_cse_id, DRIVER_PATH, OPENAI_API_KEY
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from openai import OpenAI


client = OpenAI(api_key= OPENAI_API_KEY)

def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    return res['items']


def scrape_dynamic_content(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    driver.implicitly_wait(10)
    text_content = driver.find_element(By.XPATH, "/html/body").text
    driver.quit()
    return text_content


def get_company_info(company_name):

    about_intro = "Summarize the about section for the company based on the following content:"
    customers_intro = "Summarize the target customer(s) for the company based on the following content:"
    pricing_intro = "Summarize the pricing information for the company based on the following content:"

    # About
    about_search_results = google_search(f"{company_name} About", ggl_api_key, ggl_cse_id, num=3)
    about_content = ' '.join([scrape_dynamic_content(result['link']) for result in about_search_results])
    #about_summary = interpret_with_gpt4(about_content)
    about_summary = interpret_with_gpt4(client, about_content, about_intro)

    # Customers
    # customer_search_results = google_search(f"{company_name} customers", ggl_api_key, ggl_cse_id, num=3)
    # customer_content = ' '.join([scrape_dynamic_content(result['link']) for result in customer_search_results])
    #customers_summary = interpret_with_gpt4(customer_content)
    customers_summary = interpret_with_gpt4(client, about_content, customers_intro)

    # Pricing
    pricing_search_results = google_search(f"{company_name} pricing", ggl_api_key, ggl_cse_id, num=1)
    pricing_content = ' '.join([scrape_dynamic_content(result['link']) for result in pricing_search_results])
    #pricing_summary = interpret_with_gpt4(pricing_content)
    pricing_summary = interpret_with_gpt4(client, pricing_content, pricing_intro)

    return {
        'about': about_summary,
        'customers': customers_summary,
        'pricing': pricing_summary
    }

def interpret_with_gpt4 (client, text, prompt_intro):
    full_prompt = f"{prompt_intro}\n\n{text}"

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
        print(f"An error occurred: {e}")
        return ""


company_name = "Perceive Now"
company_info = get_company_info(company_name)
print(company_info)
