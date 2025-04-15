import requests
from bs4 import BeautifulSoup
import re

# Request the site
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

url = "https://www.theverge.com/"
response = requests.get(url, headers=headers)
print(f"Status code: {response.status_code}")

# Save the HTML to a file for inspection
with open("verge_html.txt", "w", encoding="utf-8") as f:
    f.write(response.text[:100000])  # Save first 100K characters to avoid massive files
print("Saved first part of HTML to verge_html.txt")

# Parse HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Look for elements that might contain article titles
print("\nSearching for possible article elements...")

# Look for h1, h2, h3 elements that might be article titles
headers = soup.find_all(['h1', 'h2', 'h3'])
print(f"Found {len(headers)} heading elements")

# Print the first 5 with their parent information
for i, header in enumerate(headers[:5]):
    print(f"\nHeading {i+1}:")
    print(f"Text: {header.get_text(strip=True)}")
    print(f"HTML: {str(header)[:200]}...")
    
    # Get the parent elements to help identify article containers
    parent = header.parent
    if parent:
        parent_classes = parent.get('class', [])
        print(f"Parent has classes: {parent_classes}")
        
        # Look one level higher
        grandparent = parent.parent
        if grandparent:
            gp_classes = grandparent.get('class', [])
            print(f"Grandparent has classes: {gp_classes}")

# Look for <a> elements with hrefs that might be article links
article_links = []
for a in soup.find_all('a', href=True):
    href = a['href']
    # Look for URLs that match article patterns
    if re.search(r'/\d{4}/\d{1,2}/\d{1,2}/', href) or '/news/' in href:
        article_links.append(a)

print(f"\nFound {len(article_links)} potential article links")
for i, link in enumerate(article_links[:5]):
    print(f"\nArticle link {i+1}:")
    print(f"URL: {link['href']}")
    print(f"Text: {link.get_text(strip=True)}")
    link_classes = link.get('class', [])
    print(f"Link classes: {link_classes}")