  // background.js
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
          favicon: tab.favIconUrl || 'default-favicon.png',
          timestamp: new Date().toISOString()
        };
        
        // Send to our backend API
        fetch('http://localhost:5000/api/history', {
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
        
        // Also send a message to any open instances of our app
        chrome.runtime.sendMessage({
          type: 'NEW_PAGE_VISIT',
          page: pageVisit
        });
      }
    }
  });
