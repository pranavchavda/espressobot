import React, { useState } from 'react';
import { SearchIcon, SparklesIcon, MessageCircleIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import logo from '../../static/EspressoBotLogo.png';

const HomePage = () => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) {
      // Navigate to chat with the query and flag to start new conversation
      navigate('/chat', { state: { initialMessage: query.trim(), newConversation: true } });
    }
  };

  const quickPrompts = [
    "Generate product descriptions for my Shopify store",
    "Analyze competitor pricing strategies",
    "Create MAP violation enforcement letter",
    "Help me optimize product listings for SEO",
    "Draft customer service response templates",
    "Compare product specifications"
  ];

  const handleQuickPrompt = (prompt) => {
    setQuery(prompt);
    navigate('/chat', { state: { initialMessage: prompt, newConversation: true } });
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 flex flex-col">
      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-2xl mx-auto text-center">
          {/* Logo */}
          <div className="mb-12">
            <img 
              src={logo} 
              alt="EspressoBot" 
              className="h-16 w-auto mx-auto mb-6"
            />
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
              EspressoBot
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-400">
              Your AI assistant for Shopify store management
            </p>
          </div>

          {/* Search Interface */}
          <form onSubmit={handleSearch} className="mb-8">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <SearchIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask anything..."
                className="w-full pl-12 pr-16 py-4 text-lg border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm hover:shadow-md transition-shadow"
              />
              <div className="absolute inset-y-0 right-0 pr-4 flex items-center space-x-2">
                <button
                  type="button"
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  title="Voice input"
                >
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                  </svg>
                </button>
                {query.trim() && (
                  <button
                    type="submit"
                    className="p-2 text-blue-600 hover:text-blue-700 transition-colors"
                  >
                    <SparklesIcon className="h-5 w-5" />
                  </button>
                )}
              </div>
            </div>
          </form>

          {/* Quick Prompts */}
          <div className="space-y-3">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Try these popular queries:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {quickPrompts.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => handleQuickPrompt(prompt)}
                  className="text-left p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors group"
                >
                  <div className="flex items-start gap-3">
                    <MessageCircleIcon className="h-4 w-4 text-gray-400 group-hover:text-blue-500 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">
                      {prompt}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 dark:border-gray-700 py-6">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-6 text-sm text-gray-500 dark:text-gray-400">
              <button 
                onClick={() => navigate('/price-monitor')}
                className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              >
                Price Monitor
              </button>
              <button 
                onClick={() => navigate('/dashboard')}
                className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              >
                Analytics
              </button>
              <button 
                onClick={() => navigate('/tasks')}
                className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              >
                Tasks
              </button>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Powered by AI • Built for Shopify
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;