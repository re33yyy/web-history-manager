# Web History Manager - Setup Instructions

This project consists of three main components:
1. Angular frontend
2. Python Flask backend
3. Chrome extension for tracking page visits

## Setup Instructions

### 1. Backend Setup (Python Flask)

1. Create a new directory for the project and set up a virtual environment:
```bash
mkdir web-history-manager
cd web-history-manager
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages:
```bash
pip install flask flask-cors
```

3. Create a new file `app.py` with the provided Python code
4. Run the Flask server:
```bash
python app.py
```

The server will run on http://localhost:5000.

### 2. Frontend Setup (Angular)

1. Make sure you have Node.js and Angular CLI installed:
```bash
npm install -g @angular/cli
```

2. Create a new Angular project:
```bash
ng new web-history-frontend
cd web-history-frontend
```

3. Install required dependencies:
```bash
npm install @angular/cdk
```

4. Replace the contents of the following files with the provided code:
   - `src/app/app.component.ts`
   - `src/app/app.component.html`
   - `src/app/app.component.css`

5. Update the `app.module.ts` file to import the required modules:
```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { DragDropModule } from '@angular/cdk/drag-drop';

import { AppComponent } from './app.component';

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpClientModule,
    DragDropModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

6. Run the Angular application:
```bash
ng serve
```

The frontend will be available at http://localhost:4200.

### 3. Chrome Extension Setup

1. Create a new directory for the Chrome extension:
```bash
mkdir web-history-extension
cd web-history-extension
```

2. Create the following files with the provided code:
   - `manifest.json`
   - `background.js`
   - `popup.html`
   - `popup.js`

3. Create an `icons` directory and add icon images (you can use placeholder images for now)

4. Load the extension in Chrome:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" in the top-right corner
   - Click "Load unpacked" and select the extension directory
   - The extension icon should appear in your browser toolbar

## How to Use

1. Make sure both the Flask backend and Angular frontend are running
2. Browse the web with the Chrome extension installed
3. The extension will track your browsing history and send it to the backend
4. Open the web history manager by clicking the extension icon and then "Open History Manager"
5. In the web history manager, you can:
   - View your browsing history
   - Create folders to organize your pages
   - Drag pages from history to folders
   - Add the current page to a folder
   - Delete folders

## Features

- **Automatic History Tracking**: The Chrome extension automatically logs the sites you visit
- **Drag and Drop Organization**: Easily drag pages from your history into custom folders
- **Current Page Addition**: Add your current page to any folder with a single click
- **Folder Management**: Create, rename, and delete folders as needed

## System Requirements

- Python 3.6+ with Flask
- Node.js 12+ with Angular CLI
- Google Chrome browser