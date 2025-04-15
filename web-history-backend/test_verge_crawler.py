import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

# This is a standalone script you can run to test The Verge crawling
def test_verge_crawler():
    """Test scraping from The Verge with updated selectors"""
    
    # Request the site with a desktop user agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    url = "https://www.theverge.com/"
    print(f"Requesting {url}...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
        
    # Parse the HTML
    print("Parsing HTML...")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # We'll look for links that match typical article patterns
    article_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Look for URLs that match article patterns (/news/ or date-based URLs)
        if '/news/' in href or re.search(r'/\d{4}/\d{1,2}/\d{1,2}/', href):
            # Skip comment links and duplicates
            if '#comments' not in href and href not in [link['href'] for link in article_links]:
                # Make sure we have a complete URL
                if not href.startswith('http'):
                    href = urljoin(url, href)
                
                # Find title - usually the link text
                title = a.get_text(strip=True)
                
                # Only include links that have reasonable titles (not empty or just "Comments")
                if title and len(title) > 5 and title != "Comments":
                    article_links.append({
                        'title': title,
                        'href': href
                    })
    
    print(f"Found {len(article_links)} article links")
    
    # Extract and process articles
    results = []
    for i, link in enumerate(article_links[:15]):  # Process first 15 articles
        try:
            result = {
                "title": link['title'],
                "url": link['href'],
                "summary": "",  # We'll leave summary blank for now
                "published_date": ""  # No date information available from link
            }
            
            results.append(result)
            print(f"\nArticle {i+1}:")
            print(f"Title: {link['title']}")
            print(f"URL: {link['href']}")
            
        except Exception as e:
            print(f"Error processing article: {e}")
    
    # Save results to a file for inspection
    with open('verge_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
        print("\nResults saved to verge_test_results.json")

if __name__ == "__main__":
    test_verge_crawler()