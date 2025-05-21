
import { useState, useEffect } from 'react';

export function PWAInstallPrompt() {
  const [showPrompt, setShowPrompt] = useState(false);
  const [installEvent, setInstallEvent] = useState(null);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    // Check if the user is on iOS
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    setIsIOS(isIOS);

    // Handle beforeinstallprompt event for Android
    const handleBeforeInstallPrompt = (e) => {
      // Prevent Chrome 76+ from automatically showing the prompt
      e.preventDefault();
      // Store the event so it can be triggered later
      setInstallEvent(e);
      // Show the prompt to the user
      setShowPrompt(true);
    };

    // Check if the app is already installed
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    if (isStandalone) {
      setShowPrompt(false);
      return;
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!installEvent) return;

    // Show the install prompt
    installEvent.prompt();
    // Wait for the user to respond to the prompt
    const { outcome } = await installEvent.userChoice;
    // Log the outcome
    console.log(`User response to the install prompt: ${outcome}`);
    // Clear the saved prompt
    setInstallEvent(null);
    // Hide the install button
    setShowPrompt(false);
  };

  if (!showPrompt) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-zinc-800 p-4 shadow-lg z-50 flex flex-col items-center space-y-2">
      <h3 className="font-semibold text-lg">Install Shopify Agent</h3>
      {isIOS ? (
        <div className="text-sm text-center">
          <p>To install this app on your iPhone:</p>
          <p>1. Tap <span className="inline-block"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v13M5 12l7 7 7-7"/></svg></span> and then</p>
          <p>2. "Add to Home Screen" <span className="inline-block">➕</span></p>
        </div>
      ) : (
        <button
          onClick={handleInstallClick}
          className="bg-shopify-purple text-white px-4 py-2 rounded-md font-medium"
        >
          Install App
        </button>
      )}
      <button 
        onClick={() => setShowPrompt(false)} 
        className="text-sm text-gray-500"
      >
        Maybe later
      </button>
    </div>
  );
}
