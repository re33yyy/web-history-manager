  document.addEventListener('DOMContentLoaded', function() {
    // Get current tab info
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      const currentTab = tabs[0];
      document.getElementById('current-page').textContent = currentTab.title + ' - ' + currentTab.url;
    });
    
    // Open manager button
    document.getElementById('open-manager').addEventListener('click', function() {
      chrome.tabs.create({url: 'http://localhost:4200'});
    });
  });