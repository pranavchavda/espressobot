/**
 * Cache Buster Utility
 * Handles aggressive cache management for Vivaldi/Chromium browsers
 */

const CACHE_BUSTER_KEY = 'espressobot-cache-version';
const REFRESH_INTERVAL = 3 * 60 * 60 * 1000; // 3 hours in milliseconds

class CacheBuster {
  constructor() {
    this.currentVersion = this.generateVersion();
    this.startAutoRefresh();
  }

  generateVersion() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  getCurrentVersion() {
    return localStorage.getItem(CACHE_BUSTER_KEY) || this.currentVersion;
  }

  setCurrentVersion(version = null) {
    const newVersion = version || this.generateVersion();
    localStorage.setItem(CACHE_BUSTER_KEY, newVersion);
    this.currentVersion = newVersion;
    return newVersion;
  }

  shouldRefresh() {
    // DISABLED: Automatic refresh logic to prevent auth issues
    // Always return false so it only runs when manually triggered
    return false;
  }

  forceRefresh() {
    console.log('[CacheBuster] Forcing NUCLEAR cache refresh for stubborn browsers...');
    
    // NUCLEAR OPTION 1: Clear SELECTIVE storage (preserve auth)
    try {
      // Backup auth tokens before clearing
      const authToken = localStorage.getItem('authToken');
      const userInfo = localStorage.getItem('userInfo');
      const googleTokens = localStorage.getItem('googleTokens');
      
      // Clear most localStorage but preserve auth
      Object.keys(localStorage).forEach(key => {
        if (!['authToken', 'userInfo', 'googleTokens'].includes(key)) {
          localStorage.removeItem(key);
        }
      });
      
      // Clear sessionStorage completely (no auth stored here typically)
      sessionStorage.clear();
      
      // Clear IndexedDB if available
      if (window.indexedDB) {
        indexedDB.databases().then(databases => {
          databases.forEach(db => {
            // Skip databases that might contain auth info
            if (!db.name.includes('auth') && !db.name.includes('token')) {
              indexedDB.deleteDatabase(db.name);
            }
          });
        }).catch(() => {});
      }
      
      // Clear cookies selectively (avoid auth cookies)
      const authCookiePatterns = ['connect.sid', 'session', 'auth', 'token', 'passport'];
      document.cookie.split(";").forEach(c => {
        const eqPos = c.indexOf("=");
        const name = eqPos > -1 ? c.substr(0, eqPos).trim() : c.trim();
        // Don't clear auth-related cookies (be more permissive with matching)
        const isAuthCookie = authCookiePatterns.some(pattern => 
          name.toLowerCase().includes(pattern.toLowerCase())
        );
        
        if (!isAuthCookie) {
          console.log('[CacheBuster] Clearing non-auth cookie:', name);
          document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
        } else {
          console.log('[CacheBuster] Preserving auth cookie:', name);
        }
      });
      
      console.log('[CacheBuster] Preserved auth tokens during cache clear');
    } catch (e) {
      console.warn('[CacheBuster] Storage clearing failed:', e);
    }
    
    // NUCLEAR OPTION 2: Service Worker cache clearing
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(registrations => {
        registrations.forEach(registration => {
          registration.unregister();
        });
      }).catch(() => {});
      
      if ('caches' in window) {
        caches.keys().then(names => {
          names.forEach(name => {
            caches.delete(name);
          });
        }).catch(() => {});
      }
    }
    
    // NUCLEAR OPTION 3: Multiple redirect strategies
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 15);
    const baseUrl = window.location.origin + window.location.pathname;
    
    // Try multiple approaches in sequence for maximum stubbornness
    const attempts = [
      // Method 1: Query params with cache busting
      `${baseUrl}?v=${timestamp}&r=${random}&nocache=1&_=${Date.now()}`,
      // Method 2: Hash-based refresh  
      `${baseUrl}#refresh-${timestamp}-${random}`,
      // Method 3: Add multiple cache-busting params
      `${baseUrl}?cb=${timestamp}&bust=${random}&reload=force&t=${Date.now()}&vivaldi=true`
    ];
    
    console.log('[CacheBuster] Trying nuclear refresh with URL:', attempts[0]);
    
    // Set new version before redirect
    this.setCurrentVersion(`${timestamp}-${random}`);
    localStorage.setItem(`${CACHE_BUSTER_KEY}-timestamp`, timestamp.toString());
    localStorage.setItem('cache-bust-attempt', '1');
    
    // DEBUG: Log current auth state before refresh
    console.log('[CacheBuster] Auth state before refresh:', {
      authToken: localStorage.getItem('authToken') ? 'present' : 'missing',
      userInfo: localStorage.getItem('userInfo') ? 'present' : 'missing',
      cookies: document.cookie.split(';').map(c => c.trim().split('=')[0]).filter(name => name),
      allCookies: document.cookie
    });
    
    // Small delay to ensure auth state is logged
    setTimeout(() => {
      console.log('[CacheBuster] Starting nuclear redirect...');
      
      // NUCLEAR REDIRECT - force full page replacement
      try {
        // First try: location.replace (doesn't add to history)
        window.location.replace(attempts[0]);
      } catch (e) {
        try {
          // Second try: direct assignment with cache busting
          window.location.href = attempts[0];
        } catch (e2) {
          try {
            // Third try: window.open and close current
            const newWindow = window.open(attempts[0], '_blank');
            if (newWindow) {
              window.close();
            }
          } catch (e3) {
            // Last resort: traditional reload with force
            console.warn('[CacheBuster] All redirect methods failed, using reload');
            window.location.reload(true);
          }
        }
      }
    }, 100); // End of setTimeout
  }

  startAutoRefresh() {
    console.log('[CacheBuster] Cache buster initialized - automatic refresh DISABLED');
    console.log('[CacheBuster] Cache clearing only available via manual trigger');
    
    // DISABLED: Automatic cache clearing to prevent auth issues
    // Only run when manually triggered via UI button or keyboard shortcut
    
    // Keep the periodic check but make it much less frequent and only for very old cache
    const VERY_OLD_CACHE_THRESHOLD = 24 * 60 * 60 * 1000; // 24 hours
    
    setInterval(() => {
      const lastRefresh = localStorage.getItem(`${CACHE_BUSTER_KEY}-timestamp`);
      const now = Date.now();
      
      // Only auto-refresh if cache is REALLY old (24+ hours) AND user hasn't been active recently
      if (lastRefresh && (now - parseInt(lastRefresh)) > VERY_OLD_CACHE_THRESHOLD) {
        // Check if user has been active recently (no auth token clearing)
        const authToken = localStorage.getItem('authToken');
        if (!authToken) {
          console.log('[CacheBuster] Very old cache detected on unauthenticated session - auto-refresh');
          this.forceRefresh();
        } else {
          console.log('[CacheBuster] Very old cache detected but user is authenticated - skipping auto-refresh');
        }
      }
    }, 60 * 60 * 1000); // Check every hour instead of every 30 minutes
  }

  addCacheBustingToRequests() {
    console.log('[CacheBuster] Request cache busting DISABLED to prevent auth issues');
    
    // DISABLED: Automatic request cache busting to prevent interference with auth API calls
    // The server-side cache headers should handle this appropriately
    
    // Keep minimal headers only for non-API requests if needed
    const originalFetch = window.fetch;
    window.fetch = (input, init = {}) => {
      const url = typeof input === 'string' ? input : input.url;
      
      // Only add minimal cache busting for non-API static resources
      if (!url.includes('/api/') && (url.endsWith('.js') || url.endsWith('.css') || url.endsWith('.html'))) {
        const headers = {
          'Cache-Control': 'no-cache',
          ...init.headers
        };
        return originalFetch(input, { ...init, headers });
      }
      
      return originalFetch(input, init);
    };
  }

  // Method to check if browser is Vivaldi/Chromium and apply extra measures
  detectVivaldi() {
    const userAgent = navigator.userAgent;
    const isVivaldi = /Vivaldi/.test(userAgent);
    const isChromium = /Chrome/.test(userAgent) && !/Edge/.test(userAgent);
    const isOpera = /OPR\//.test(userAgent);
    const isBrave = /Brave/.test(userAgent);
    
    if (isVivaldi || isChromium || isOpera || isBrave) {
      console.log('[CacheBuster] Chromium-based browser detected - applying aggressive cache busting');
      
      // Add meta tags to prevent caching
      this.addNoCacheMetaTags();
      
      // Add keyboard shortcut for manual refresh (Ctrl+Shift+R alternative)
      this.addKeyboardShortcut();
      
      // Apply extra aggressive measures for Vivaldi specifically
      if (isVivaldi) {
        console.log('[CacheBuster] VIVALDI DETECTED - using nuclear cache busting');
        this.applyVivaldiSpecificMeasures();
      }
      
      return true;
    }
    
    return false;
  }

  addKeyboardShortcut() {
    document.addEventListener('keydown', (e) => {
      // Ctrl+Shift+F5 or Ctrl+Alt+R for manual refresh
      if ((e.ctrlKey && e.shiftKey && e.key === 'F5') || 
          (e.ctrlKey && e.altKey && e.key === 'r')) {
        e.preventDefault();
        console.log('[CacheBuster] Manual keyboard refresh triggered');
        this.forceRefresh();
      }
    });
  }

  applyVivaldiSpecificMeasures() {
    // Vivaldi-specific measures (NON-AGGRESSIVE)
    console.log('[CacheBuster] Applying Vivaldi-specific measures (manual-only mode)');
    
    // Only apply meta tags and keyboard shortcuts - no automatic URL manipulation
    // Removed automatic URL parameter injection to prevent navigation issues
    
    console.log('[CacheBuster] Vivaldi measures applied - use Ctrl+Shift+F5 or menu button for cache refresh');
  }

  addNoCacheMetaTags() {
    const metaTags = [
      { 'http-equiv': 'Cache-Control', content: 'no-cache, no-store, must-revalidate' },
      { 'http-equiv': 'Pragma', content: 'no-cache' },
      { 'http-equiv': 'Expires', content: '0' }
    ];

    metaTags.forEach(({ 'http-equiv': httpEquiv, content }) => {
      let meta = document.querySelector(`meta[http-equiv="${httpEquiv}"]`);
      if (!meta) {
        meta = document.createElement('meta');
        meta.setAttribute('http-equiv', httpEquiv);
        document.head.appendChild(meta);
      }
      meta.setAttribute('content', content);
    });
  }

  // Manual refresh method for user-triggered refreshes
  manualRefresh() {
    console.log('[CacheBuster] Manual refresh requested');
    this.forceRefresh();
  }

  // Login-specific cache clearing (preserves auth but clears everything else)
  clearCacheOnLogin() {
    console.log('[CacheBuster] Clearing cache on new login...');
    
    try {
      // Backup auth tokens before clearing
      const authToken = localStorage.getItem('authToken');
      const userInfo = localStorage.getItem('userInfo');
      const googleTokens = localStorage.getItem('googleTokens');
      
      // Clear most localStorage but preserve auth
      Object.keys(localStorage).forEach(key => {
        if (!['authToken', 'userInfo', 'googleTokens'].includes(key)) {
          localStorage.removeItem(key);
          console.log('[CacheBuster] Cleared localStorage key:', key);
        }
      });
      
      // Clear sessionStorage completely
      const sessionKeys = Object.keys(sessionStorage);
      sessionStorage.clear();
      console.log(`[CacheBuster] Cleared ${sessionKeys.length} sessionStorage keys`);
      
      // Clear specific cache items that might be stale
      const cacheItemsToDelete = [
        'conversations-cache',
        'user-preferences',
        'last-selected-chat',
        'memory-cache',
        'agent-cache',
        'model-cache',
        'settings-cache',
        'sidebar-state',
        'ui-preferences'
      ];
      
      cacheItemsToDelete.forEach(key => {
        if (localStorage.getItem(key)) {
          localStorage.removeItem(key);
          console.log('[CacheBuster] Cleared cache item:', key);
        }
      });
      
      // Set a flag to indicate cache was cleared on this login
      localStorage.setItem('cache-cleared-on-login', Date.now().toString());
      
      console.log('[CacheBuster] Cache cleared successfully on login, auth tokens preserved');
      return true;
    } catch (error) {
      console.error('[CacheBuster] Error clearing cache on login:', error);
      return false;
    }
  }
}

// Create singleton instance
const cacheBuster = new CacheBuster();

// Detect browser and apply appropriate measures
if (cacheBuster.detectVivaldi()) {
  // More aggressive measures for Vivaldi/Chromium
  console.log('[CacheBuster] Enhanced cache busting active for Vivaldi/Chromium');
}

// Add cache busting to all requests
cacheBuster.addCacheBustingToRequests();

// Expose manual refresh globally
window.espressoBotCacheBuster = {
  refresh: () => cacheBuster.manualRefresh(),
  version: () => cacheBuster.getCurrentVersion(),
  shouldRefresh: () => cacheBuster.shouldRefresh(),
  clearOnLogin: () => cacheBuster.clearCacheOnLogin()
};

export default cacheBuster;