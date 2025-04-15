import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import hashlib
import datetime
from urllib.parse import urljoin

# Database configuration
DB_PATH = 'web_history.db'

def save_verge_articles_directly():
    """Direct script to save The Verge articles to database"""
    # Make sure the site exists in the database
    site_id = 'www.theverge.com'
    site_name = 'The Verge'
    site_url = 'https://www.theverge.com/'
    
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
                    '{"name": "The Verge", "url": "https://www.theverge.com/", "update_frequency": 3600, "max_items": 15}'
                )
            )
            print(f"Added site: {site_name}")
    
    # Fetch articles from The Verge
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Requesting {site_url}...")
    response = requests.get(site_url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"Error: Got status code {response.status_code}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all article links
    all_links = soup.find_all('a', href=True)
    article_links = []
    
    for a in all_links:
        href = a['href']
        if '/news/' in href or re.search(r'/\d{4}/\d{1,2}/\d{1,2}/', href):
            if '#comments' not in href and href not in [link.get('href', '') for link in article_links]:
                if not href.startswith('http'):
                    href = urljoin(site_url, href)
                title = a.get_text(strip=True)
                if title and len(title) > 5 and 'Comments' not in title:
                    article_links.append({
                        'title': title,
                        'href': href
                    })
    
    print(f"Found {len(article_links)} article links")
    
    # Process and save articles
    with sqlite3.connect(DB_PATH) as conn:
        for article in article_links[:15]:  # Limit to 15 articles
            try:
                article_url = article['href']
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
    save_verge_articles_directly()