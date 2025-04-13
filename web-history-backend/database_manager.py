import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import urlparse

# Database configuration
DATABASE_FILE = 'web_history.db'
SCHEMA_FILE = 'schema.sql'

# Old file paths for migration
HISTORY_FILE = 'history.json'
FOLDERS_FILE = 'folders.json'
FREQUENCY_FILE = 'frequency.json'

class DatabaseManager:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.conn = None
    
    def initialize_db(self):
        """Initialize the database with schema if it doesn't exist"""
        db_exists = os.path.exists(self.db_file)
        
        # Connect to the database (creates file if it doesn't exist)
        conn = sqlite3.connect(self.db_file)
        
        # Set connection to return rows as dictionaries
        conn.row_factory = sqlite3.Row
        
        # Create schema if database is new
        if not db_exists:
            print(f"Creating new database {self.db_file}")
            with open(SCHEMA_FILE, 'r') as f:
                schema = f.read()
                conn.executescript(schema)
                conn.commit()
        
        conn.close()
        print(f"Database initialized: {self.db_file}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()
    
    def migrate_from_json(self):
        """Migrate data from JSON files to SQLite database"""
        print("Starting migration from JSON files to SQLite...")
        
        # Check if files exist
        if not os.path.exists(HISTORY_FILE) or not os.path.exists(FOLDERS_FILE) or not os.path.exists(FREQUENCY_FILE):
            print("One or more source JSON files are missing. Skipping migration.")
            return False
        
        try:
            # Connect to database
            with self.get_connection() as conn:
                # Migrate history
                print("Migrating history...")
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
                    
                for idx, page in enumerate(history):
                    # Parse domain from URL
                    url = page.get('url', '')
                    try:
                        domain = urlparse(url).netloc
                    except:
                        domain = ''
                    
                    # Ensure timestamp is a string
                    timestamp = page.get('timestamp', '')
                    if isinstance(timestamp, dict) and '$date' in timestamp:
                        timestamp = timestamp['$date']
                    
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO history (id, url, title, timestamp, domain)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            page.get('id', str(idx)),
                            url,
                            page.get('title', ''),
                            timestamp,
                            domain
                        )
                    )
                
                # Migrate folders
                print("Migrating folders...")
                with open(FOLDERS_FILE, 'r') as f:
                    folders = json.load(f)
                
                for idx, folder in enumerate(folders):
                    folder_id = folder.get('id', str(idx))
                    
                    # Insert folder
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO folders (id, name, is_collapsed, display_order)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            folder_id,
                            folder.get('name', f'Folder {idx}'),
                            folder.get('isCollapsed', False),
                            idx
                        )
                    )
                    
                    # Insert pages in this folder
                    pages = folder.get('pages', [])
                    for page_idx, page in enumerate(pages):
                        # Ensure timestamp is a string
                        timestamp = page.get('timestamp', '')
                        if isinstance(timestamp, dict) and '$date' in timestamp:
                            timestamp = timestamp['$date']
                        
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO folder_pages 
                            (folder_id, page_id, url, title, timestamp, display_order)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                folder_id,
                                page.get('id', str(page_idx)),
                                page.get('url', ''),
                                page.get('title', ''),
                                timestamp,
                                page_idx
                            )
                        )
                
                # Migrate frequency data
                print("Migrating frequency data...")
                with open(FREQUENCY_FILE, 'r') as f:
                    frequency = json.load(f)
                
                for url, data in frequency.items():
                    try:
                        domain = urlparse(url).netloc
                    except:
                        domain = data.get('domain', '')
                    
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO frequency (url, title, count, domain)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            url,
                            data.get('title', url),
                            data.get('count', 1),
                            domain
                        )
                    )
                
                print("Migration completed successfully")
                return True
                
        except Exception as e:
            print(f"Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return False

# Database operations for history
class HistoryDB:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_all(self):
        """Get all history entries"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM history ORDER BY timestamp DESC"
            )
            return [dict(row) for row in cursor]
    
    def add(self, page):
        """Add a new page to history"""
        with self.db_manager.get_connection() as conn:
            # Parse domain
            try:
                domain = urlparse(page['url']).netloc
            except:
                domain = ''
            
            # Insert into history
            conn.execute(
                """
                INSERT INTO history (id, url, title, timestamp, domain)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    page.get('id', str(datetime.now().timestamp() * 1000)),
                    page['url'],
                    page.get('title', ''),
                    page.get('timestamp', datetime.now().isoformat()),
                    domain
                )
            )
            
            # Update frequency
            self.update_frequency(conn, page)
            
            return page
    
    def update_frequency(self, conn, page):
        """Update the frequency counter for a URL"""
        url = page['url']
        
        # Get existing frequency
        cursor = conn.execute(
            "SELECT count FROM frequency WHERE url = ?",
            (url,)
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing frequency
            conn.execute(
                "UPDATE frequency SET count = count + 1, title = ? WHERE url = ?",
                (page.get('title', url), url)
            )
        else:
            # Insert new frequency entry
            try:
                domain = urlparse(url).netloc
            except:
                domain = ''
            
            conn.execute(
                """
                INSERT INTO frequency (url, title, count, domain)
                VALUES (?, ?, ?, ?)
                """,
                (
                    url,
                    page.get('title', url),
                    1,
                    domain
                )
            )
    
    def get_frequent(self):
        """Get pages ordered by visit frequency"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT url, title, count, domain FROM frequency
                ORDER BY count DESC
                """
            )
            
            frequent_pages = []
            for row in cursor:
                row_dict = dict(row)
                frequent_pages.append({
                    'id': str(datetime.now().timestamp() * 1000),  # Generate a new ID
                    'url': row_dict['url'],
                    'title': row_dict['title'],
                    'visitCount': row_dict['count'],
                    'timestamp': datetime.now().isoformat()
                })
            
            return frequent_pages

# Database operations for folders
class FoldersDB:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_all(self):
        """Get all folders with their pages"""
        with self.db_manager.get_connection() as conn:
            # Get all folders
            cursor = conn.execute(
                "SELECT * FROM folders ORDER BY display_order"
            )
            folders = [dict(row) for row in cursor]
            
            # For each folder, get its pages
            for folder in folders:
                cursor = conn.execute(
                    """
                    SELECT * FROM folder_pages 
                    WHERE folder_id = ? 
                    ORDER BY display_order
                    """,
                    (folder['id'],)
                )
                folder['pages'] = [dict(row) for row in cursor]
                
                # Convert is_collapsed to isCollapsed for frontend compatibility
                folder['isCollapsed'] = folder.pop('is_collapsed', False)
            
            return folders
    
    def create(self, folder):
        """Create a new folder"""
        with self.db_manager.get_connection() as conn:
            # Get max display_order
            cursor = conn.execute("SELECT MAX(display_order) as max_order FROM folders")
            row = cursor.fetchone()
            max_order = row['max_order'] if row and row['max_order'] is not None else 0
            
            folder_id = folder.get('id', str(datetime.now().timestamp() * 1000))
            
            conn.execute(
                """
                INSERT INTO folders (id, name, is_collapsed, display_order)
                VALUES (?, ?, ?, ?)
                """,
                (
                    folder_id,
                    folder.get('name', 'New Folder'),
                    folder.get('isCollapsed', False),
                    max_order + 1
                )
            )
            
            # Return created folder
            folder['id'] = folder_id
            folder['pages'] = []
            return folder
    
    def delete(self, folder_id):
        """Delete a folder and its pages"""
        with self.db_manager.get_connection() as conn:
            conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            return True
    
    def add_page(self, folder_id, page):
        """Add a page to a folder"""
        with self.db_manager.get_connection() as conn:
            # Check if URL already exists in this folder
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM folder_pages WHERE folder_id = ? AND url = ?",
                (folder_id, page['url'])
            )
            row = cursor.fetchone()
            
            if row and row['count'] > 0:
                return False, "URL already exists in folder"
            
            # Get max display_order
            cursor = conn.execute(
                "SELECT MAX(display_order) as max_order FROM folder_pages WHERE folder_id = ?",
                (folder_id,)
            )
            row = cursor.fetchone()
            max_order = row['max_order'] if row and row['max_order'] is not None else 0
            
            page_id = page.get('id', str(datetime.now().timestamp() * 1000))
            
            conn.execute(
                """
                INSERT INTO folder_pages (folder_id, page_id, url, title, timestamp, display_order)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    folder_id,
                    page_id,
                    page['url'],
                    page.get('title', ''),
                    page.get('timestamp', datetime.now().isoformat()),
                    max_order + 1
                )
            )
            
            page['id'] = page_id
            return True, page
    
    def remove_page(self, folder_id, page_id):
        """Remove a page from a folder"""
        with self.db_manager.get_connection() as conn:
            conn.execute(
                "DELETE FROM folder_pages WHERE folder_id = ? AND page_id = ?",
                (folder_id, page_id)
            )
            return True
    
    def move_page(self, source_id, page_id, target_id):
        """Move a page from one place (history or folder) to a folder"""
        with self.db_manager.get_connection() as conn:
            page = None
            
            # Try to find page in a folder
            if source_id:
                cursor = conn.execute(
                    "SELECT * FROM folder_pages WHERE folder_id = ? AND page_id = ?",
                    (source_id, page_id)
                )
                row = cursor.fetchone()
                
                if row:
                    page = dict(row)
                    # Remove from source folder
                    conn.execute(
                        "DELETE FROM folder_pages WHERE folder_id = ? AND page_id = ?",
                        (source_id, page_id)
                    )
            
            # If not found in folders, look in history
            if not page:
                cursor = conn.execute(
                    "SELECT * FROM history WHERE id = ?",
                    (page_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    page = dict(row)
            
            if not page:
                return False, "Page not found"
            
            # Check if URL already exists in target folder
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM folder_pages WHERE folder_id = ? AND url = ?",
                (target_id, page['url'])
            )
            row = cursor.fetchone()
            
            if row and row['count'] > 0:
                return False, "URL already exists in folder"
            
            # Get max display_order
            cursor = conn.execute(
                "SELECT MAX(display_order) as max_order FROM folder_pages WHERE folder_id = ?",
                (target_id,)
            )
            row = cursor.fetchone()
            max_order = row['max_order'] if row and row['max_order'] is not None else 0
            
            # Add to target folder
            conn.execute(
                """
                INSERT INTO folder_pages (folder_id, page_id, url, title, timestamp, display_order)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    target_id,
                    page_id,
                    page['url'],
                    page.get('title', ''),
                    page.get('timestamp', datetime.now().isoformat()),
                    max_order + 1
                )
            )
            
            return True, page
    
    def rename(self, folder_id, new_name):
        """Rename a folder"""
        with self.db_manager.get_connection() as conn:
            # Check for name collisions
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM folders WHERE name = ? AND id != ?",
                (new_name, folder_id)
            )
            row = cursor.fetchone()
            
            if row and row['count'] > 0:
                return False, "A folder with this name already exists"
            
            conn.execute(
                "UPDATE folders SET name = ? WHERE id = ?",
                (new_name, folder_id)
            )
            
            return True, {"name": new_name}
    
    def update_order(self, folders):
        """Update the order of folders"""
        with self.db_manager.get_connection() as conn:
            for idx, folder in enumerate(folders):
                conn.execute(
                    "UPDATE folders SET display_order = ?, is_collapsed = ? WHERE id = ?",
                    (idx, folder.get('isCollapsed', False), folder['id'])
                )
            
            return True
    
    def update_page_order(self, folder_id, pages):
        """Update the order of pages in a folder"""
        with self.db_manager.get_connection() as conn:
            for idx, page in enumerate(pages):
                conn.execute(
                    "UPDATE folder_pages SET display_order = ? WHERE folder_id = ? AND page_id = ?",
                    (idx, folder_id, page['id'])
                )
            
            return True

# Create database manager instance
db_manager = DatabaseManager()

# Create model instances
history_db = HistoryDB(db_manager)
folders_db = FoldersDB(db_manager)