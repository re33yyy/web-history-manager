import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

# Helper function to print database state
def check_database():
    with sqlite3.connect('web_history.db') as conn:
        conn.row_factory = sqlite3.Row
        # Check if site exists
        site_result = conn.execute("SELECT * FROM crawled_sites WHERE name = 'The Verge'").fetchone()
        if site_result:
            print(f"Site found in database: {dict(site_result)}")
            site_id = site_result['id']
            
            # Check for articles
            articles = conn.execute("SELECT * FROM crawled_content WHERE site_id = ?", (site_id,)).fetchall()
            print(f"Found {len(articles)} articles for The Verge")
            
            if articles:
                print("\nFirst article details:")
                print(dict(articles[0]))
            else:
                print("No articles found for The Verge in database")
        else:
            print("The Verge site not found in database")

# Direct crawler test function
def test_verge_direct():
    url = "https://www.theverge.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Requesting {url}...")
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"Error: Got status code {response.status_code}")
        return
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all <a> elements
    all_links = soup.find_all('a', href=True)
    print(f"Found {len(all_links)} total links")
    
    # Look for article links
    article_links = []
    for a in all_links:
        href = a['href']
        if '/news/' in href or re.search(r'/\d{4}/\d{1,2}/\d{1,2}/', href):
            if '#comments' not in href and href not in [link.get('href', '') for link in article_links]:
                if not href.startswith('http'):
                    href = urljoin(url, href)
                title = a.get_text(strip=True)
                if title and len(title) > 5 and 'Comments' not in title:
                    article_links.append({
                        'title': title,
                        'href': href
                    })
    
    print(f"Found {len(article_links)} article links")
    for i, link in enumerate(article_links[:5]):
        print(f"\nArticle {i+1}:")
        print(f"Title: {link['title']}")
        print(f"URL: {link['href']}")

print("Checking database state:")
check_database()
print("\nTesting direct crawler:")
test_verge_direct()