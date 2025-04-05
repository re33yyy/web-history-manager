# Web History Manager Firefox Extension

This Firefox extension integrates with your Web History Manager application, allowing you to capture browsing history and organize web pages into custom folders directly from your browser.

## Features

1. **Automatic History Tracking**
   - Captures pages you visit and sends them to your Web History Manager backend
   - Maintains your browsing privacy with pause/resume functionality
   - Respects Firefox's privacy policy

2. **Quick Access to Folders**
   - Popup interface shows all your folders
   - Add current page to any folder with one click
   - Right-click context menu for quick saving

3. **Smart Folder Management**
   - Create new folders directly from the extension
   - Recently used folders for quick access
   - Avoid duplicates with collision detection

4. **User-Friendly Interface**
   - Firefox-styled UI that looks native to the browser
   - Success/error notifications
   - Keyboard shortcuts for power users

## Installation

### Temporary Installation (for Development)

1. Open Firefox and navigate to `about:debugging`
2. Click "This Firefox" in the sidebar
3. Click "Load Temporary Add-on..."
4. Navigate to your extension folder and select `manifest.json`
5. The extension will be installed temporarily (until Firefox restarts)

### Permanent Installation

For permanent installation, the extension needs to be signed by Mozilla:

1. Package the extension files into a ZIP archive
2. Create a developer account on [Mozilla Add-ons](https://addons.mozilla.org/developers/)
3. Submit the extension for review
4. Once approved, it can be installed from Mozilla Add-ons

## Directory Structure

```
web-history-extension-firefox/
├── manifest.json         # Extension configuration
├── background.js         # Background script
├── popup.html            # Main popup interface
├── popup.js              # Popup functionality
├── content-script.js     # Web page integration
├── folder-create.html    # New folder creation interface
├── folder-create.js      # New folder creation logic
└── icons/                # Extension icons
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Using the Extension

### Viewing History and Folders

1. Click the Web History Manager extension icon in the toolbar
2. Your current page will be displayed at the top
3. Below that, you'll see a list of your folders
4. Recent folders appear at the bottom for quick access

### Adding Pages to Folders

1. **From the Popup**:
   - Click the extension icon
   - Find the folder you want to add the page to
   - Click the "Add" button

2. **From the Context Menu**:
   - Right-click anywhere on a webpage
   - Select "Add to Web History Folder"
   - Choose a folder from the list

3. **For Links**:
   - Right-click on any link
   - Select "Add to Web History Folder" 
   - Choose a folder from the list

### Creating New Folders

1. **From the Popup**:
   - Click the extension icon
   - Click the "+ New Folder" button
   - Enter a name and click "Create"

2. **From the Context Menu**:
   - Right-click on a page or link
   - Select "Add to Web History Folder" 
   - Click "➕ Create New Folder..."

### Privacy Controls

1. Click the extension icon in the toolbar
2. Click "Pause Capture" to temporarily stop tracking browsing history
3. Click "Resume Capture" when you want to start tracking again

### Keyboard Shortcuts

- `Alt+S` - Open the extension popup for quick access

## Configuration

The extension is configured to connect to your backend API at `http://localhost:5000/api`. 
If your backend is running at a different location, you'll need to modify the `API_URL` 
variable in the following files:

- `background.js`
- `popup.js`

## Firefox-Specific Differences from Chrome

- Uses `browser.*` APIs instead of `chrome.*`
- Manifest V2 format (Firefox hasn't fully adopted Manifest V3)
- Includes Firefox-specific styling for better integration
- Contains `browser_specific_settings` in manifest.json
- Uses asynchronous Promise-based API calls rather than callbacks

## Troubleshooting

1. **Extension doesn't appear in toolbar**
   - Check if the extension is installed in `about:addons`
   - Click the menu button (☰) and select "Customize Toolbar"
   - Find the Web History Manager icon and drag it to your toolbar

2. **Pages aren't being tracked**
   - Check if tracking is paused
   - Verify the backend API is running
   - Check Firefox's console for errors (Ctrl+Shift+J)

3. **Can't add pages to folders**
   - Make sure the backend is accessible
   - Check for network errors in the console
   - Verify folder exists in Web History Manager

4. **Context menu doesn't appear**
   - Restart Firefox
   - Reinstall the extension
   - Ensure the extension has proper permissions

## Future Enhancements

- Additional keyboard shortcuts
- Dark theme support
- Custom tagging system
- Search functionality
- Sync with Firefox's built-in history
- Support for Firefox Mobile
