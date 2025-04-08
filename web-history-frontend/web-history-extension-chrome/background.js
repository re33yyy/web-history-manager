// Backend API URL
const API_URL = 'http://localhost:5000/api';

// Track page visits and send to our backend
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only capture when the page has fully loaded
  if (changeInfo.status === 'complete' && tab.url) {
    // Filter out extension pages, settings pages, etc.
    if (tab.url.startsWith('http') || tab.url.startsWith('https')) {
      const pageVisit = {
        id: Date.now().toString(),
        url: tab.url,
        title: tab.title || tab.url,
        favicon: tab.favIconUrl || 'asserts/icons/default-favicon.png',
        timestamp: new Date().toISOString()
      };
      
      // Send to our backend API
      fetch(`${API_URL}/history`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(pageVisit)
      })
      .then(response => response.json())
      .then(data => {
        console.log('Page visit recorded:', data);
      })
      .catch(error => {
        console.error('Error recording page visit:', error);
      });
    }
  }
});

// Create context menu items for quick folder access
chrome.runtime.onInstalled.addListener(() => {
  // Create parent menu item
  chrome.contextMenus.create({
    id: 'web-history-manager',
    title: 'Add to Web History Folder',
    contexts: ['page', 'link']
  });
  
  // Load folders and create submenu
  updateFolderMenu();
  
  // Set up periodic refresh of folders list
  setInterval(updateFolderMenu, 60000); // Update folders every minute
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId.startsWith('folder-')) {
    const folderId = info.menuItemId.replace('folder-', '');
    
    // Determine if this is a page or link
    let pageData;
    
    if (info.linkUrl) {
      // This is a link context menu
      pageData = {
        id: Date.now().toString(),
        url: info.linkUrl,
        title: info.linkText || info.linkUrl,
        favicon: 'assets/icons/default-favicon.png',
        timestamp: new Date().toISOString()
      };
    } else {
      // This is a page context menu
      pageData = {
        id: Date.now().toString(),
        url: tab.url,
        title: tab.title || tab.url,
        favicon: tab.favIconUrl || 'assets/icons/default-favicon.png',
        timestamp: new Date().toISOString()
      };
    }
    
    // Add to folder
    addToFolder(folderId, pageData);
  }
});

// Function to update the folder menu
function updateFolderMenu() {
  // Remove existing folder submenus
  chrome.contextMenus.removeAll(() => {
    // Recreate parent menu
    chrome.contextMenus.create({
      id: 'web-history-manager',
      title: 'Add to Web History Folder',
      contexts: ['page', 'link']
    });
    
    // Get folders from backend
    fetch(`${API_URL}/folders`)
      .then(response => response.json())
      .then(folders => {
        // Create submenu items for each folder
        folders.forEach(folder => {
          chrome.contextMenus.create({
            id: `folder-${folder.id}`,
            parentId: 'web-history-manager',
            title: folder.name,
            contexts: ['page', 'link']
          });
        });
        
        // Add option to create new folder
        chrome.contextMenus.create({
          id: 'create-new-folder',
          parentId: 'web-history-manager',
          title: '➕ Create New Folder...',
          contexts: ['page', 'link']
        });
      })
      .catch(error => {
        console.error('Error loading folders for menu:', error);
      });
  });
}

// Function to add a page to a folder
function addToFolder(folderId, pageData) {
  fetch(`${API_URL}/folders/${folderId}/pages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(pageData)
  })
  .then(response => {
    if (response.status === 409) {
      // URL already exists in folder
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Already in Folder',
        message: 'This page already exists in the selected folder.'
      });
      return null;
    }
    return response.json();
  })
  .then(data => {
    if (data) {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Added to Folder',
        message: 'Page successfully added to folder.'
      });
    }
  })
  .catch(error => {
    console.error('Error adding page to folder:', error);
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'Error',
      message: 'Failed to add page to folder. Please try again.'
    });
  });
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'createFolder') {
    // Create a new folder
    const newFolder = {
      name: message.folderName,
      pages: []
    };
    
    fetch(`${API_URL}/folders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(newFolder)
    })
    .then(response => response.json())
    .then(data => {
      // Update folder menu
      updateFolderMenu();
      sendResponse({ success: true, folder: data });
    })
    .catch(error => {
      console.error('Error creating folder:', error);
      sendResponse({ success: false, error: error.toString() });
    });
    
    // Keep the message channel open for async response
    return true;
  }
  
  if (message.action === 'updateFolderMenu') {
    updateFolderMenu();
    sendResponse({ success: true });
    return true;
  }
});