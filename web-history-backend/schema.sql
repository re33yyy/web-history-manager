-- Schema for Web History Manager
-- Defines tables for history items, folders, pages in folders, and page frequency

-- Table for history entries
CREATE TABLE IF NOT EXISTS history (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    timestamp TEXT NOT NULL,
    domain TEXT
);

-- Table for storing folders
CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    is_collapsed BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0
);

-- Table for storing pages within folders
CREATE TABLE IF NOT EXISTS folder_pages (
    folder_id TEXT NOT NULL,
    page_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    timestamp TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    PRIMARY KEY (folder_id, page_id),
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
);

-- Table for frequency data
CREATE TABLE IF NOT EXISTS frequency (
    url TEXT PRIMARY KEY,
    title TEXT,
    count INTEGER DEFAULT 1,
    domain TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp);
CREATE INDEX IF NOT EXISTS idx_history_url ON history(url);
CREATE INDEX IF NOT EXISTS idx_folder_pages_url ON folder_pages(url);
CREATE INDEX IF NOT EXISTS idx_frequency_count ON frequency(count);

-- Table for storing sites to crawl
CREATE TABLE IF NOT EXISTS crawled_sites (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    last_crawled TIMESTAMP,
    config TEXT
);

-- Table for storing crawled content
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
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_content_site ON crawled_content(site_id);
CREATE INDEX IF NOT EXISTS idx_content_read ON crawled_content(is_read);
CREATE INDEX IF NOT EXISTS idx_content_date ON crawled_content(crawled_date);
