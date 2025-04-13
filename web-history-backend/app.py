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

from database_manager import db_manager, history_db, folders_db
from backup_manager import backup_manager

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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