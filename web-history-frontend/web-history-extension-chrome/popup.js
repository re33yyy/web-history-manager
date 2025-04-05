// Backend API URL
const API_URL = 'http://localhost:5000/api';

// DOM Elements
const pageTitle = document.getElementById('pageTitle');
const pageUrl = document.getElementById('pageUrl');
const folderList = document.getElementById('folderList');
const newFolderBtn = document.getElementById('newFolderBtn');
const newFolderForm = document.getElementById('newFolderForm');
const folderNameInput = document.getElementById('folderNameInput');
const saveFolderBtn = document.getElementById('saveFolderBtn');
const cancelFolderBtn = document.getElementById('cancelFolderBtn');
const notification = document.getElementById('notification');
const captureBtnToggle = document.getElementById('captureBtnToggle');
const recentFolderList = document.getElementById('recentFolderList');

// Current page data
let currentPage = {
  url: '',
  title: '',
  favicon: ''
};

// Tracking state
let captureEnabled = true;

// Recent folders
let recentFolders = [];

// Initialize popup
document.addEventListener('DOMContentLoaded', function() {
  // Get current tab info
  getCurrentTab();
  
  // Load folders
  loadFolders();
  
  // Load recent folders from storage
  loadRecentFolders();
  
  // Load capture state
  loadCaptureState();
  
  // Set up event listeners
  setupEventListeners();
});

// Get current tab information
function getCurrentTab() {
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    if (tabs.length > 0) {
      const tab = tabs[0];
      currentPage = {
        id: Date.now().toString(),
        url: tab.url,
        title: tab.title || tab.url,
        favicon: tab.favIconUrl || 'icons/default-favicon.png',
        timestamp: new Date().toISOString()
      };
      
      // Update UI
      pageTitle.textContent = currentPage.title;
      pageUrl.textContent = currentPage.url;
    }
  });
}

// Load folders from backend
function loadFolders() {
  fetch(`${API_URL}/folders`)
    .then(response => response.json())
    .then(folders => {
      if (folders.length === 0) {
        folderList.innerHTML = `
          <div class="folder-item">
            <span class="folder-name">No folders yet. Create one!</span>
          </div>
        `;
        return;
      }
      
      folderList.innerHTML = '';
      folders.forEach(folder => {
        const folderItem = document.createElement('div');
        folderItem.className = 'folder-item';
        folderItem.innerHTML = `
          <span class="folder-name">${folder.name}</span>
          <button class="add-button">Add</button>
        `;
        
        // Add click handler for the Add button
        const addButton = folderItem.querySelector('.add-button');
        addButton.addEventListener('click', () => {
          addToFolder(folder.id, folder.name);
        });
        
        folderList.appendChild(folderItem);
      });
    })
    .catch(error => {
      console.error('Error loading folders:', error);
      folderList.innerHTML = `
        <div class="folder-item">
          <span class="folder-name">Error loading folders. Please try again.</span>
        </div>
      `;
    });
}

// Add current page to folder
function addToFolder(folderId, folderName) {
  fetch(`${API_URL}/folders/${folderId}/pages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(currentPage)
  })
  .then(response => {
    if (response.status === 409) {
      showNotification('This page already exists in the selected folder.', 'error');
      return null;
    }
    return response.json();
  })
  .then(data => {
    if (data) {
      showNotification(`Page added to "${folderName}" folder.`, 'success');
      
      // Add to recent folders
      addToRecentFolders({
        id: folderId,
        name: folderName
      });
    }
  })
  .catch(error => {
    console.error('Error adding page to folder:', error);
    showNotification('Failed to add page to folder. Please try again.', 'error');
  });
}

// Set up event listeners
function setupEventListeners() {
  // New folder button
  newFolderBtn.addEventListener('click', () => {
    newFolderForm.classList.add('visible');
    folderNameInput.focus();
  });
  
  // Save folder button
  saveFolderBtn.addEventListener('click', createNewFolder);
  
  // Folder name input enter key
  folderNameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      createNewFolder();
    }
  });
  
  // Cancel folder button
  cancelFolderBtn.addEventListener('click', () => {
    newFolderForm.classList.remove('visible');
    folderNameInput.value = '';
  });
  
  // Capture toggle button
  captureBtnToggle.addEventListener('click', toggleCapture);
}

// Create a new folder
function createNewFolder() {
  const folderName = folderNameInput.value.trim();
  
  if (!folderName) {
    showNotification('Folder name cannot be empty.', 'error');
    return;
  }
  
  // Send message to background script to create folder
  chrome.runtime.sendMessage(
    {
      action: 'createFolder',
      folderName: folderName
    },
    (response) => {
      if (response.success) {
        showNotification(`Folder "${folderName}" created.`, 'success');
        folderNameInput.value = '';
        newFolderForm.classList.remove('visible');
        
        // Reload folders
        loadFolders();
        
        // Add to recent folders
        addToRecentFolders({
          id: response.folder.id,
          name: folderName
        });
      } else {
        showNotification('Failed to create folder. Please try again.', 'error');
      }
    }
  );
}

// Show notification
function showNotification(message, type) {
  notification.textContent = message;
  notification.className = 'notification';
  notification.classList.add(type);
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    notification.className = 'notification';
  }, 5000);
}

// Toggle history capture
function toggleCapture() {
  captureEnabled = !captureEnabled;
  
  if (captureEnabled) {
    captureBtnToggle.textContent = 'Pause Capture';
    showNotification('Page capture enabled.', 'success');
  } else {
    captureBtnToggle.textContent = 'Resume Capture';
    showNotification('Page capture paused.', 'success');
  }
  
  // Save state to storage
  chrome.storage.local.set({ captureEnabled: captureEnabled });
}

// Load capture state from storage
function loadCaptureState() {
  chrome.storage.local.get('captureEnabled', (result) => {
    if (result.hasOwnProperty('captureEnabled')) {
      captureEnabled = result.captureEnabled;
      
      if (captureEnabled) {
        captureBtnToggle.textContent = 'Pause Capture';
      } else {
        captureBtnToggle.textContent = 'Resume Capture';
      }
    }
  });
}

// Add to recent folders
function addToRecentFolders(folder) {
  // Check if folder is already in the list
  const existingIndex = recentFolders.findIndex(f => f.id === folder.id);
  
  if (existingIndex !== -1) {
    // Remove from current position
    recentFolders.splice(existingIndex, 1);
  }
  
  // Add to the beginning of the list
  recentFolders.unshift(folder);
  
  // Limit to 5 recent folders
  if (recentFolders.length > 5) {
    recentFolders = recentFolders.slice(0, 5);
  }
  
  // Save to storage
  chrome.storage.local.set({ recentFolders: recentFolders });
  
  // Update UI
  updateRecentFoldersUI();
}

// Load recent folders from storage
function loadRecentFolders() {
  chrome.storage.local.get('recentFolders', (result) => {
    if (result.recentFolders && Array.isArray(result.recentFolders)) {
      recentFolders = result.recentFolders;
      updateRecentFoldersUI();
    }
  });
}

// Update recent folders UI
function updateRecentFoldersUI() {
  if (recentFolders.length === 0) {
    document.getElementById('recentFolders').style.display = 'none';
    return;
  }
  
  document.getElementById('recentFolders').style.display = 'block';
  recentFolderList.innerHTML = '';
  
  recentFolders.forEach(folder => {
    const folderItem = document.createElement('div');
    folderItem.className = 'recent-folder-item';
    folderItem.textContent = folder.name;
    
    folderItem.addEventListener('click', () => {
      addToFolder(folder.id, folder.name);
    });
    
    recentFolderList.appendChild(folderItem);
  });
}