import sqlite3
import requests
from bs4 import BeautifulSoup
import hashlib
import datetime
from urllib.parse import urljoin

# Database configuration
DB_PATH = 'web_history.db'

def save_hackernews_articles_directly():
    """Direct script to save Hacker News articles to database"""
    # Site details
    site_id = 'news.ycombinator.com'
    site_name = 'Hacker News'
    site_url = 'https://news.ycombinator.com/'
    
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
                    '{"name": "Hacker News", "url": "https://news.ycombinator.com/", "update_frequency": 1800, "max_items": 20}'
                )
            )
            print(f"Added site: {site_name}")
    
    # Fetch articles from Hacker News
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Requesting {site_url}...")
    response = requests.get(site_url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"Error: Got status code {response.status_code}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all article rows
    article_rows = soup.select('tr.athing')
    print(f"Found {len(article_rows)} article rows")
    
    # Process and save articles
    with sqlite3.connect(DB_PATH) as conn:
        for row in article_rows[:20]:  # Limit to 20 articles
            try:
                # Get article ID from row
                story_id = row.get('id')
                
                # Find title and link
                title_span = row.select_one('span.titleline')
                if not title_span:
                    continue
                    
                title_link = title_span.select_one('a')
                if not title_link:
                    continue
                
                article_title = title_link.get_text(strip=True)
                article_url = title_link.get('href')
                
                # Make URL absolute if needed
                if not article_url.startswith(('http://', 'https://')):
                    article_url = urljoin(site_url, article_url)
                
                # Create a unique ID for the article
                article_id = f"{site_id}_{story_id}"
                
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
    save_hackernews_articles_directly()