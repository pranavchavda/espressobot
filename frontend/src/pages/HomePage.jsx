import React, { useState, useRef } from 'react';
import { ArrowRight, Bot, Zap, Mail, CheckSquare, BarChart2, ImageIcon, FileIcon, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import logo from '../../static/EspressoBotLogo.png';
import { Button } from '@common/button';

const HomePage = () => {
  const [query, setQuery] = useState('');
  const [imageAttachment, setImageAttachment] = useState(null);
  const [fileAttachment, setFileAttachment] = useState(null);
  const navigate = useNavigate();
  const imageInputRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim() || imageAttachment || fileAttachment) {
      navigate('/chat', { 
        state: { 
          initialMessage: query.trim(), 
          imageAttachment,
          fileAttachment,
          newConversation: true 
        } 
      });
    }
  };

  const quickPrompts = [
    { text: "Check for important new emails", icon: Mail },
    { text: "Add to my tasks: Redesign parts site", icon: CheckSquare },
    { text: "Show me total sales for yesterday", icon: BarChart2 },
    { text: "Draft a product description for the new grinder", icon: Zap },
  ];

  const handleQuickPrompt = (prompt) => {
    navigate('/chat', { state: { initialMessage: prompt, newConversation: true } });
  };

  // Simplified attachment logic for homepage
  const handleImageAttachment = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      setImageAttachment({ dataUrl: e.target.result, file });
      setFileAttachment(null);
    };
    reader.readAsDataURL(file);
  };

  const handleFileAttachment = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      setFileAttachment({ dataUrl: e.target.result, file });
      setImageAttachment(null);
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-3xl mx-auto">
        <header className="text-center mb-12">
          <img 
            src={logo} 
            alt="EspressoBot" 
            className="h-16 w-auto mx-auto mb-4"
          />
          <h1 className="text-5xl font-bold text-zinc-800 dark:text-white">
            EspressoBot
          </h1>
          <p className="text-lg text-zinc-500 dark:text-zinc-400 mt-2">
            Your AI-powered command center for iDrinkCoffee.com
          </p>
        </header>

        <main>
          <form onSubmit={handleSearch} className="mb-10">
            <div className="relative">
              <Bot className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-zinc-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Delegate a task to your AI agent..."
                className="w-full pl-12 pr-40 py-4 text-base border border-zinc-200 dark:border-zinc-700 rounded-full bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-lg"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                <Button
                  type="button"
                  plain
                  onClick={() => imageInputRef.current?.click()}
                  className="h-10 w-10 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-700"
                  title="Add image"
                >
                  <ImageIcon className="h-5 w-5 text-zinc-500" />
                </Button>
                <Button
                  type="button"
                  plain
                  onClick={() => fileInputRef.current?.click()}
                  className="h-10 w-10 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-700"
                  title="Add file"
                >
                  <FileIcon className="h-5 w-5 text-zinc-500" />
                </Button>
                <button
                  type="submit"
                  disabled={!query.trim() && !imageAttachment && !fileAttachment}
                  className="h-10 w-10 bg-blue-600 text-white rounded-full flex items-center justify-center hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed transition-colors"
                >
                  <ArrowRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          </form>

          {(imageAttachment || fileAttachment) && (
            <div className="mb-6 flex justify-center">
              <div className="relative inline-block">
                {imageAttachment && (
                  <img 
                    src={imageAttachment.dataUrl} 
                    alt="Preview" 
                    className="h-24 rounded-lg border border-zinc-200 dark:border-zinc-700"
                  />
                )}
                {fileAttachment && (
                  <div className="h-24 w-24 flex items-center justify-center bg-zinc-100 dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700">
                    <FileIcon className="h-8 w-8 text-zinc-500" />
                  </div>
                )}
                <button 
                  onClick={() => { setImageAttachment(null); setFileAttachment(null); }}
                  className="absolute -top-2 -right-2 bg-zinc-200 dark:bg-zinc-700 rounded-full p-1 hover:bg-zinc-300 dark:hover:bg-zinc-600"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </div>
          )}

          <input type="file" ref={imageInputRef} accept="image/*" onChange={(e) => handleImageAttachment(e.target.files[0])} className="hidden" />
          <input type="file" ref={fileInputRef} onChange={(e) => handleFileAttachment(e.target.files[0])} className="hidden" />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {quickPrompts.map((prompt, index) => (
              <button
                key={index}
                onClick={() => handleQuickPrompt(prompt.text)}
                className="text-left p-4 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:border-blue-400 dark:hover:border-blue-600 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="bg-zinc-100 dark:bg-zinc-800 p-2 rounded-full">
                    <prompt.icon className="h-5 w-5 text-zinc-500 group-hover:text-blue-500 transition-colors" />
                  </div>
                  <span className="text-sm text-zinc-700 dark:text-zinc-300">
                    {prompt.text}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
};

export default HomePage;
