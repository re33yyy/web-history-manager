// src/app/loading/loading.component.ts
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LoadingService } from '../loading.service';

@Component({
  selector: 'app-loading',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="loadingService.loading$ | async" class="loading-overlay">
      <div class="loading-spinner">
        <div class="hourglass"></div>
      </div>
    </div>
  `,
  styles: [`
    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.3);
      z-index: 9999;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: wait;
    }
    
    .loading-spinner {
      background-color: white;
      padding: 20px;
      border-radius: 5px;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    }
    
    .hourglass {
      display: inline-block;
      width: 48px;
      height: 48px;
      position: relative;
      overflow: hidden;
      background: #fff;
    }
    
    .hourglass:after {
      content: "";
      position: absolute;
      left: 50%;
      top: 0;
      transform: translateX(-50%);
      width: 28px;
      height: 48px;
      background-image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><path fill='%233f51b5' d='M54,24h-8v-4h8V24z M54,80h-8v-4h8V80z M54,32c0-5.51-4.49-10-10-10s-10,4.49-10,10h10h10 M54,68c0,5.51-4.49,10-10,10s-10-4.49-10-10h10h10 M50,38c0-3.31-2.69-6-6-6s-6,2.69-6,6c0,0.91,0.21,1.76,0.57,2.53L50,62.47c0.36-0.77,0.57-1.62,0.57-2.53c0-3.31-2.69-6-6-6V38'/></svg>");
      background-repeat: no-repeat;
      background-position: center;
      animation: hourglass 1s linear infinite;
    }
    
    @keyframes hourglass {
      0% {
        transform: translateX(-50%) rotate(0deg);
      }
      100% {
        transform: translateX(-50%) rotate(180deg);
      }
    }
  `]
})
export class LoadingComponent {
  constructor(public loadingService: LoadingService) {}
}