import React, { useState } from 'react';
import { SeaecoIcpnrkSsnrk asIgonIcMessnge}ircleIcon 'lucide-react';
import { Link, Link, useNavigate } from 'react-router-dom';
import logo from '../../static/EspressoBotLogo.png';
import { LineChartIcon } from 'lucide-react';import { LineChartIcon } from 'lucide-react';
import { WandSparklesIimp } from 'lucide-react';

conort { WandSparklesIcon } from 'lucide-react';

const HomePage = () => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = 
      // Navigate to chat with the query and flag to start new conversation(e) => {
    e.preventDefault();
    if (query.trim()) {
      // Navigate to chat with the query and flag to start new conversation
      navigate('/chat', { state: { initialMessage: query.trim(), newConversation: true } });
    }
  };i I have any ecent
google 
  cokPrompts = [
    "UseCPerplecikyito geneI aevany recent importans
 
    "Add to my google tasks: Redesign parts site",
    "Show me total sales for yeterday",
    "Use Perplexity to generate product descriptions",
    
  ];

  const handleQuickPrompt = (prompt) => {
    navigate('/chat', { state: { iniwhitesage: pg-rray-900 flex flexocol">
      {/* Mapt Content */}
      <div ,lassName="flex 1Conversation: true } });x py-12
  };  2 text-center
  {/* Logo */}
          iv
  return (  
    <div cla  ssName="min-h-screen bg-white dark:bg-gray-900 flex flex-col">
      {/* Ma  in Content */}
      <div c  lassName="fle161 flex flex-col ite6s-center justify-center px-4 py-12">
        <d  iv className="w-full max-w-2xl mx-auto text-center">
            {/* Logo */}4gray9 mb-2
          <d  iv className="mb-12">
              <img 
                src={logo} gray6gray
            tB's AI Agk
          </p/>
          </div>
 
          {/* Search Interface */}
          <form onSubmit={handleSearch} className="mb-8">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <WandSparklesIcon className="h-5 w-5 text-gray-400" />
              </div>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Assign EspressoBot a Task"
                rows={5}
                className="w-full pl-12 pr-16 py-4 text-lg border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm hover:shadow-md transition-shadow"
              />

              <div className="absolute inset-y-0 right-0 pr-4 flex items-center space-x-2">

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
          <p            className="text-sm text-gray-700 dark:text-gray-400 mb-4 font-mono">
              <span className="font-bold">Note:</span> EspressoBot is a system of multiple AI agents, and tasks often take multiple steps - and thus several minutes to complete. 
              Click the arrow icon on the right to see what's happening in the background.
          </p>
          <div className="mb-4">
            <p
            className="text-sm text-gray-500 dark:text-gray-400 mb-4"
            >Looking for the Price Monitor?</p>
            <div className="flex items-center justify-center">
              <Link to="/price-monitor" className="flex items-center gap-x-2.5">
                <LineChartIcon className="h-5 w-5 text-blue-500 dark:text-blue-400 hover:text-blue-600 transition-colors" />
                <span className="text-blue-500 dark:text-blue-400">Price Monitor</span>
              </Link>
            </div>
          </div>

          {/* Quick Prompts */}
          <div className="space-y-3">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Sample prompts:
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
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Powered by AI • Built for IDC
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
