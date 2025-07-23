import React, { useState, useEffect } from 'react';
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react';
import { Button } from '@common/button';
import { XIcon, FileTextIcon, PlusIcon, TrashIcon, RefreshCwIcon } from 'lucide-react';
import { Field, Label } from '@common/fieldset';
import { Textarea } from '@common/textarea';

export function ScratchpadDialog({ isOpen, onClose }) {
  const [scratchpadData, setScratchpadData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [newEntry, setNewEntry] = useState('');
  const [activeTab, setActiveTab] = useState('content'); // 'content' or 'entries'

  // Load scratchpad data when dialog opens
  useEffect(() => {
    if (isOpen) {
      loadScratchpad();
    }
  }, [isOpen]);

  // Update edit content when scratchpad data changes
  useEffect(() => {
    if (scratchpadData?.content) {
      setEditContent(scratchpadData.content);
    }
  }, [scratchpadData]);

  const loadScratchpad = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/scratchpad', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ action: 'read' }),
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to load scratchpad');
      
      const result = await response.json();
      setScratchpadData(result.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const saveScratchpad = async (action, content, author = 'User') => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/scratchpad', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ action, content, author }),
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to save scratchpad');
      
      const result = await response.json();
      setScratchpadData(result.data);
      
      if (action === 'add_entry') {
        setNewEntry('');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveContent = () => {
    saveScratchpad('write', editContent);
  };

  const handleAddEntry = () => {
    if (newEntry.trim()) {
      saveScratchpad('add_entry', newEntry.trim());
    }
  };

  const handleClear = () => {
    if (confirm('Are you sure you want to clear the entire scratchpad?')) {
      saveScratchpad('clear', '');
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/25" />
      <div className="fixed inset-0 flex w-screen items-center justify-center p-4">
        <DialogPanel className="max-w-4xl w-full max-h-[80vh] bg-white dark:bg-zinc-900 rounded-lg shadow-xl">
          <div className="flex items-center justify-between p-6 border-b border-zinc-200 dark:border-zinc-700">
            <DialogTitle className="text-lg font-semibold flex items-center gap-2">
              <FileTextIcon className="h-5 w-5" />
              Scratchpad
            </DialogTitle>
            <Button onClick={onClose} className="p-1" color="zinc" outline>
              <XIcon className="h-4 w-4" />
            </Button>
          </div>

          <div className="p-6">
            {/* Tab Navigation */}
            <div className="flex gap-2 mb-4 border-b border-zinc-200 dark:border-zinc-700">
              <button
                onClick={() => setActiveTab('content')}
                className={`px-4 py-2 font-medium text-sm ${
                  activeTab === 'content'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
                }`}
              >
                Main Content
              </button>
              <button
                onClick={() => setActiveTab('entries')}
                className={`px-4 py-2 font-medium text-sm ${
                  activeTab === 'entries'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
                }`}
              >
                Entries ({scratchpadData?.entries?.length || 0})
              </button>
            </div>

            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-8">
                <RefreshCwIcon className="h-5 w-5 animate-spin mr-2" />
                Loading scratchpad...
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 p-4 rounded-lg mb-4">
                Error: {error}
              </div>
            )}

            {/* Content Tab */}
            {activeTab === 'content' && !loading && (
              <div className="space-y-4">
                <Field>
                  <Label>Main Content</Label>
                  <Textarea
                    rows={12}
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    placeholder="Write your notes here... This content is shared across all agents and conversations."
                    className="font-mono text-sm"
                  />
                </Field>
                <div className="flex gap-2 justify-end">
                  <Button onClick={loadScratchpad} color="zinc" outline>
                    <RefreshCwIcon className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                  <Button onClick={handleSaveContent} color="blue">
                    Save Content
                  </Button>
                </div>
              </div>
            )}

            {/* Entries Tab */}
            {activeTab === 'entries' && !loading && (
              <div className="space-y-4">
                {/* Add New Entry */}
                <div className="bg-zinc-50 dark:bg-zinc-800 p-4 rounded-lg">
                  <Field>
                    <Label>Add New Entry</Label>
                    <div className="flex gap-2">
                      <Textarea
                        rows={2}
                        value={newEntry}
                        onChange={(e) => setNewEntry(e.target.value)}
                        placeholder="Add a quick note or update..."
                        className="flex-1"
                      />
                      <Button 
                        onClick={handleAddEntry} 
                        disabled={!newEntry.trim()}
                        color="blue"
                        className="self-end"
                      >
                        <PlusIcon className="h-4 w-4" />
                      </Button>
                    </div>
                  </Field>
                </div>

                {/* Entries List */}
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {scratchpadData?.entries?.length > 0 ? (
                    scratchpadData.entries
                      .slice()
                      .reverse() // Show newest first
                      .map((entry) => (
                        <div
                          key={entry.id}
                          className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg p-3"
                        >
                          <div className="flex justify-between items-start mb-2">
                            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                              {entry.author}
                            </span>
                            <span className="text-xs text-zinc-500">
                              {formatDate(entry.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">
                            {entry.content}
                          </p>
                        </div>
                      ))
                  ) : (
                    <div className="text-center py-8 text-zinc-500">
                      No entries yet. Add your first entry above!
                    </div>
                  )}
                </div>

                <div className="flex gap-2 justify-end">
                  <Button onClick={loadScratchpad} color="zinc" outline>
                    <RefreshCwIcon className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                </div>
              </div>
            )}

            {/* Actions Bar */}
            <div className="flex justify-between items-center mt-6 pt-4 border-t border-zinc-200 dark:border-zinc-700">
              <div className="text-xs text-zinc-500">
                {scratchpadData?.last_updated && (
                  <>Last updated: {formatDate(scratchpadData.last_updated)}</>
                )}
              </div>
              <Button onClick={handleClear} color="red" outline>
                <TrashIcon className="h-4 w-4 mr-2" />
                Clear All
              </Button>
            </div>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  );
}