from google_serp_api import ScrapeitCloudClient
from collections import Counter
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from htmldate import find_date
from time import sleep
import json

# Setup
service = Service(
    './chromedriver')
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=service, options=options)


def find_article_links(driver, url):
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    keywords = ['artykul/', '/2024/', 'article/']
    article_links = []

    for link in soup.find_all('a', href=True):
        href = link['href']
        if any(keyword in href for keyword in keywords):
            if href.startswith('/'):
                href = url.rstrip('/') + href
            if url.rstrip('/') not in href:
                href = url.rstrip('/') + '/' + href.lstrip('/')
            article_links.append(href)

    if not article_links:
        for article in soup.find_all('article'):
            link = article.find('a', href=True)
            if link and link['href']:
                href = link['href']
                if href.startswith('/'):
                    href = url.rstrip('/') + href
                article_links.append(href)

    return article_links


sleep(5)


def get_article_data(driver, link):
    data = {'site': str(link), 'title': '', 'category': '',
            'date': '', 'content': []}
    if link:
        driver.get(str(link))
        content = driver.page_source
        soup = BeautifulSoup(content, 'html.parser')
        title = soup.find('h1')
        if title:
            data['title'] = title.text
        else:
            data['title'] = 'No title found'
        for href in soup.find_all('a', href=True):
            if any(keyword in href['href'] for keyword in ['kategorie/', 'kategoria/', 'temat/']):
                category = href.text
                if category:
                    data['category'] = category
        if not data['category']:
            for article in soup.findAll('article'):
                for href in article.find_all('a', href=True):
                    if any(keyword in href['href'] for keyword in ['tag/']):
                        category = href.text
                        if category:
                            data['category'] = category

        data['date'] = find_date(link)
        for article in soup.find_all('article'):
            for tag in article.find_all(['h2', 'h3', 'p']):
                for inner_tag in tag.find_all():
                    if inner_tag.name != 'a':
                        inner_tag.attrs = {}
                tag.attrs = {}
                data['content'].append(str(tag))
            break
        for div in soup.find_all('div'):
            if any('block' in i or 'article' in i for i in div.get('class', [])):
                for tag in div.find_all(['h2', 'h3', 'p']):
                    for inner_tag in tag.find_all():
                        if inner_tag.name != 'a':
                            inner_tag.attrs = {}
                    tag.attrs = {}
                    data['content'].append(str(tag))

    return data


# Tests
# Please enter your testing sites!!!
sites = []
articles = {'art1': {}, 'art2': {}}
output = {}
for site in sites:
    driver = webdriver.Chrome()
    driver.get(site)
    links = find_article_links(driver, site)
    sec_link = 1
    if links:
        while links[0] == links[sec_link]:
            sec_link += 1
        articles = {'art1': get_article_data(driver, links[0]), 'art2': get_article_data(
            driver, links[sec_link]) if len(links) > 1 else {}}
        output[site] = articles
        driver.quit()
        sec_link = 1
    else:
        print(f"No articles found for site: {site}")
with open('response.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

# Project
# Get top ten google results
driver.quit()
service = Service(
    './chromedriver')
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=service, options=options)

client = ScrapeitCloudClient(api_key='INSERT_KEY')
response = client.scrape(
    params={
        "q": "najtrudniejsze gry indie",
        'location': "Poland",
        'deviceType': "desktop",
        'gl': "pl",
        'hl': "pl",
        'num': 10,
    }
)

data = json.loads(response.text)

#Get article information from these websites

with open('banned_domains.txt') as f:
    banned = f.read().splitlines()

# Scrape and save data to .json file
def analyze(api_output):
    articles = {}
    articles_counter = 0
    articles_counter_valid = 0
    total_words = 0
    word_counter = Counter()
    word_counter_site = Counter()
    for site in api_output['organicResults']:
        link = site['link']
        data = get_article_data(driver, link)
        if int(len(' '.join(data['content']))) < 1500 or not data['content']:
            articles_counter += 1
            continue
        if any(ban in link for ban in banned):
            articles_counter += 1
            continue
        articles_counter += 1
        articles_counter_valid += 1
        articles[link] = data
        content = ' '.join(data['content'])
        words = re.findall(r'\w+', content.lower())
        words = [word for word in words if word not in [
            'p', 'span', 'strong', 'h2', 'h3', 'toc', 'em', 'rem']]
        total_words += len(words)
        word_counter.update(words)
        word_counter_site.update(words)
        articles[link]['5 most common words'] = word_counter_site.most_common(
            5)
        word_counter_site = Counter()
        banned.append(urlparse(link).netloc)

        if len(articles) == 3:
            break
    articles['analyzed articles'] = articles_counter
    articles['word count'] = total_words
    articles['average word count'] = total_words/articles_counter_valid
    articles['5 most common words'] = word_counter.most_common(5)
    with open('response_with_statistics.json', 'w') as json_file:
        json.dump(articles, json_file, ensure_ascii=False, indent=4)
    open('banned_domains.txt', 'w').close()
    with open('banned_domains.txt', 'w') as f:
        for line in banned:
            f.write(f"{line}\n")


analyze(data)
