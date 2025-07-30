import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import { registerServiceWorker } from './registerServiceWorker'
import { ToastProvider } from './components/common/toast';
import cacheBuster from './utils/cache-buster';

// Register service worker for PWA support
registerServiceWorker()

const container = document.getElementById('root');
createRoot(container).render(
  <React.StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <App />
      </ToastProvider>
    </BrowserRouter>
  </React.StrictMode>
);