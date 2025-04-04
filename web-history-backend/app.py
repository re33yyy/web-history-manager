from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
import uuid
from collections import Counter
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# File paths for storing data
HISTORY_FILE = 'history.json'
FOLDERS_FILE = 'folders.json'
FREQUENCY_FILE = 'frequency.json'

# Initialize data files if they don't exist
def init_data_files():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(FOLDERS_FILE):
        with open(FOLDERS_FILE, 'w') as f:
            json.dump([], f)
            
    if not os.path.exists(FREQUENCY_FILE):
        with open(FREQUENCY_FILE, 'w') as f:
            json.dump({}, f)

init_data_files()

# Helper functions to read/write data
def read_history():
    with open(HISTORY_FILE, 'r') as f:
        try:
            history = json.load(f)
            for page in history:
                if 'timestamp' in page and isinstance(page['timestamp'], str):
                    page['timestamp'] = datetime.fromisoformat(page['timestamp'].replace('Z', '+00:00'))
            return history
        except json.JSONDecodeError:
            return []

def write_history(history):
    # Convert datetime objects to strings for JSON serialization
    serializable_history = []
    for page in history:
        page_copy = page.copy()
        if 'timestamp' in page_copy and isinstance(page_copy['timestamp'], datetime):
            page_copy['timestamp'] = page_copy['timestamp'].isoformat()
        serializable_history.append(page_copy)
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(serializable_history, f)

def read_folders():
    with open(FOLDERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def write_folders(folders):
    # Convert datetime objects to strings for JSON serialization
    serializable_folders = []
    for folder in folders:
        folder_copy = folder.copy()
        pages = []
        for page in folder_copy['pages']:
            page_copy = page.copy()
            if 'timestamp' in page_copy and isinstance(page_copy['timestamp'], datetime):
                page_copy['timestamp'] = page_copy['timestamp'].isoformat()
            pages.append(page_copy)
        folder_copy['pages'] = pages
        serializable_folders.append(folder_copy)
    
    with open(FOLDERS_FILE, 'w') as f:
        json.dump(serializable_folders, f)

def read_frequency():
    with open(FREQUENCY_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def write_frequency(frequency):
    with open(FREQUENCY_FILE, 'w') as f:
        json.dump(frequency, f)

def get_domain(url):
    """Extract domain from URL"""
    parsed_url = urlparse(url)
    return parsed_url.netloc

# Routes for history
@app.route('/api/history', methods=['GET'])
def get_history():
    history = read_history()
    # Convert datetime objects to strings for JSON serialization
    for page in history:
        if 'timestamp' in page and isinstance(page['timestamp'], datetime):
            page['timestamp'] = page['timestamp'].isoformat()
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
    
    # Update frequency counter
    frequency = read_frequency()
    url = page['url']
    domain = get_domain(url)
    
    if url in frequency:
        frequency[url]['count'] += 1
        if 'title' in page:
            frequency[url]['title'] = page['title']
        if 'favicon' in page:
            frequency[url]['favicon'] = page['favicon']
    else:
        frequency[url] = {
            'count': 1,
            'title': page.get('title', url),
            'favicon': page.get('favicon', ''),
            'domain': domain
        }
    
    write_frequency(frequency)
    
    # Add to history
    history = read_history()
    history.insert(0, page)  # Add to the beginning of history
    write_history(history)
    return jsonify(page), 201

@app.route('/api/history/frequent', methods=['GET'])
def get_frequent_pages():
    frequency = read_frequency()
    # Convert to list of pages
    frequent_pages = []
    
    for url, data in frequency.items():
        if data.get('title', url) != 'WebHistoryFrontend':
            frequent_pages.append({
                'id': str(uuid.uuid4()),  # Generate a new ID for this view
                'url': url,
                'title': data.get('title', url),
                'favicon': data.get('favicon', ''),
                'visitCount': data.get('count', 0),
                'timestamp': datetime.now().isoformat()  # Use current time as timestamp
        })
    
    # Sort by visit count, descending
    frequent_pages.sort(key=lambda x: x['visitCount'], reverse=True)
    return jsonify(frequent_pages)

# Routes for folders
@app.route('/api/folders', methods=['GET'])
def get_folders():
    folders = read_folders()
    # Convert datetime objects to strings for JSON serialization
    for folder in folders:
        for page in folder['pages']:
            if 'timestamp' in page and isinstance(page['timestamp'], datetime):
                page['timestamp'] = page['timestamp'].isoformat()
    return jsonify(folders)

@app.route('/api/folders', methods=['POST'])
def create_folder():
    folder = request.json
    if 'id' not in folder:
        folder['id'] = str(uuid.uuid4())
    if 'pages' not in folder:
        folder['pages'] = []
    
    folders = read_folders()
    folders.append(folder)
    write_folders(folders)
    return jsonify(folder), 201

@app.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    folders = read_folders()
    folders = [f for f in folders if f['id'] != folder_id]
    write_folders(folders)
    return '', 204

@app.route('/api/folders/<folder_id>/pages', methods=['POST'])
def add_page_to_folder(folder_id):
    page = request.json
    if 'id' not in page:
        page['id'] = str(uuid.uuid4())
    if 'timestamp' not in page:
        page['timestamp'] = datetime.now().isoformat()
    
    # Check if this URL already exists in the folder
    folders = read_folders()
    target_folder = None
    for folder in folders:
        if folder['id'] == folder_id:
            target_folder = folder
            break
    
    if target_folder:
        # Check if URL already exists
        url_exists = any(p['url'] == page['url'] for p in target_folder['pages'])
        
        if not url_exists:
            target_folder['pages'].append(page)
            write_folders(folders)
            return jsonify(page), 201
        else:
            return jsonify({"error": "URL already exists in folder"}), 409
    
    return jsonify({"error": "Folder not found"}), 404

@app.route('/api/folders/<folder_id>/pages/<page_id>', methods=['POST'])
def move_page_to_folder(folder_id, page_id):
    # Find page in history or other folders
    page = None
    
    # Check history
    history = read_history()
    new_history = []
    for p in history:
        if p['id'] == page_id:
            page = p
        else:
            new_history.append(p)
    
    # If not found in history, check folders
    if not page:
        folders = read_folders()
        source_folder = None
        for folder in folders:
            new_pages = []
            for p in folder['pages']:
                if p['id'] == page_id:
                    page = p
                    source_folder = folder
                else:
                    new_pages.append(p)
            if source_folder:
                source_folder['pages'] = new_pages
                break
    
    # Add to target folder if found and not duplicate
    if page:
        folders = read_folders()
        target_folder = None
        for folder in folders:
            if folder['id'] == folder_id:
                target_folder = folder
                break
        
        if target_folder:
            # Check if URL already exists in target folder
            url_exists = any(p['url'] == page['url'] for p in target_folder['pages'])
            
            if not url_exists:
                target_folder['pages'].append(page)
                
                # Update history if page was from there
                if page in history:
                    write_history(new_history)
                
                write_folders(folders)
                return jsonify(page), 200
            else:
                return jsonify({"error": "URL already exists in folder"}), 409
    
    return jsonify({"error": "Page not found"}), 404

@app.route('/api/folders/<folder_id>/pages/<page_id>', methods=['DELETE'])
def remove_page_from_folder(folder_id, page_id):
    folders = read_folders()
    for folder in folders:
        if folder['id'] == folder_id:
            folder['pages'] = [p for p in folder['pages'] if p['id'] != page_id]
            break
    
    write_folders(folders)
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)