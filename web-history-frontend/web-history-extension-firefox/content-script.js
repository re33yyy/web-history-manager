// This script runs in the context of the web page

// Check if we should capture this page
browser.storage.local.get('captureEnabled').then(result => {
  const captureEnabled = result.hasOwnProperty('captureEnabled') ? result.captureEnabled : true;
  
  if (captureEnabled) {
    // Get page information
    const pageData = {
      url: window.location.href,
      title: document.title,
      favicon: getFaviconUrl(),
      timestamp: new Date().toISOString()
    };
    
    // Check if we're on the history manager app
    if (!document.title.includes('WebHistoryFrontend')) {
      // Send to background script
      browser.runtime.sendMessage({
        type: 'PAGE_VISIT',
        page: pageData
      });
    }
  }
});

// Function to get the favicon URL
function getFaviconUrl() {
  // Try to find favicon from link tags
  const linkTags = document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]');
  
  if (linkTags.length > 0) {
    // Get the href attribute of the first matching link tag
    const faviconHref = linkTags[0].getAttribute('href');
    
    // If href is absolute URL, return as is
    if (faviconHref.startsWith('http://') || faviconHref.startsWith('https://')) {
      return faviconHref;
    }
    
    // Otherwise, convert to absolute URL
    return new URL(faviconHref, window.location.origin).href;
  }
  
  // Default to site favicon
  return window.location.origin + '/favicon.ico';
}

// Add keyboard shortcut support for quick saving
document.addEventListener('keydown', (event) => {
  // Alt+S to open the save dialog
  if (event.altKey && event.key === 's') {
    browser.runtime.sendMessage({ action: 'openPopup' });
  }
});

// Listen for the context menu selection for adding the current selection to a note
document.addEventListener('mouseup', (event) => {
  const selection = window.getSelection().toString().trim();
  
  if (selection) {
    // Store the selected text temporarily
    browser.storage.local.set({ lastSelection: selection });
  }
});