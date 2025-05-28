import React from 'react'; // Still might be needed for some global JSX or future client-side enhancements
import './index.css'; // Global styles
import { registerServiceWorker } from './registerServiceWorker';

// Register service worker for PWA support
registerServiceWorker();

// Remix will handle mounting the application.
// This file is now primarily for global side effects like CSS imports or service workers.
console.log("Remix application entry point (main.jsx) - Global styles and service worker registered.");