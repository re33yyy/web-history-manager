import sqlite3
import requests
from bs4 import BeautifulSoup
import hashlib
import datetime
from urllib.parse import urljoin
import re

# Database configuration
DB_PATH = 'web_history.db'

def explore_bbc_structure():
    """Explore the BBC News website structure"""
    site_url = 'https://www.bbc.com/news'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Requesting {site_url}...")
    response = requests.get(site_url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"Error: Got status code {response.status_code}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try different selectors
    selectors_to_try = [
        'div.gs-c-promo',
        'article',
        '.article',
        '.story',
        'div.story',
        'div.media-list__item',
        'a.gs-c-promo-heading',
        'h3'
    ]
    
    print("\nTesting different selectors:")
    for selector in selectors_to_try:
        elements = soup.select(selector)
        print(f"{selector}: {len(elements)} elements found")
    
    # Find all links that might be articles
    news_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Look for news article patterns in URLs
        if '/news/' in href and not href.endswith('/news'):
            # Add to our list if it looks like a news article URL
            if not href.startswith(('http://', 'https://')):
                href = urljoin('https://www.bbc.com', href)
            
            # Get the title from the link text
            title = a.get_text(strip=True)
            if title and len(title) > 10:  # Reasonable length for a headline
                news_links.append({
                    'url': href,
                    'title': title
                })
    
    # Remove duplicates
    unique_links = []
    seen_urls = set()
    for link in news_links:
        if link['url'] not in seen_urls:
            seen_urls.add(link['url'])
            unique_links.append(link)
    
    print(f"\nFound {len(unique_links)} unique news article links")
    
    # Print the first 5 for inspection
    for i, link in enumerate(unique_links[:5]):
        print(f"\nArticle {i+1}:")
        print(f"Title: {link['title']}")
        print(f"URL: {link['url']}")
    
    return unique_links

def save_bbc_articles_directly():
    """Direct script to save BBC News articles to database using adaptive approach"""
    # Site details
    site_id = 'www.bbc.com'
    site_name = 'BBC News'
    site_url = 'https://www.bbc.com/news'
    
    # First explore the structure
    article_links = explore_bbc_structure()
    
    if not article_links:
        print("No articles found, cannot proceed")
        return
    
    with sqlite3.connect(DB_PATH) as conn:
        # Check if site exists
        cursor = conn.execute("SELECT id FROM crawled_sites WHERE id = ?", (site_id,))
        if not cursor.fetchone():
            # Insert site if it doesn't exist
            conn.execute(
                """
                INSERT INTO crawled_sites (id, name, url, last_crawled, config)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    site_id,
                    site_name,
                    site_url,
                    datetime.datetime.now().isoformat(),
                    '{"name": "BBC News", "url": "https://www.bbc.com/news", "update_frequency": 3600, "max_items": 15}'
                )
            )
            print(f"Added site: {site_name}")
    
    # Process and save articles
    with sqlite3.connect(DB_PATH) as conn:
        for i, article in enumerate(article_links[:15]):  # Limit to 15 articles
            try:
                article_url = article['url']
                article_title = article['title']
                
                # Create a unique ID for the article
                article_id = f"{site_id}_{hashlib.md5(article_url.encode()).hexdigest()}"
                
                # Check if article already exists
                cursor = conn.execute(
                    "SELECT id FROM crawled_content WHERE id = ?",
                    (article_id,)
                )
                
                if cursor.fetchone() is None:
                    # Insert new article
                    conn.execute(
                        """
                        INSERT INTO crawled_content 
                        (id, site_id, title, url, summary, published_date, crawled_date, is_read)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            article_id,
                            site_id,
                            article_title,
                            article_url,
                            "",  # No summary
                            "",  # No published date
                            datetime.datetime.now().isoformat(),
                            False
                        )
                    )
                    print(f"Added article: {article_title}")
                else:
                    print(f"Article already exists: {article_title}")
            except Exception as e:
                print(f"Error processing article: {e}")
    
    # Update last_crawled time
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE crawled_sites SET last_crawled = ? WHERE id = ?", 
            (datetime.datetime.now().isoformat(), site_id)
        )
    
    print("Done!")

if __name__ == "__main__":
    save_bbc_articles_directly()