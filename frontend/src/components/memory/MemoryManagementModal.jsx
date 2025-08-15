import React, { useState, useEffect } from 'react';
import { X, Search, Edit2, Trash2, RefreshCw, Database, Users, CheckSquare, Square } from 'lucide-react';
import { Button } from '@common/button';
import { Input } from '@common/input';
import { Textarea } from '@common/textarea';
import { Dialog } from '@common/dialog';
import { Heading } from '@common/heading';
import { Text } from '@common/text';
import { Badge } from '@common/badge';
import { Checkbox } from '@common/checkbox';

export function MemoryManagementModal({ isOpen, onClose }) {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState({ total: 0, byUser: [] });
  const [editingMemory, setEditingMemory] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [selectedMemories, setSelectedMemories] = useState(new Set());

  // Fetch all users with memories
  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const res = await fetch('/api/memory/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  // Fetch memories
  const fetchMemories = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const params = new URLSearchParams();
      if (selectedUserId) params.append('userId', selectedUserId);
      params.append('limit', '500');
      
      const res = await fetch(`/api/memory/list/1?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories);
        setStats(data.stats);
      }
    } catch (error) {
      console.error('Error fetching memories:', error);
    } finally {
      setLoading(false);
    }
  };

  // Search memories
  const searchMemories = async () => {
    if (!searchQuery) {
      fetchMemories();
      return;
    }
    
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const params = new URLSearchParams({
        q: searchQuery,
        limit: '50'
      });
      if (selectedUserId) params.append('userId', selectedUserId);
      
      const res = await fetch(`/api/memory/search?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories);
      }
    } catch (error) {
      console.error('Error searching memories:', error);
    } finally {
      setLoading(false);
    }
  };

  // Update memory
  const updateMemory = async () => {
    if (!editingMemory || !editContent) return;
    
    try {
      const token = localStorage.getItem('authToken');
      const res = await fetch(`/api/memory/${editingMemory.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content: editContent })
      });
      
      if (res.ok) {
        setEditingMemory(null);
        setEditContent('');
        fetchMemories(); // Refresh list
      }
    } catch (error) {
      console.error('Error updating memory:', error);
    }
  };

  // Delete memory
  const deleteMemory = async (memoryId) => {
    if (!confirm('Are you sure you want to delete this memory?')) return;
    
    try {
      const token = localStorage.getItem('authToken');
      const res = await fetch(`/api/memory/${memoryId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        fetchMemories(); // Refresh list
      }
    } catch (error) {
      console.error('Error deleting memory:', error);
    }
  };

  // Delete all memories for a user
  const deleteAllUserMemories = async () => {
    if (!selectedUserId) return;
    if (!confirm(`Are you sure you want to delete ALL memories for user ${selectedUserId}? This cannot be undone.`)) return;
    
    try {
      const token = localStorage.getItem('authToken');
      const res = await fetch(`/api/memory/user/${selectedUserId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        fetchMemories(); // Refresh list
        fetchUsers(); // Refresh user list
      }
    } catch (error) {
      console.error('Error deleting user memories:', error);
    }
  };

  // Bulk delete selected memories
  const bulkDeleteMemories = async () => {
    if (selectedMemories.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedMemories.size} selected memories? This cannot be undone.`)) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      
      // Delete each selected memory
      const deletePromises = Array.from(selectedMemories).map(memoryId =>
        fetch(`/api/memory/${memoryId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        })
      );
      
      await Promise.all(deletePromises);
      
      setSelectedMemories(new Set()); // Clear selection
      fetchMemories(); // Refresh list
    } catch (error) {
      console.error('Error bulk deleting memories:', error);
    } finally {
      setLoading(false);
    }
  };

  // Toggle memory selection
  const toggleMemorySelection = (memoryId) => {
    const newSelection = new Set(selectedMemories);
    if (newSelection.has(memoryId)) {
      newSelection.delete(memoryId);
    } else {
      newSelection.add(memoryId);
    }
    setSelectedMemories(newSelection);
  };

  // Select/deselect all visible memories
  const toggleSelectAll = () => {
    if (selectedMemories.size === memories.length) {
      setSelectedMemories(new Set());
    } else {
      setSelectedMemories(new Set(memories.map(m => m.id)));
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchUsers();
      fetchMemories();
    }
  }, [isOpen]);

  useEffect(() => {
    if (searchQuery) {
      const timer = setTimeout(() => {
        searchMemories();
      }, 300);
      return () => clearTimeout(timer);
    } else {
      fetchMemories();
    }
  }, [searchQuery, selectedUserId]);

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onClose={onClose} size="5xl">
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="relative bg-white dark:bg-zinc-900 rounded-lg shadow-xl w-full max-h-[90vh] overflow-hidden" style={{ maxWidth: '1400px' }}>
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-zinc-200 dark:border-zinc-700">
              <div>
                <Heading level={2} className="flex items-center gap-2">
                  <Database className="h-6 w-6" />
                  Memory Management
                </Heading>
                <Text className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                  Total memories: {stats.total} | Users: {stats.byUser.length}
                </Text>
              </div>
              <Button onClick={onClose} plain>
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Controls */}
            <div className="p-6 border-b border-zinc-200 dark:border-zinc-700 space-y-4">
              <div className="flex gap-4">
                <div className="flex-1 relative">
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2 pointer-events-none">
                    <Search className="h-4 w-4 text-zinc-400" />
                  </div>
                  <Input
                    type="text"
                    placeholder="Search memories..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10"
                  />
                </div>
                <select
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className="px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-md bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                >
                  <option value="">All Users</option>
                  {users.map(user => (
                    <option key={user.userId} value={user.userId}>
                      {user.userId} ({user.memoryCount} memories)
                    </option>
                  ))}
                </select>
                <Button onClick={fetchMemories} outline>
                  <RefreshCw className="h-4 w-4" />
                </Button>
                {selectedUserId && (
                  <Button 
                    onClick={deleteAllUserMemories} 
                    color="red"
                    outline
                  >
                    Delete All for User
                  </Button>
                )}
              </div>
              {/* Bulk selection controls */}
              {memories.length > 0 && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <Button 
                      onClick={toggleSelectAll} 
                      outline
                      className="flex items-center gap-2"
                    >
                      {selectedMemories.size === memories.length ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}
                      {selectedMemories.size === memories.length ? 'Deselect All' : 'Select All'}
                    </Button>
                    {selectedMemories.size > 0 && (
                      <Text className="text-sm text-zinc-600 dark:text-zinc-400">
                        {selectedMemories.size} selected
                      </Text>
                    )}
                  </div>
                  {selectedMemories.size > 0 && (
                    <Button 
                      onClick={bulkDeleteMemories} 
                      color="red"
                      disabled={loading}
                    >
                      Delete Selected ({selectedMemories.size})
                    </Button>
                  )}
                </div>
              )}
            </div>

            {/* Memory List */}
            <div className="overflow-y-auto" style={{ maxHeight: 'calc(90vh - 200px)' }}>
              {loading ? (
                <div className="p-8 text-center text-zinc-500">Loading memories...</div>
              ) : memories.length === 0 ? (
                <div className="p-8 text-center text-zinc-500">No memories found</div>
              ) : (
                <div className="divide-y divide-zinc-200 dark:divide-zinc-700">
                  {memories.map((memory) => (
                    <div key={memory.id} className="p-6 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors">
                      {editingMemory?.id === memory.id ? (
                        <div className="space-y-3">
                          <Textarea
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            rows={3}
                            className="w-full"
                          />
                          <div className="flex gap-2">
                            <Button onClick={updateMemory} small>
                              Save
                            </Button>
                            <Button 
                              onClick={() => {
                                setEditingMemory(null);
                                setEditContent('');
                              }} 
                              outline 
                              small
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-start gap-4">
                            <div className="pt-1">
                              <button
                                onClick={() => toggleMemorySelection(memory.id)}
                                className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded transition-colors"
                              >
                                {selectedMemories.has(memory.id) ? (
                                  <CheckSquare className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                ) : (
                                  <Square className="h-5 w-5 text-zinc-400" />
                                )}
                              </button>
                            </div>
                            <div className="flex-1">
                              <Text className="text-zinc-900 dark:text-zinc-100 text-base leading-relaxed">
                                {memory.content || memory.memory || 'No content available'}
                              </Text>
                              <div className="flex items-center gap-4 mt-3">
                                <Badge color="zinc">
                                  ID: {memory.id}
                                </Badge>
                                {memory.user_id && (
                                  <Badge color="amber">
                                    User: {memory.user_id}
                                  </Badge>
                                )}
                                {memory.score && (
                                  <Badge color="indigo" small>
                                    Score: {memory.score.toFixed(3)}
                                  </Badge>
                                )}
                                <Text className="text-xs text-zinc-500">
                                  {new Date(memory.created_at || memory.createdAt).toLocaleString()}
                                </Text>
                              </div>
                              {memory.metadata && (
                                <div className="mt-2">
                                  {(() => {
                                    try {
                                      const metadata = typeof memory.metadata === 'string' 
                                        ? JSON.parse(memory.metadata) 
                                        : memory.metadata;
                                      
                                      return (
                                        <div className="space-y-2">
                                          {metadata.type && (
                                            <div className="flex items-center gap-2">
                                              <Badge color="blue" small>
                                                {metadata.type}
                                              </Badge>
                                              {metadata.category && (
                                                <Badge color="green" small>
                                                  {metadata.category}
                                                </Badge>
                                              )}
                                              {metadata.priority && (
                                                <Badge color={metadata.priority === 'high' ? 'red' : metadata.priority === 'medium' ? 'amber' : 'zinc'} small>
                                                  {metadata.priority}
                                                </Badge>
                                              )}
                                            </div>
                                          )}
                                          {metadata.tags && Array.isArray(metadata.tags) && metadata.tags.length > 0 && (
                                            <div className="flex flex-wrap gap-1">
                                              {metadata.tags.map((tag, idx) => (
                                                <Badge key={idx} color="purple" small>
                                                  {tag}
                                                </Badge>
                                              ))}
                                            </div>
                                          )}
                                          {metadata.agent_type && (
                                            <div>
                                              <Badge color="indigo" small>
                                                Agent: {metadata.agent_type}
                                              </Badge>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    } catch (e) {
                                      return (
                                        <Text className="text-xs text-zinc-600 dark:text-zinc-400">
                                          Metadata: {memory.metadata}
                                        </Text>
                                      );
                                    }
                                  })()}
                                </div>
                              )}
                            </div>
                            <div className="flex gap-3 ml-4">
                              <Button
                                onClick={() => {
                                  setEditingMemory(memory);
                                  setEditContent(memory.content || memory.memory || '');
                                }}
                                outline
                                className="flex items-center gap-1"
                              >
                                <Edit2 className="h-4 w-4" />
                                Edit
                              </Button>
                              <Button
                                onClick={() => deleteMemory(memory.id)}
                                outline
                                color="red"
                                className="flex items-center gap-1"
                              >
                                <Trash2 className="h-4 w-4" />
                                Delete
                              </Button>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Dialog>
  );
}