import os
import json
import shutil
import threading
import time
import sqlite3
import hashlib
from datetime import datetime

# File paths
DATABASE_FILE = 'web_history.db'
CONFIG_FILE = "backup_config.json"
BACKUP_METADATA_FILE = "backup_metadata.json"
INTERVAL_FALLBACK = 3600  # Default backup interval (1 hour)

class BackupManager:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
    
    def load_backup_config(self):
        """Load backup configuration from file"""
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create default config if file doesn't exist or is invalid
            default_config = {
                "backup_interval_seconds": INTERVAL_FALLBACK,
                "backup_directory": "./backups",
                "max_backups": 10
            }
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config):
        """Save backup configuration to file"""
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    
    def get_backup_metadata(self):
        """Get information about the last backup"""
        if os.path.exists(BACKUP_METADATA_FILE):
            try:
                with open(BACKUP_METADATA_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_backup_time": 0,
            "db_hash": None
        }
    
    def save_backup_metadata(self, metadata):
        """Save information about the current backup"""
        with open(BACKUP_METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def calculate_db_hash(self):
        """Calculate SHA-256 hash of database file to detect changes"""
        if not os.path.exists(self.db_file):
            return None
        
        hasher = hashlib.sha256()
        with open(self.db_file, 'rb') as f:
            buf = f.read(65536)  # Read in 64k chunks
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    
    def perform_backup(self):
        """Create a backup of the database if it has changed"""
        print("Checking for changes since last backup...")
        try:
            config = self.load_backup_config()
            interval = config.get("backup_interval_seconds", INTERVAL_FALLBACK)
            backup_dir = os.path.abspath(config.get("backup_directory", "./backups"))
            max_backups = config.get("max_backups", 10)
            
            # Make sure backup directory exists
            os.makedirs(backup_dir, exist_ok=True)
            
            # Get last backup info
            metadata = self.get_backup_metadata()
            current_hash = self.calculate_db_hash()
            
            if current_hash is None:
                print(f"Database file {self.db_file} not found, skipping backup")
                return interval
            
            if current_hash != metadata.get("db_hash"):
                # Database has changed, create a backup
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(backup_dir, f"web_history_{timestamp}.db")
                
                # First make sure database is not in the middle of a transaction
                try:
                    conn = sqlite3.connect(self.db_file)
                    conn.execute("PRAGMA wal_checkpoint(FULL)")
                    conn.close()
                except Exception as e:
                    print(f"Warning: Could not checkpoint database: {e}")
                
                # Copy the database file
                shutil.copy2(self.db_file, backup_path)
                print(f"Created backup at {backup_path}")
                
                # Update metadata
                metadata["last_backup_time"] = time.time()
                metadata["db_hash"] = current_hash
                self.save_backup_metadata(metadata)
                
                # Prune old backups if we exceed the maximum
                self.prune_old_backups(backup_dir, max_backups)
            else:
                print("No changes detected since last backup, skipping...")
            
            return interval
        except Exception as e:
            print(f"Backup error: {e}")
            import traceback
            traceback.print_exc()
            return INTERVAL_FALLBACK
    
    def prune_old_backups(self, backup_dir, max_backups):
        """Remove old backups if we exceed the maximum number of backups"""
        try:
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith("web_history_") and f.endswith(".db")]
            if len(backup_files) <= max_backups:
                return
            
            # Sort by date (oldest first)
            backup_files.sort()
            
            # Remove oldest backups
            for i in range(len(backup_files) - max_backups):
                old_file = os.path.join(backup_dir, backup_files[i])
                os.remove(old_file)
                print(f"Removed old backup: {old_file}")
        except Exception as e:
            print(f"Error pruning old backups: {e}")
    
    def restore_backup(self, timestamp):
        """Restore from a backup file"""
        config = self.load_backup_config()
        backup_dir = os.path.abspath(config.get("backup_directory", "./backups"))
        backup_file = f"web_history_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_file)
        
        if not os.path.exists(backup_path):
            print(f"Backup not found: {backup_file}")
            return False
        
        try:
            # Check if current database exists
            if os.path.exists(self.db_file):
                # Create a backup of current state just in case
                timestamp_now = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_backup = f"{self.db_file}.{timestamp_now}.bak"
                shutil.copy2(self.db_file, current_backup)
                print(f"Created backup of current database at {current_backup}")
            
            # Copy the backup file to the current database location
            shutil.copy2(backup_path, self.db_file)
            print(f"Restored database from {backup_file}")
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def backup_files_periodically(self):
        """Run backup periodically based on the configured interval"""
        while True:
            interval = self.perform_backup()
            time.sleep(interval)
    
    def start_backup_thread(self):
        """Start a background thread for periodic backups"""
        thread = threading.Thread(target=self.backup_files_periodically, daemon=True)
        thread.start()
        print("Backup thread started")

# Create an instance for direct use
backup_manager = BackupManager()