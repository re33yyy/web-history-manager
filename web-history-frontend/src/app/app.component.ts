import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CdkDragDrop, moveItemInArray, transferArrayItem } from '@angular/cdk/drag-drop';
import { NgIf, NgFor } from '@angular/common';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DragDropModule } from '@angular/cdk/drag-drop';

interface WebPage {
  id: string;
  url: string;
  title: string;
  favicon: string;
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
    this.http.get<WebPage[]>('http://localhost:5000/api/history').subscribe(
      (data) => {
        this.history = data;
      },
      (error) => {
        console.error('Error loading history:', error);
      }
    );
  }

  loadFrequentPages() {
    this.http.get<WebPage[]>('http://localhost:5000/api/history/frequent').subscribe(
      (data) => {
        this.frequentPages = data;
      },
      (error) => {
        console.error('Error loading frequent pages:', error);
      }
    );
  }

  loadFolders() {
    this.http.get<Folder[]>('http://localhost:5000/api/folders').subscribe(
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

  onDrop(event: CdkDragDrop<WebPage[]>) {
    if (event.previousContainer === event.container) {
      // Reordering within the same container
      moveItemInArray(
        event.container.data,
        event.previousIndex,
        event.currentIndex
      );
    } else {
      // Get the page being moved
      const page = event.previousContainer.data[event.previousIndex];
      
      // Moving item from one container to another
      if (event.container.id.startsWith('folder-')) {
        // We're dropping into a folder - check if this URL already exists in the folder
        const folderId = event.container.id.replace('folder-', '');
        const folder = this.folders.find(f => f.id === folderId);
        
        // Check if the page URL already exists in the folder
        const urlExists = folder?.pages.some(p => p.url === page.url);
        
        if (!urlExists) {
          // If URL doesn't exist in the folder, add it
          transferArrayItem(
            event.previousContainer.data,
            event.container.data,
            event.previousIndex,
            event.currentIndex
          );
          
          // Update the backend
          const pageId = event.container.data[event.currentIndex].id;
          
          this.http.post(`http://localhost:5000/api/folders/${folderId}/pages/${pageId}`, {}).subscribe(
            () => {
              console.log('Page added to folder successfully');
            },
            (error) => {
              console.error('Error adding page to folder:', error);
            }
          );
        } else {
          // URL already exists in folder, just remove from source without adding to destination
          event.previousContainer.data.splice(event.previousIndex, 1);
          
          // Notify user
          alert('This URL already exists in the folder. Duplicate not added.');
        }
      } else {
        // Not dropping into a folder, perform normal transfer
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
    const currentPage: WebPage = {
      id: Date.now().toString(),
      url: this.currentUrl,
      title: 'Current Page',
      favicon: 'favicon.ico',
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
}