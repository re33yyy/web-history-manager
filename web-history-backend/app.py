from flask import Flask, jsonify, request
from flask_cors import CORS
from flask import make_response
import json
import os
from datetime import datetime
import uuid
import threading
import time
import argparse
import hashlib
from urllib.parse import urlparse
import sqlite3

from database_manager import db_manager, history_db, folders_db
from backup_manager import backup_manager
from unified_crawler import UnifiedCrawler, SITE_CONFIGS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

crawler = UnifiedCrawler()

# Initialize database
db_manager.initialize_db()

@app.after_request
def add_header(response):
    # More aggressive cache prevention
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Routes for history
@app.route('/api/history', methods=['GET'])
def get_history():
    history = history_db.get_all()
    return jsonify(history)

@app.route('/api/history', methods=['POST'])
def add_history():
    page = request.json
    if 'title' in page and page['title'] == 'WebHistoryFrontend':
        return jsonify(page), 201
    if 'id' not in page:
        page['id'] = str(uuid.uuid4())
    if 'timestamp' not in page:
        page['timestamp'] = datetime.now().isoformat()

    if 'favicon' in page:
        del page['favicon']
    
    # Add to history database
    history_db.add(page)
    return jsonify(page), 201

@app.route('/api/history/frequent', methods=['GET'])
def get_frequent_pages():
    frequent_pages = history_db.get_frequent()
    return jsonify(frequent_pages)

# Routes for folders
@app.route('/api/folders', methods=['GET'])
def get_folders():
    folders = folders_db.get_all()
    return jsonify(folders)

@app.route('/api/folders', methods=['POST'])
def create_folder():
    folder = request.json
    if 'id' not in folder:
        folder['id'] = str(uuid.uuid4())
    if 'pages' not in folder:
        folder['pages'] = []
    
    created_folder = folders_db.create(folder)
    return jsonify(created_folder), 201

@app.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    folders_db.delete(folder_id)
    return '', 204

@app.route('/api/folders/<folder_id>/pages', methods=['POST'])
def add_page_to_folder(folder_id):
    page = request.json
    if 'id' not in page:
        page['id'] = str(uuid.uuid4())
    if 'timestamp' not in page:
        page['timestamp'] = datetime.now().isoformat()
    
    success, result = folders_db.add_page(folder_id, page)
    
    if success:
        return jsonify(result), 201
    else:
        return jsonify({"error": result}), 409

@app.route('/api/folders/<folder_id>/pages/<page_id>', methods=['POST'])
def move_page_to_folder(folder_id, page_id):
    # Source folder is null in this case (could be from history)
    success, result = folders_db.move_page(None, page_id, folder_id)
    
    if success:
        return jsonify(result), 200
    else:
        return jsonify({"error": result}), 409 if "already exists" in result else 404

@app.route('/api/folders/<folder_id>/remove-page', methods=['POST'])
def alt_remove_page_from_folder(folder_id):
    data = request.json
    page_id = data.get('pageId')
    
    folders_db.remove_page(folder_id, page_id)
    return '', 204

@app.route('/api/folders/<folder_id>/pages/<page_id>', methods=['DELETE'])
def remove_page_from_folder(folder_id, page_id):
    folders_db.remove_page(folder_id, page_id)
    return '', 204

@app.route('/api/folders/<folder_id>/rename', methods=['POST'])
def rename_folder(folder_id):
    """
    Rename a folder and check for name collisions
    """
    request_data = request.json
    new_name = request_data.get('name', '').strip()
    
    # Validate the new name
    if not new_name:
        return jsonify({"error": "Folder name cannot be empty"}), 400
    
    success, result = folders_db.rename(folder_id, new_name)
    
    if success:
        return jsonify({"success": True, "name": new_name}), 200
    else:
        return jsonify({"error": result}), 409

@app.route('/api/folders/reorder', methods=['POST'])
def reorder_folders():
    """
    Update the order of folders and save their collapsed state
    """
    updated_folders = request.json
    
    success = folders_db.update_order(updated_folders)
    
    return jsonify({"success": success}), 200

@app.route('/api/folders/<folder_id>/pages/reorder', methods=['POST'])
def reorder_pages_in_folder(folder_id):
    updated_pages = request.json
    
    success = folders_db.update_page_order(folder_id, updated_pages)
    
    return jsonify({"success": success}), 200

@app.route('/api/export-bookmarks', methods=['GET'])
def export_bookmarks():
    folders = folders_db.get_all()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    top_folder_name = f"WebHistoryManager Export - {timestamp}"

    lines = [
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        '<TITLE>Bookmarks</TITLE>',
        '<H1>Bookmarks</H1>',
        '<DL><p>',
        f'    <DT><H3>{top_folder_name}</H3>',
        '    <DL><p>'
    ]

    for folder in folders:
        lines.append(f'        <DT><H3>{folder["name"]}</H3>')
        lines.append('        <DL><p>')
        for page in folder['pages']:
            title = page.get('title', page['url'])
            url = page['url']
            add_date = int(datetime.now().timestamp())
            lines.append(f'            <DT><A HREF="{url}" ADD_DATE="{add_date}">{title}</A>')
        lines.append('        </DL><p>')
    
    lines.append('    </DL><p>')
    lines.append('</DL><p>')

    html_content = '\n'.join(lines)

    return html_content, 200, {
        'Content-Type': 'text/html; charset=utf-8',
        'Content-Disposition': 'attachment; filename="webhistory_bookmarks.html"'
    }

@app.route('/api/migrate', methods=['POST'])
def migrate_data():
    """Endpoint to trigger migration from JSON to SQLite"""
    success = db_manager.migrate_from_json()
    
    if success:
        return jsonify({"success": True, "message": "Migration completed successfully"}), 200
    else:
        return jsonify({"success": False, "message": "Migration failed. Check server logs for details."}), 500

# Backup management endpoints
@app.route('/api/backup/create', methods=['POST'])
def create_backup():
    """Manually create a backup"""
    try:
        backup_manager.perform_backup()
        return jsonify({"success": True, "message": "Backup created successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Backup failed: {str(e)}"}), 500

@app.route('/api/backup/list', methods=['GET'])
def list_backups():
    """List available backups"""
    try:
        config = backup_manager.load_backup_config()
        backup_dir = os.path.abspath(config.get("backup_directory", "./backups"))
        
        if not os.path.exists(backup_dir):
            return jsonify({"backups": []}), 200
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.startswith("web_history_") and filename.endswith(".db"):
                # Extract timestamp from filename
                timestamp = filename.replace("web_history_", "").replace(".db", "")
                
                # Get file size and creation time
                filepath = os.path.join(backup_dir, filename)
                size = os.path.getsize(filepath)
                created = os.path.getctime(filepath)
                
                backups.append({
                    "timestamp": timestamp,
                    "size": size,
                    "created": datetime.fromtimestamp(created).isoformat(),
                    "filename": filename
                })
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return jsonify({"backups": backups}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error listing backups: {str(e)}"}), 500

@app.route('/api/backup/restore/<timestamp>', methods=['POST'])
def restore_backup_api(timestamp):
    """Restore database from a backup"""
    try:
        success = backup_manager.restore_backup(timestamp)
        if success:
            return jsonify({"success": True, "message": "Database restored successfully"}), 200
        else:
            return jsonify({"success": False, "message": "Restore failed"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Restore error: {str(e)}"}), 500

@app.route('/api/backup/config', methods=['GET'])
def get_backup_config():
    """Get backup configuration"""
    config = backup_manager.load_backup_config()
    return jsonify(config), 200

@app.route('/api/backup/config', methods=['POST'])
def update_backup_config():
    """Update backup configuration"""
    try:
        new_config = request.json
        
        # Validate configuration
        if "backup_interval_seconds" in new_config:
            interval = int(new_config["backup_interval_seconds"])
            if interval < 300:  # Minimum 5 minutes
                return jsonify({"success": False, "message": "Backup interval must be at least 300 seconds (5 minutes)"}), 400
        
        # Load current config and update with new values
        config = backup_manager.load_backup_config()
        config.update(new_config)
        
        # Save updated config using backup_manager
        backup_manager.save_config(config)
        
        return jsonify({"success": True, "message": "Backup configuration updated"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error updating config: {str(e)}"}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard data with content from all crawled sites"""
    try:
        dashboard_data = crawler.get_dashboard_data()
        return jsonify(dashboard_data), 200
    except Exception as e:
        print(f"Error retrieving dashboard data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error retrieving dashboard data: {str(e)}"}), 500

@app.route('/api/sites', methods=['GET'])
def get_sites():
    """Get list of registered sites"""
    try:
        with sqlite3.connect('web_history.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id, name, url, last_crawled FROM crawled_sites ORDER BY name")
            sites = [dict(row) for row in cursor]
            return jsonify(sites), 200
    except Exception as e:
        return jsonify({"error": f"Error retrieving sites: {str(e)}"}), 500

@app.route('/api/sites', methods=['POST'])
def add_site():
    """Add a new site to be crawled"""
    try:
        site_config = request.json
        if not site_config or not site_config.get('url') or not site_config.get('name'):
            return jsonify({"error": "Missing required fields (name, url)"}), 400
        
        success = crawler.register_site(site_config)
        if success:
            return jsonify({"success": True, "message": f"Site {site_config['name']} registered"}), 201
        else:
            return jsonify({"error": "Failed to register site"}), 500
    except Exception as e:
        return jsonify({"error": f"Error adding site: {str(e)}"}), 500

@app.route('/api/sites/<site_id>', methods=['DELETE'])
def delete_site(site_id):
    """Delete a site and its articles"""
    try:
        with sqlite3.connect('web_history.db') as conn:
            # First delete related articles
            conn.execute("DELETE FROM crawled_content WHERE site_id = ?", (site_id,))
            # Then delete the site
            conn.execute("DELETE FROM crawled_sites WHERE id = ?", (site_id,))
            return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": f"Error deleting site: {str(e)}"}), 500
        
@app.route('/api/sites', methods=['GET'])
def get_crawled_sites():
    """Get list of sites being crawled"""
    try:
        with sqlite3.connect('web_history.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id, name, url, last_crawled FROM crawled_sites ORDER BY name")
            sites = [dict(row) for row in cursor]
            return jsonify(sites), 200
    except Exception as e:
        return jsonify({"error": f"Error retrieving sites: {str(e)}"}), 500

@app.route('/api/sites/<site_id>/articles', methods=['GET'])
def get_site_articles(site_id):
    """Get articles for a specific site"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        with sqlite3.connect('web_history.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM crawled_content 
                WHERE site_id = ? 
                ORDER BY crawled_date DESC 
                LIMIT ?
                """,
                (site_id, limit)
            )
            articles = [dict(row) for row in cursor]
            return jsonify(articles), 200
    except Exception as e:
        return jsonify({"error": f"Error retrieving articles: {str(e)}"}), 500

@app.route('/api/crawl/trigger', methods=['POST'])
def trigger_crawl():
    """Manually trigger a crawl of all sites"""
    try:
        # Register any unregistered sites first
        for config in SITE_CONFIGS:
            crawler.register_site(config)
        
        # Start crawling in a separate thread to not block the response
        import threading
        thread = threading.Thread(target=crawler.crawl_all_sites)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True, 
            "message": "Crawl started in background"
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error triggering crawl: {str(e)}"}), 500
    
@app.route('/api/crawl/site/<site_id>', methods=['POST'])
def crawl_site(site_id):
    """Crawl a specific site"""
    try:
        with sqlite3.connect('web_history.db') as conn:
            cursor = conn.execute(
                "SELECT id, name, url, config FROM crawled_sites WHERE id = ?",
                (site_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return jsonify({"error": f"Site {site_id} not found"}), 404
            
            site_id, name, url, config_json = row
            config = json.loads(config_json)
            
            # Start crawling in a separate thread
            import threading
            thread = threading.Thread(target=crawler.crawl_site, args=(site_id, config))
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "success": True, 
                "message": f"Crawling {name} in background"
            }), 200
    except Exception as e:
        return jsonify({"error": f"Error crawling site: {str(e)}"}), 500
        
@app.route('/api/articles/<article_id>/mark-read', methods=['POST'])
def mark_article_read(article_id):
    """Mark an article as read"""
    try:
        print(f"Attempting to mark article {article_id} as read")
        with sqlite3.connect('web_history.db') as conn:
            result = conn.execute(
                "UPDATE crawled_content SET is_read = 1 WHERE id = ?",
                (article_id,)
            )
            print(f"Rows affected: {result.rowcount}")
            conn.commit()
            return jsonify({"success": True}), 200
    except Exception as e:
        print(f"Error marking article as read: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error marking article as read: {str(e)}"}), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--migrate', action='store_true', help='Migrate data from JSON files to SQLite database')
    parser.add_argument('--restore', help='Restore backup from timestamp like 20250407_120653')
    args = parser.parse_args()

    if args.migrate:
        db_manager.initialize_db()
        success = db_manager.migrate_from_json()
        print(f"Migration {'completed successfully' if success else 'failed'}")
    elif args.restore:
        success = backup_manager.restore_backup(args.restore)
        print(f"Restore {'completed successfully' if success else 'failed'}")
    else:
        # Start backup thread
        backup_manager.start_backup_thread()
        
        # Start the application
        app.run(debug=True)