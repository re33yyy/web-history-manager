// dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';

interface Article {
  id: string;
  title: string;
  url: string;
  summary: string;
  published_date: string;
  crawled_date: string;
  is_read: boolean;
}

interface Site {
  id: string;
  name: string;
  url: string;
}

interface SiteContent {
  site: Site;
  articles: Article[];
  isCollapsed?: boolean; // Added property for collapsible sections
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  dashboardData: SiteContent[] = [];
  isLoading: boolean = true;
  errorMessage: string = '';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadDashboard();
  }

  loadDashboard() {
    this.isLoading = true;
    this.errorMessage = '';

    this.http.get<SiteContent[]>('/api/dashboard').subscribe(
      (data) => {
        // Initialize collapse state for each site
        data.forEach(siteContent => {
          // Default to expanded (not collapsed)
          siteContent.isCollapsed = false;
        });
        
        this.dashboardData = data;
        this.isLoading = false;
        
        // Load saved collapse states from localStorage
        this.loadSiteCollapseState();
      },
      (error) => {
        console.error('Error loading dashboard:', error);
        this.errorMessage = 'Failed to load dashboard data. Please try again later.';
        this.isLoading = false;
      }
    );
  }

  // Toggle site collapse state
  toggleSiteCollapse(siteContent: SiteContent, event: MouseEvent) {
    // Prevent the event from triggering link clicks
    event.preventDefault();
    event.stopPropagation();
    
    // Toggle the collapsed state
    siteContent.isCollapsed = !siteContent.isCollapsed;
    
    // Save the state to localStorage
    this.saveSiteCollapseState();
  }

  // Method to save collapse state to localStorage
  saveSiteCollapseState() {
    // Create a map of site IDs to collapse states
    const collapseStates = this.dashboardData.reduce((states, siteContent) => {
      states[siteContent.site.id] = siteContent.isCollapsed || false;
      return states;
    }, {} as {[key: string]: boolean});
    
    // Save to localStorage
    localStorage.setItem('dashboardCollapseStates', JSON.stringify(collapseStates));
  }

  // Method to load collapse state from localStorage
  loadSiteCollapseState() {
    const savedStates = localStorage.getItem('dashboardCollapseStates');
    if (savedStates) {
      try {
        const states = JSON.parse(savedStates) as {[key: string]: boolean};
        
        // Apply saved states to dashboard data
        this.dashboardData.forEach(siteContent => {
          if (states[siteContent.site.id] !== undefined) {
            siteContent.isCollapsed = states[siteContent.site.id];
          }
        });
      } catch (e) {
        console.error('Error loading saved collapse states:', e);
      }
    }
  }

  markAsRead(articleId: string) {
    // First update the UI immediately for better user experience
    this.dashboardData.forEach(siteContent => {
      const article = siteContent.articles.find(a => a.id === articleId);
      if (article) {
        article.is_read = true;
      }
    });
    
    // Then send the request to the server
    this.http.post(`/api/articles/${articleId}/mark-read`, {}).subscribe(
      () => {
        console.log(`Article ${articleId} marked as read`);
      },
      (error) => {
        console.error('Error marking article as read:', error);
        // Revert the UI change if the server request fails
        this.dashboardData.forEach(siteContent => {
          const article = siteContent.articles.find(a => a.id === articleId);
          if (article) {
            article.is_read = false;
          }
        });
      }
    );
  }

  triggerCrawl() {
    this.isLoading = true;
    this.errorMessage = '';

    this.http.post('/api/crawl/trigger', {}).subscribe(
      () => {
        this.loadDashboard();
      },
      (error) => {
        console.error('Error triggering crawl:', error);
        this.errorMessage = 'Failed to trigger crawl. Please try again later.';
        this.isLoading = false;
      }
    );
  }

  formatDate(dateString: string): string {
    if (!dateString) return '';
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (e) {
      return dateString;
    }
  }

  refreshContent() {
    this.isLoading = true;
    this.errorMessage = '';
    
    this.http.post('/api/crawl/trigger', {}).subscribe(
      (response) => {
        console.log('Refresh triggered successfully:', response);
        // Wait a moment for the crawler to complete
        setTimeout(() => {
          this.loadDashboard();
        }, 1000);
      },
      (error) => {
        console.error('Error triggering refresh:', error);
        this.errorMessage = 'Failed to refresh content. Please try again.';
        this.isLoading = false;
      }
    );
  }
}