from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup
from typing import List, Dict

def fetch_amazon_page_selenium(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " 
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
    # Optional: add proxy if needed
    # chrome_options.add_argument("--proxy-server=http://your_proxy:port")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    # Wait for dynamic content to load
    time.sleep(5)
    page_html = driver.page_source
    driver.quit()
    return page_html

def parse_product_listings(html_content: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html_content, "html.parser")
    product_containers = soup.find_all('div', attrs={'data-asin': True, 'data-component-type': 's-search-result'})
    products = []
    
    for container in product_containers:
        product = {}
        
        # Extract title
        title_element = container.find('h2', class_='a-size-medium')
        product['title'] = title_element.text.strip() if title_element else "Title not found"
        
        # Extract price
        price_element = container.find('span', class_='a-price-whole')
        price_fraction_element = container.find('span', class_='a-price-fraction')
        if price_element and price_fraction_element:
            product['price'] = f"${price_element.text.strip()}{price_fraction_element.text.strip()}"
        elif price_element:
            product['price'] = f"${price_element.text.strip()}"
        else:
            product['price'] = "Price not found"
            
        # Extract product link
        link_element = container.find('a', class_='a-link-normal s-no-outline')
        if link_element:
            product['link'] = f"https://www.amazon.com{link_element.get('href')}"
        else:
            product['link'] = "Link not found"
            
        products.append(product)
    
    return products

if __name__ == '__main__':
    search_query = "gaming laptop"
    encoded_query = search_query.replace(" ", "+")
    search_url = f"https://www.amazon.com/s?k={encoded_query}"
    
    html_content = fetch_amazon_page_selenium(search_url)
    if html_content:
        products = parse_product_listings(html_content)
        for product in products:
            print(f"Title: {product['title']}")
            print(f"Price: {product['price']}")
            print(f"Link: {product['link']}")
            print("-" * 50)
    else:
        print("Failed to fetch page with Selenium.")
