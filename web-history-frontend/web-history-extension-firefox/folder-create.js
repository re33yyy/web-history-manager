// DOM Elements
const folderNameInput = document.getElementById('folderName');
const errorMessage = document.getElementById('errorMessage');
const createBtn = document.getElementById('createBtn');
const cancelBtn = document.getElementById('cancelBtn');

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
  // Focus on input field
  folderNameInput.focus();
  
  // Set up event listeners
  setupEventListeners();
});

// Set up event listeners
function setupEventListeners() {
  // Create button click
  createBtn.addEventListener('click', createFolder);
  
  // Input enter key
  folderNameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      createFolder();
    }
  });
  
  // Input change (to hide error when typing)
  folderNameInput.addEventListener('input', () => {
    errorMessage.classList.remove('visible');
  });
  
  // Cancel button
  cancelBtn.addEventListener('click', () => {
    window.close();
  });
}

// Create a new folder
function createFolder() {
  const folderName = folderNameInput.value.trim();
  
  if (!folderName) {
    errorMessage.textContent = 'Folder name cannot be empty.';
    errorMessage.classList.add('visible');
    folderNameInput.focus();
    return;
  }
  
  // Send message to background script
  browser.runtime.sendMessage({
    action: 'createFolder',
    folderName: folderName
  }).then(response => {
    if (response.success) {
      // Notify the background script to update the folder menu
      browser.runtime.sendMessage({ action: 'updateFolderMenu' });
      
      // Close the popup
      window.close();
    } else {
      errorMessage.textContent = 'Failed to create folder. Please try again.';
      errorMessage.classList.add('visible');
    }
  }).catch(error => {
    errorMessage.textContent = 'An error occurred. Please try again.';
    errorMessage.classList.add('visible');
    console.error('Error creating folder:', error);
  });
}
