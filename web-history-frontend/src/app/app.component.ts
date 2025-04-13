import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CdkDragDrop, moveItemInArray, transferArrayItem } from '@angular/cdk/drag-drop';
import { NgIf, NgFor } from '@angular/common';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DragDropModule } from '@angular/cdk/drag-drop';

interface WebPage {
  page_id: string;
  url: string;
  title: string;
  // favicon: string;
  timestamp: Date;
  visitCount?: number;
}

interface Folder {
  id: string;
  name: string;
  pages: WebPage[];
  isCollapsed?: boolean; // Property to track collapse state
  isEditing?: boolean; // Property to track editing state
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  standalone: true,
  imports: [NgIf, NgFor, CommonModule, FormsModule, DragDropModule ]
})
export class AppComponent implements OnInit {
  history: WebPage[] = [];
  frequentPages: WebPage[] = [];
  folders: Folder[] = [];
  newFolderName: string = '';
  isCreatingFolder: boolean = false;
  currentUrl: string = '';
  activeTab: 'history' | 'frequent' = 'history';
  editingFolderName: string = '';
  
  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadHistory();
    this.loadFrequentPages();
    this.loadFolders();
    this.getCurrentTab();
    
    // Set up listener for browser history updates
    window.addEventListener('message', (event) => {
      if (event.data.type === 'NEW_PAGE_VISIT') {
        this.history.unshift(event.data.page);
        this.loadFrequentPages(); // Reload frequent pages when a new page is visited
      }
    });
  }

  get connectedDropLists(): string[] {
    return [
      'history',
      'frequent',
      ...this.folders.map(f => 'folder-' + f.id)
    ];
  }

  get folderDropListIds(): string[] {
    return this.folders.map(f => 'folder-' + f.id);
  }
    
  loadHistory() {
    console.log("loadHistory()")
    const timestamp = new Date().getTime();
    this.http.get<WebPage[]>(`http://localhost:5000/api/history?t=${timestamp}`).subscribe(
      (data) => {
        this.history = data;
      },
      (error) => {
        console.error('Error loading history:', error);
      }
    );
  }

  loadFrequentPages() {
    console.log("loadFrequentPages()")
    const timestamp = new Date().getTime();
    this.http.get<WebPage[]>(`http://localhost:5000/api/history/frequent?t=${timestamp}`).subscribe(
      (data) => {
        this.frequentPages = data;
      },
      (error) => {
        console.error('Error loading frequent pages:', error);
      }
    );
  }

  loadFolders() {
    console.log("loadFolders()")
    const timestamp = new Date().getTime();
    this.http.get<Folder[]>(`http://localhost:5000/api/folders?t=${timestamp}`).subscribe(
      (data) => {
        // Initialize collapse state for each folder
        data.forEach(folder => {
          folder.isCollapsed = folder.isCollapsed || false;
        });
        this.folders = data;
      },
      (error) => {
        console.error('Error loading folders:', error);
      }
    );
  }

  getCurrentTab() {
    // This would use browser extension API in a real implementation
    // For demo purposes, we'll simulate with a placeholder URL
    this.currentUrl = 'https://example.com/current-page';
  }

  createFolder() {
    if (this.newFolderName.trim() === '') return;
    
    const newFolder: Folder = {
      id: Date.now().toString(),
      name: this.newFolderName,
      pages: [],
      isCollapsed: false
    };
    
    this.http.post<Folder>('http://localhost:5000/api/folders', newFolder).subscribe(
      (response) => {
        this.folders.push(response);
        this.newFolderName = '';
        this.isCreatingFolder = false;
      },
      (error) => {
        console.error('Error creating folder:', error);
      }
    );
  }

  deleteFolder(folderId: string) {
    this.http.delete(`http://localhost:5000/api/folders/${folderId}`).subscribe(
      () => {
        this.folders = this.folders.filter(folder => folder.id !== folderId);
      },
      (error) => {
        console.error('Error deleting folder:', error);
      }
    );
  }

  // Toggle folder collapse state
  toggleFolderCollapse(folder: Folder) {
    folder.isCollapsed = !folder.isCollapsed;
    // Save collapsed state to backend
    this.updateFolderOrder();
  }
  
  // Start renaming a folder
  startEditingFolder(folder: Folder, event: Event) {
    event.stopPropagation(); // Prevent event bubbling to other handlers
    
    // Close any other folder that might be in edit mode
    this.folders.forEach(f => {
      if (f !== folder) f.isEditing = false;
    });
    
    // Set the current folder to edit mode
    folder.isEditing = true;
    this.editingFolderName = folder.name;
  }
  
  // Save the new folder name
  saveEditedFolderName(folder: Folder) {
    // Trim whitespace
    const newName = this.editingFolderName.trim();
    
    // Check if name is empty
    if (newName === '') {
      alert('Folder name cannot be empty');
      return;
    }
    
    // Check for name collision
    const nameExists = this.folders.some(f => 
      f.id !== folder.id && f.name.toLowerCase() === newName.toLowerCase()
    );
    
    if (nameExists) {
      alert('A folder with this name already exists');
      return;
    }
    
    // Save the new name
    const oldName = folder.name;
    folder.name = newName;
    folder.isEditing = false;
    
    // Update on backend
    this.http.post(`http://localhost:5000/api/folders/${folder.id}/rename`, { name: newName }).subscribe(
      () => {
        console.log('Folder renamed successfully');
      },
      (error) => {
        console.error('Error renaming folder:', error);
        // Revert the name on error
        folder.name = oldName;
      }
    );
  }
  
  // Cancel renaming
  cancelFolderEdit(folder: Folder) {
    folder.isEditing = false;
  }

  // New method to update folder order after reordering
  updateFolderOrder() {
    this.http.post('http://localhost:5000/api/folders/reorder', this.folders).subscribe(
      () => {
        console.log('Folder order updated successfully');
      },
      (error) => {
        console.error('Error updating folder order:', error);
      }
    );
  }

  // Modified method to handle folder reordering
  onFolderDrop(event: CdkDragDrop<Folder[]>) {
    moveItemInArray(this.folders, event.previousIndex, event.currentIndex);
    this.updateFolderOrder();
  }

  updateFolderPageOrder(folderId: string, pages: WebPage[]) {
    this.http.post(`/api/folders/${folderId}/pages/reorder`, pages).subscribe(
      () => {
        console.log('Folder page order saved.');
      },
      (error) => {
        console.error('Failed to save page order:', error);
      }
    );
  }

  onDrop(event: CdkDragDrop<WebPage[]>) {
    console.log('Drop event detected:', event);
    
    if (event.previousContainer === event.container) {
      // Reordering within the same container
      console.log('Reordering within same container:', event.container.id);
      moveItemInArray(
        event.container.data,
        event.previousIndex,
        event.currentIndex
      );
      if (event.container.id.startsWith('folder-')) {
        const folderId = event.container.id.replace('folder-', '');
        console.log('Updating page order for folder:', folderId);
        const folder = this.folders.find(f => f.id === folderId);
        if (folder) {
          this.updateFolderPageOrder(folderId, folder.pages);
        }
      }
    } else {
      // Get the page being moved before we modify the arrays
      const page = {...event.previousContainer.data[event.previousIndex]};
      console.log('Moving page between containers:', page);
      console.log('Page ID:', page.page_id);
      
      // Check if we're moving FROM a folder TO a non-folder (removing from folder)
      if (event.previousContainer.id.startsWith('folder-') && 
          !event.container.id.startsWith('folder-')) {
        
        // First complete the UI operation
        transferArrayItem(
          event.previousContainer.data,
          event.container.data,
          event.previousIndex,
          event.currentIndex
        );
        
        // Then sync with backend
        const folderId = event.previousContainer.id.replace('folder-', '');
        console.log(`Removing page with ID ${page.page_id} from folder ${folderId}`);
        
        this.http.delete(`/api/folders/${folderId}/pages/${page.page_id}`).subscribe(
          () => {
            console.log('Page removed from folder successfully');
            this.refreshData();
          },
          (error) => {
            console.error('Error removing page from folder:', error);
            console.log('Page details:', JSON.stringify(page));
          }
        );
      } 
      // Moving item from one container to another folder
      else if (event.container.id.startsWith('folder-')) {
        // We're dropping into a folder - check if this URL already exists in the folder
        const folderId = event.container.id.replace('folder-', '');
        const folder = this.folders.find(f => f.id === folderId);
        console.log('Target folder:', folder);
        console.log('Adding page to folder:', folderId);
        
        // Check if the page URL already exists in the folder
        const urlExists = folder?.pages.some(p => p.url === page.url);
        console.log('URL already exists in folder?', urlExists);
        
        if (!urlExists) {
          // First complete the UI operation
          transferArrayItem(
            event.previousContainer.data,
            event.container.data,
            event.previousIndex,
            event.currentIndex
          );
          
          // Don't use source container ID as page ID
          const sourceType = event.previousContainer.id;
          console.log('Source container type:', sourceType);
          
          if (sourceType === 'history' || sourceType === 'frequent') {
            // When moving from history or frequent lists, add page as new
            console.log('Adding new page to folder with data:', JSON.stringify(page));
            
            this.http.post(`/api/folders/${folderId}/pages`, page).subscribe(
              (response) => {
                console.log('Page added to folder successfully:', response);
                this.refreshData();
              },
              (error) => {
                console.error('Error adding page to folder:', error);
                // Revert UI change on error
                event.container.data.splice(event.currentIndex, 1);
                event.previousContainer.data.splice(event.previousIndex, 0, page);
              }
            );
          } else if (sourceType.startsWith('folder-')) {
            // When moving between folders, use page ID
            const sourceFolderId = sourceType.replace('folder-', '');
            console.log(`Moving page with ID ${page.page_id} from folder ${sourceFolderId} to folder ${folderId}`);
            
            // Use alternative remove-page endpoint first
            this.http.post(`/api/folders/${sourceFolderId}/remove-page`, {
              pageId: page.page_id
            }).subscribe(
              () => {
                console.log('Removed from source folder successfully');
                
                // Then add to target folder
                this.http.post(`/api/folders/${folderId}/pages`, page).subscribe(
                  (response) => {
                    console.log('Added to target folder successfully:', response);
                    this.refreshData();
                  },
                  (error) => {
                    console.error('Error adding to target folder:', error);
                    // Try to revert UI change on error
                    this.refreshData();
                  }
                );
              },
              (error) => {
                console.error('Error removing from source folder:', error);
                // Revert UI change on error
                this.refreshData();
              }
            );
          }
        } else {
          // URL already exists in folder, just remove from source without adding to destination
          event.previousContainer.data.splice(event.previousIndex, 1);
          
          // Notify user
          alert('This URL already exists in the folder. Duplicate not added.');
        }
      } else {
        // Not dropping into a folder, perform normal transfer
        console.log('Normal transfer between non-folder containers');
        transferArrayItem(
          event.previousContainer.data,
          event.container.data,
          event.previousIndex,
          event.currentIndex
        );
      }
    }
  }
    
  addCurrentPageToFolder(folderId: string) {
    // This would get the current page from the browser in a real implementation
    // Skip if we're using the example URL
    if (this.currentUrl === 'https://example.com/current-page') {
      alert('Cannot add example page. This feature requires the browser extension.');
      return;
    }
    const currentPage: WebPage = {
      page_id: Date.now().toString(),
      url: this.currentUrl,
      title: 'Current Page',
      //favicon: 'favicon.ico',
      timestamp: new Date()
    };
    
    // Check if this URL already exists in the folder
    const folder = this.folders.find(f => f.id === folderId);
    const urlExists = folder?.pages.some(p => p.url === currentPage.url);
    
    if (!urlExists) {
      this.http.post(`http://localhost:5000/api/folders/${folderId}/pages`, currentPage).subscribe(
        (response: any) => {
          if (folder) {
            folder.pages.push(response);
          }
        },
        (error) => {
          console.error('Error adding current page to folder:', error);
        }
      );
    } else {
      alert('This URL already exists in the folder. Duplicate not added.');
    }
  }
  
  setActiveTab(tab: 'history' | 'frequent') {
    this.activeTab = tab;
  }

  refreshData() {
    this.loadHistory();
    this.loadFrequentPages();
    this.loadFolders();
  }  

  extractDomain(url: string): string {
    try {
      const parsed = new URL(url);
      return parsed.hostname + parsed.pathname;
    } catch {
      return url;
    }
  }
  
  formatTooltip(page: WebPage): string {
    return `${page.title || page.url}\nLast visited: ${page.timestamp || 'N/A'}\nVisits: ${page.visitCount || 0}`;
  }  

  exportBookmarks() {
    const link = document.createElement('a');
    link.href = '/api/export-bookmarks';
    link.download = 'webhistory_bookmarks.html';
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  removePage(folderId: string, pageId: string) {
    // Find the folder
    const folder = this.folders.find(f => f.id === folderId);
    if (!folder) return;

    // Call API to remove the page
    this.http.delete(`/api/folders/${folderId}/pages/${pageId}`).subscribe(
      () => {
        console.log('Page removed successfully');
        
        // Remove page from local state
        if (folder) {
          folder.pages = folder.pages.filter(p => p.page_id !== pageId);
        }
      },
      (error) => {
        console.error('Error removing page:', error);
      }
    );
  }
}