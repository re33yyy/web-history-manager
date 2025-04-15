import sqlite3
import requests
from bs4 import BeautifulSoup
import json
import re
import hashlib
import datetime
import time
import logging
from urllib.parse import urlparse, urljoin
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='crawler.log'
)
logger = logging.getLogger('web_crawler')

# Database configuration
DB_PATH = 'web_history.db'

    # Site configurations
SITE_CONFIGS = [
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/",
        "crawler_type": "verge",
        "update_frequency": 3600,
        "max_items": 15
    },
    {
        "name": "Hacker News",
        "url": "https://news.ycombinator.com/",
        "crawler_type": "hacker_news",
        "update_frequency": 1800,
        "max_items": 20
    },
    {
        "name": "BBC News",
        "url": "https://www.bbc.com/news",
        "crawler_type": "bbc",
        "update_frequency": 3600,
        "max_items": 15
    },
    # Add more sites as needed
    {
        "name": "100 Percent Fedup",
        "url": "https://100percentfedup.com/",
        "crawler_type": "auto",
        "update_frequency": 1800,
        "max_items": 20
    },
    {
        "name": "Goodlike Productions",
        "url": "https://www.godlikeproductions.com/",
        "crawler_type": "auto",
        "update_frequency": 1800,
        "max_items": 20
    }
]

class UnifiedCrawler:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.logger = logger
        self.init_db()
        
        # Register crawler strategies
        self.crawler_strategies = {
            'standard_article': self.crawl_standard_article_site,
            'news_site': self.crawl_news_site,
            'hacker_news': self.crawl_hacker_news,
            'verge': self.crawl_verge,
            'bbc': self.crawl_bbc_news,
            '100_percent_fedup': self.crawl_news_site
        }
    
    def init_db(self):
        """Initialize the database with tables for crawled content"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS crawled_sites (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                last_crawled TIMESTAMP,
                config TEXT
            )
            """)
            
            conn.execute("""
            CREATE TABLE IF NOT EXISTS crawled_content (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                summary TEXT,
                published_date TEXT,
                crawled_date TIMESTAMP,
                is_read BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (site_id) REFERENCES crawled_sites(id) ON DELETE CASCADE
            )
            """)
            
            # Add index for faster queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_site ON crawled_content(site_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_read ON crawled_content(is_read)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_date ON crawled_content(crawled_date)")
    
    def register_site(self, site_config):
        """Register or update a site in the database"""
        try:
            site_id = site_config.get('id')
            if not site_id:
                # Generate ID from domain if not provided
                site_id = urlparse(site_config['url']).netloc
                site_config['id'] = site_id
            
            with sqlite3.connect(self.db_path) as conn:
                # Check if site already exists
                cursor = conn.execute("SELECT id FROM crawled_sites WHERE id = ?", (site_id,))
                if cursor.fetchone():
                    # Update existing site
                    conn.execute(
                        """
                        UPDATE crawled_sites
                        SET name = ?, url = ?, config = ?
                        WHERE id = ?
                        """,
                        (
                            site_config["name"],
                            site_config["url"],
                            json.dumps(site_config),
                            site_id
                        )
                    )
                    self.logger.info(f"Updated site configuration for {site_config['name']}")
                else:
                    # Insert new site
                    conn.execute(
                        """
                        INSERT INTO crawled_sites (id, name, url, config, last_crawled)
                        VALUES (?, ?, ?, ?, NULL)
                        """,
                        (
                            site_id,
                            site_config["name"],
                            site_config["url"],
                            json.dumps(site_config)
                        )
                    )
                    self.logger.info(f"Registered new site: {site_config['name']}")
            return True
        except Exception as e:
            self.logger.error(f"Error registering site {site_config.get('name', 'unknown')}: {e}")
            traceback.print_exc()
            return False
    
    def crawl_all_sites(self):
        """Crawl all registered sites that need updating"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, name, url, last_crawled, config FROM crawled_sites"
            )
            
            for row in cursor:
                site_id, name, url, last_crawled, config_json = row
                try:
                    config = json.loads(config_json)
                    
                    # Check if we need to update this site
                    current_time = datetime.datetime.now()
                    if last_crawled is None:
                        should_update = True
                    else:
                        last_crawl_time = datetime.datetime.fromisoformat(last_crawled)
                        elapsed_seconds = (current_time - last_crawl_time).total_seconds()
                        should_update = elapsed_seconds >= config.get("update_frequency", 3600)
                    
                    if should_update:
                        self.logger.info(f"Crawling site: {name}")
                        self.crawl_site(site_id, config)
                        
                        # Update the last_crawled timestamp
                        conn.execute(
                            "UPDATE crawled_sites SET last_crawled = ? WHERE id = ?",
                            (current_time.isoformat(), site_id)
                        )
                except Exception as e:
                    self.logger.error(f"Error processing site {name}: {e}")
    
    def crawl_site(self, site_id, config):
        """Crawl a specific site using the appropriate strategy"""
        try:
            # Check if we should use auto-detection
            if config.get('crawler_type') == 'auto':
                self.logger.info(f"Using auto-detection for {config.get('name')}")
                articles = self.try_multiple_crawlers(site_id, config)
            else:
                # Determine which strategy to use
                strategy_name = config.get('crawler_type', 'standard_article')
                
                if strategy_name in self.crawler_strategies:
                    strategy = self.crawler_strategies[strategy_name]
                    self.logger.info(f"Using {strategy_name} crawler for {config.get('name')}")
                    articles = strategy(site_id, config)
                else:
                    self.logger.error(f"Unknown crawler type: {strategy_name}")
                    articles = []
            
            if articles:
                self.save_articles(articles)
                self.logger.info(f"Saved {len(articles)} articles from {config.get('name')}")
            else:
                self.logger.warning(f"No articles found for {config.get('name')}")
        except Exception as e:
            self.logger.error(f"Error crawling site {site_id}: {e}")
            traceback.print_exc()
            
    # =========================================================================
    # Crawler Strategy Methods
    # =========================================================================
    
    def crawl_standard_article_site(self, site_id, config):
        """Standard crawler for sites with typical article structure"""
        self.logger.info(f"Using standard article crawler for {config.get('name')}")
        
        # Request the site
        response = self._make_request(config["url"])
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Use selectors from config
        selectors = config.get("selectors", {})
        articles_selector = selectors.get("articles")
        
        if not articles_selector:
            self.logger.error(f"No article selector found for {config.get('name')}")
            return []
        
        # Extract articles
        article_elements = soup.select(articles_selector)
        self.logger.info(f"Found {len(article_elements)} article elements")
        
        # Process articles
        articles = []
        for article in article_elements[:config.get("max_items", 20)]:
            try:
                # Use selectors to extract data
                title_elem = article.select_one(selectors.get("title", ""))
                link_elem = article.select_one(selectors.get("link", ""))
                summary_elem = article.select_one(selectors.get("summary", ""))
                date_elem = article.select_one(selectors.get("published_date", ""))
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    
                    # Get URL and make it absolute if needed
                    link = link_elem["href"]
                    if not link.startswith(('http://', 'https://')):
                        link = urljoin(config["url"], link)
                    
                    # Get summary and date if available
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    published_date = date_elem.get_text(strip=True) if date_elem else ""
                    
                    # Create unique ID
                    article_id = f"{site_id}_{self._create_article_id(link)}"
                    
                    articles.append({
                        "id": article_id,
                        "site_id": site_id,
                        "title": title,
                        "url": link,
                        "summary": summary,
                        "published_date": published_date,
                        "crawled_date": datetime.datetime.now().isoformat()
                    })
            except Exception as e:
                self.logger.error(f"Error processing article: {e}")
        
        return articles
    
    def crawl_news_site(self, site_id, config):
        """Crawler for typical news sites with headline/summary format"""
        self.logger.info(f"Using news site crawler for {config.get('name')}")
        
        # Request the site
        response = self._make_request(config["url"])
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links that might be news articles
        news_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # Filter by URL patterns from config
            url_patterns = config.get("url_patterns", ["/article/", "/news/", "/story/"])
            
            if any(pattern in href for pattern in url_patterns):
                # Make URL absolute if needed
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(config["url"], href)
                
                # Get title from link text or title attribute
                title = a.get('title', '') or a.get_text(strip=True)
                
                # Add if title is reasonable length and not duplicate
                if title and len(title) > 5 and href not in [link.get('url') for link in news_links]:
                    news_links.append({
                        'title': title,
                        'url': href
                    })
        
        self.logger.info(f"Found {len(news_links)} news links")
        
        # Create article objects
        articles = []
        for link in news_links[:config.get("max_items", 20)]:
            try:
                article_id = f"{site_id}_{self._create_article_id(link['url'])}"
                
                articles.append({
                    "id": article_id,
                    "site_id": site_id,
                    "title": link['title'],
                    "url": link['url'],
                    "summary": "",  # No summary in basic link extraction
                    "published_date": "",  # No date in basic link extraction
                    "crawled_date": datetime.datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Error creating article: {e}")
        
        return articles
    
    def crawl_hacker_news(self, site_id, config):
        """Special crawler for Hacker News"""
        self.logger.info(f"Using Hacker News crawler for {config.get('name')}")
        
        # Request the site
        response = self._make_request(config["url"])
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all article rows (Hacker News specific structure)
        article_rows = soup.select('tr.athing')
        self.logger.info(f"Found {len(article_rows)} article rows")
        
        articles = []
        for row in article_rows[:config.get("max_items", 20)]:
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
                
                title = title_link.get_text(strip=True)
                url = title_link.get('href')
                
                # Make URL absolute if needed
                if not url.startswith(('http://', 'https://')):
                    url = urljoin(config["url"], url)
                
                # Create article object
                article_id = f"{site_id}_{story_id}"
                
                articles.append({
                    "id": article_id,
                    "site_id": site_id,
                    "title": title,
                    "url": url,
                    "summary": "",  # No summary on HN
                    "published_date": "",  # We could get this from subtext in future
                    "crawled_date": datetime.datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Error processing HN article: {e}")
        
        return articles
    
    def crawl_verge(self, site_id, config):
        """Special crawler for The Verge"""
        self.logger.info(f"Using The Verge crawler")
        
        # Request the site
        response = self._make_request(config["url"])
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for links that match article patterns
        article_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Look for URLs that match The Verge article patterns
            if '/news/' in href or re.search(r'/\d{4}/\d{1,2}/\d{1,2}/', href):
                # Skip comment links and duplicates
                if '#comments' not in href and href not in [link.get('href', '') for link in article_links]:
                    # Make sure we have a complete URL
                    if not href.startswith('http'):
                        href = urljoin(config["url"], href)
                    
                    title = a.get_text(strip=True)
                    
                    # Only include links with reasonable titles
                    if title and len(title) > 5 and title != "Comments":
                        article_links.append({
                            'title': title,
                            'href': href
                        })
        
        self.logger.info(f"Found {len(article_links)} article links on The Verge")
        
        # Create article objects
        articles = []
        for link in article_links[:config.get("max_items", 15)]:
            try:
                article_id = f"{site_id}_{self._create_article_id(link['href'])}"
                
                articles.append({
                    "id": article_id,
                    "site_id": site_id,
                    "title": link['title'],
                    "url": link['href'],
                    "summary": "",  # No summary in basic extraction
                    "published_date": "",  # No date in basic extraction
                    "crawled_date": datetime.datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Error creating Verge article: {e}")
        
        return articles
    
    def crawl_bbc_news(self, site_id, config):
        """Special crawler for BBC News"""
        self.logger.info(f"Using BBC News crawler")
        
        # Request the site
        response = self._make_request(config["url"])
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links that might be news articles
        news_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Look for URLs that match BBC news article patterns
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
        
        self.logger.info(f"Found {len(unique_links)} unique BBC news article links")
        
        # Create article objects
        articles = []
        for link in unique_links[:config.get("max_items", 15)]:
            try:
                article_id = f"{site_id}_{self._create_article_id(link['url'])}"
                
                articles.append({
                    "id": article_id,
                    "site_id": site_id,
                    "title": link['title'],
                    "url": link['url'],
                    "summary": "",  # No summary in basic extraction
                    "published_date": "",  # No date in basic extraction
                    "crawled_date": datetime.datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Error creating BBC article: {e}")
        
        return articles
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _make_request(self, url, max_retries=3, retry_delay=1):
        """Make a request with retry logic"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
        
        self.logger.error(f"All {max_retries} request attempts failed for {url}")
        return None
    
    def _create_article_id(self, url):
        """Create a unique ID for an article based on its URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def save_articles(self, articles):
        """Save crawled articles to the database"""
        with sqlite3.connect(self.db_path) as conn:
            articles_added = 0
            for article in articles:
                try:
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
                            (id, site_id, title, url, summary, published_date, crawled_date, is_read)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                article["id"],
                                article["site_id"],
                                article["title"],
                                article["url"],
                                article.get("summary", ""),
                                article.get("published_date", ""),
                                article.get("crawled_date", datetime.datetime.now().isoformat()),
                                False
                            )
                        )
                        articles_added += 1
                        self.logger.info(f"Added article: {article['title'][:50]}...")
                except Exception as e:
                    self.logger.error(f"Error saving article: {e}")
            
            self.logger.info(f"Added {articles_added} new articles to the database")
    
    def get_dashboard_data(self):
        """Retrieve data for the dashboard view"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get all sites
            cursor = conn.execute("SELECT id, name, url FROM crawled_sites ORDER BY name")
            sites = [dict(row) for row in cursor]
            
            # Get content for each site
            dashboard = []
            for site in sites:
                cursor = conn.execute(
                    """
                    SELECT * FROM crawled_content 
                    WHERE site_id = ? 
                    ORDER BY crawled_date DESC 
                    LIMIT 10
                    """,
                    (site["id"],)
                )
                
                articles = [dict(row) for row in cursor]
                dashboard.append({
                    "site": site,
                    "articles": articles
                })
            
            return dashboard

    def try_multiple_crawlers(self, site_id, config, crawler_types=None):
        """Try multiple crawler types in sequence until one succeeds"""
        
        if not crawler_types:
            # Default sequence to try, from most specific to most general
            crawler_types = ['verge', 'hacker_news', 'bbc', 'news_site', 'standard_article']
        
        # Make a copy of the config for modification
        test_config = config.copy()
        
        for crawler_type in crawler_types:
            if crawler_type in self.crawler_strategies:
                self.logger.info(f"Trying {crawler_type} crawler for {config.get('name')}")
                
                # Update the temporary config to use this crawler type
                test_config['crawler_type'] = crawler_type
                
                # Try this crawler
                strategy = self.crawler_strategies[crawler_type]
                articles = strategy(site_id, test_config)
                
                # If we found articles, consider it successful
                if articles and len(articles) > 0:
                    self.logger.info(f"Successfully crawled {config.get('name')} with {crawler_type} strategy ({len(articles)} articles)")
                    
                    # Update the site's config with the successful crawler type
                    with sqlite3.connect(self.db_path) as conn:
                        # Read current config
                        cursor = conn.execute("SELECT config FROM crawled_sites WHERE id = ?", (site_id,))
                        row = cursor.fetchone()
                        if row:
                            current_config = json.loads(row[0])
                            # Update crawler type
                            current_config['crawler_type'] = crawler_type
                            # Save back to database
                            conn.execute(
                                "UPDATE crawled_sites SET config = ? WHERE id = ?",
                                (json.dumps(current_config), site_id)
                            )
                    
                    return articles
                else:
                    self.logger.info(f"No articles found with {crawler_type} crawler, trying next type")
        
        # If we get here, no crawler type worked
        self.logger.warning(f"All crawler types failed for {config.get('name')}")
        return []

# Entry point for running crawler
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Web Crawler for Personal Dashboard')
    parser.add_argument('--register', action='store_true', help='Register sites from configuration')
    parser.add_argument('--crawl', action='store_true', help='Crawl all registered sites')
    parser.add_argument('--site', type=str, help='Crawl a specific site by ID')
    
    args = parser.parse_args()
    
    crawler = UnifiedCrawler()
    
    if args.register:
        print("Registering sites...")
        for config in SITE_CONFIGS:
            print(f"Registering site: {config}")
            crawler.register_site(config)
    
    if args.site:
        print(f"Crawling specific site: {args.site}")
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT id, name, url, config FROM crawled_sites WHERE id = ?",
                (args.site,)
            )
            row = cursor.fetchone()
            
            if row:
                site_id, name, url, config_json = row
                config = json.loads(config_json)
                print(f"Crawling {name}...")
                crawler.crawl_site(site_id, config)
            else:
                print(f"Site {args.site} not found")
    
    elif args.crawl:
        print("Crawling all sites...")
        crawler.crawl_all_sites()
    
    # If no arguments provided, register and crawl all
    if not (args.register or args.crawl or args.site):
        print("No arguments provided - registering and crawling all sites")
        for config in SITE_CONFIGS:
            crawler.register_site(config)
        crawler.crawl_all_sites()