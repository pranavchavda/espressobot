import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import { registerServiceWorker } from './registerServiceWorker'

// Register service worker for PWA support
registerServiceWorker()

const container = document.getElementById('root');
createRoot(container).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);