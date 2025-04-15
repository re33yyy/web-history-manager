# Add this to your web_crawler.py file to fix The Verge article saving

def debug_save_verge_articles(self):
    """Directly save articles from The Verge for debugging"""
    site_id = 'www.theverge.com'  # This should match the ID in your database
    
    # Fetch the site
    url = "https://www.theverge.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        print(f"Error fetching The Verge: {response.status_code}")
        return
    
    # Parse and find articles
    soup = BeautifulSoup(response.text, 'html.parser')
    article_links = []
    
    for a in soup.find_all('a', href=True):
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
    
    # Create article objects
    articles_to_save = []
    for link in article_links[:15]:  # Limit to 15 articles
        article_id = f"{site_id}_{hashlib.md5(link['href'].encode()).hexdigest()}"
        
        articles_to_save.append({
            "id": article_id,
            "site_id": site_id,
            "title": link['title'],
            "url": link['href'],
            "summary": "",  # No summary available
            "published_date": "",  # No date available
            "crawled_date": datetime.datetime.now().isoformat()
        })
    
    # Save articles directly to database
    with sqlite3.connect(self.db_path) as conn:
        for article in articles_to_save:
            # Check if article already exists
            cursor = conn.execute(
                "SELECT id FROM crawled_content WHERE id = ?",
                (article["id"],)
            )
            
            if cursor.fetchone() is None:
                # Insert new article
                conn.execute(
                    """
                    INSERT INTO crawled_content 
                    (id, site_id, title, url, summary, published_date, crawled_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article["id"],
                        article["site_id"],
                        article["title"],
                        article["url"],
                        article["summary"],
                        article["published_date"],
                        article["crawled_date"]
                    )
                )
                print(f"Added new article: {article['title']}")
    
    print(f"Saved {len(articles_to_save)} articles from The Verge")