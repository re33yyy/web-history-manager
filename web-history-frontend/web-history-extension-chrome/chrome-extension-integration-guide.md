# Web History Manager Chrome Extension

This Chrome extension integrates with your Web History Manager application, allowing you to easily capture browsing history and organize pages into folders directly from your browser.

## Features

1. **Automatic History Capture**: Tracks pages you visit and sends them to your Web History Manager
2. **Quick Folder Access**: Add the current page to any folder with just two clicks
3. **Context Menu Integration**: Right-click on any page or link to add it to a folder
4. **Folder Management**: Create new folders directly from the extension
5. **Recently Used Folders**: Quick access to your most frequently used folders
6. **Pause/Resume Tracking**: Toggle history tracking on and off as needed

## Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" using the toggle in the top-right corner
3. Click "Load unpacked" and select the extension directory
4. The Web History Manager icon should appear in your browser toolbar

## Directory Structure

```
web-history-extension/
├── manifest.json       # Extension configuration
├── background.js       # Background script for tracking and context menus
├── popup.html          # Extension popup interface
├── popup.js            # Popup functionality
├── content-script.js   # Page content integration
└── icons/              # Extension icons
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Using the Extension

### Adding Pages to Folders

1. **Using the Popup**:
   - Click the extension icon in the toolbar
   - Select a folder from the list
   - Click "Add" to add the current page

2. **Using the Context Menu**:
   - Right-click anywhere on a webpage
   - Select "Add to Web History Folder"
   - Choose a folder from the submenu

3. **For Links**:
   - Right-click on any link
   - Select "Add to Web History Folder"
   - Choose a folder from the submenu

### Creating New Folders

1. Click the extension icon in the toolbar
2. Click "+ New Folder"
3. Enter the folder name and click "Create"

### Managing History Tracking

- Click the extension icon in the toolbar
- Click "Pause Capture" to temporarily stop tracking
- Click "Resume Capture" to start tracking again

### Opening the Web History Manager

- Click the extension icon in the toolbar
- Click "Open Manager" to launch the full Web History Manager application

## Integration Details

The extension communicates with your Flask backend API to:

1. Record page visits
2. Retrieve folder lists
3. Add pages to folders
4. Create new folders

## Configuration

Edit the `API_URL` variable in both `background.js` and `popup.js` if your backend is not running at `http://localhost:5000/api`.

## Security Considerations

- The extension only tracks pages with HTTP or HTTPS protocols
- Chrome extensions have limited cross-origin capabilities, so the backend must use CORS
- Tracking can be paused at any time for privacy

## Troubleshooting

1. **Pages aren't being tracked**:
   - Check if tracking is paused (the popup button will say "Resume Capture")
   - Verify the backend API is running
   - Check browser console for errors

2. **Can't add pages to folders**:
   - Ensure the backend API is accessible
   - Check for network errors in the browser console
   - Verify the folder exists in the Web History Manager

3. **Context menu doesn't appear**:
   - Restart the browser
   - Reinstall the extension
   - Ensure the extension has the "contextMenus" permission

## Future Enhancements

- Keyboard shortcuts for quick folder access
- Customizable tracking settings
- Tagging support for pages
- Dark mode support
- Syncing with the browser's built-in history