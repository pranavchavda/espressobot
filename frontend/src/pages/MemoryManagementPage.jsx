import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  X, Search, Edit2, Trash2, RefreshCw, Database, 
  ChevronLeft, Download, Upload, Filter, TrendingUp,
  Calendar, Tag, AlertCircle, CheckCircle, Info
} from 'lucide-react';
import { Button } from '@common/button';
import { Input } from '@common/input';
import { Textarea } from '@common/textarea';
import { Heading } from '@common/heading';
import { Text } from '@common/text';
import { Badge } from '@common/badge';

export default function MemoryManagementPage() {
  const navigate = useNavigate();
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [minImportance, setMinImportance] = useState(0);
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [editingMemory, setEditingMemory] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [selectedMemories, setSelectedMemories] = useState(new Set());
  const [showStats, setShowStats] = useState(true);

  // Fetch dashboard data
  const fetchDashboard = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const userId = selectedUserId || '1'; // Default to user ID 1 instead of 'all'
      const res = await fetch(`/api/memory/dashboard/${userId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats);
        // Optionally set memories from dashboard
        if (data.recent_memories) {
          setMemories(data.recent_memories);
        }
      }
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    }
  };

  // Fetch memories with filters
  const fetchMemories = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const userId = selectedUserId || '1'; // Default to user ID 1 instead of 'all'
      const params = new URLSearchParams();
      
      if (selectedCategory) params.append('category', selectedCategory);
      if (minImportance > 0) params.append('importance_min', minImportance);
      params.append('limit', '100');
      
      const res = await fetch(`/api/memory/list/${userId}?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setMemories(data);
      }
    } catch (error) {
      console.error('Error fetching memories:', error);
    } finally {
      setLoading(false);
    }
  };

  // Search memories semantically
  const searchMemories = async () => {
    if (!searchQuery) {
      fetchMemories();
      return;
    }
    
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const userId = selectedUserId || '1'; // Default to user ID 1 instead of 'all'
      
      const res = await fetch(`/api/memory/search/${userId}`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: searchQuery,
          limit: 50,
          similarity_threshold: 0.7,
          category: selectedCategory || null
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setMemories(data);
      }
    } catch (error) {
      console.error('Error searching memories:', error);
    } finally {
      setLoading(false);
    }
  };

  // Export memories
  const exportMemories = async (format = 'json') => {
    try {
      const token = localStorage.getItem('authToken');
      const userId = selectedUserId || 'all';
      
      const res = await fetch(`/api/memory/export/${userId}?format=${format}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `memories_${userId}_${Date.now()}.${format}`;
        a.click();
      }
    } catch (error) {
      console.error('Error exporting memories:', error);
    }
  };

  // Import memories
  const handleImport = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const token = localStorage.getItem('authToken');
      const userId = selectedUserId || 'default';
      
      const res = await fetch(`/api/memory/import/${userId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        alert(`Successfully imported ${data.imported_count} memories`);
        fetchMemories();
      }
    } catch (error) {
      console.error('Error importing memories:', error);
    }
  };

  // Update memory
  const updateMemory = async () => {
    if (!editingMemory || !editContent) return;
    
    try {
      const token = localStorage.getItem('authToken');
      const res = await fetch(`/api/memory/${editingMemory.id}?user_id=${editingMemory.user_id}`, {
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
        fetchMemories();
      }
    } catch (error) {
      console.error('Error updating memory:', error);
    }
  };

  // Delete memory
  const deleteMemory = async (memoryId, userId) => {
    if (!confirm('Are you sure you want to delete this memory?')) return;
    
    try {
      const token = localStorage.getItem('authToken');
      const res = await fetch(`/api/memory/${memoryId}?user_id=${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        fetchMemories();
      }
    } catch (error) {
      console.error('Error deleting memory:', error);
    }
  };

  // Bulk delete
  const bulkDelete = async () => {
    if (selectedMemories.size === 0) return;
    if (!confirm(`Delete ${selectedMemories.size} selected memories?`)) return;
    
    try {
      const token = localStorage.getItem('authToken');
      const userId = selectedUserId || 'all';
      
      const res = await fetch(`/api/memory/bulk/${userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          operation: 'delete',
          memory_ids: Array.from(selectedMemories)
        })
      });
      
      if (res.ok) {
        setSelectedMemories(new Set());
        fetchMemories();
      }
    } catch (error) {
      console.error('Error bulk deleting:', error);
    }
  };

  // Cleanup old memories
  const cleanupMemories = async () => {
    if (!confirm('Remove memories older than 90 days with low access count?')) return;
    
    try {
      const token = localStorage.getItem('authToken');
      const res = await fetch('/api/memory/cleanup?days_old=90&min_access_count=1', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        alert(`Cleaned up ${data.deleted_count} old memories`);
        fetchMemories();
      }
    } catch (error) {
      console.error('Error cleaning up memories:', error);
    }
  };

  useEffect(() => {
    fetchDashboard();
    fetchMemories();
  }, [selectedUserId, selectedCategory, minImportance]);

  useEffect(() => {
    if (searchQuery) {
      const timer = setTimeout(() => {
        searchMemories();
      }, 300);
      return () => clearTimeout(timer);
    } else {
      fetchMemories();
    }
  }, [searchQuery]);

  const getCategoryColor = (category) => {
    const colors = {
      products: 'blue',
      preferences: 'purple',
      interactions: 'green',
      facts: 'amber',
      problems: 'red',
      solutions: 'emerald',
      general: 'zinc'
    };
    return colors[category] || 'zinc';
  };

  const getImportanceColor = (score) => {
    if (score >= 0.8) return 'red';
    if (score >= 0.5) return 'amber';
    return 'zinc';
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Header */}
      <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                outline
                onClick={() => navigate('/admin')}
              >
                <ChevronLeft className="h-4 w-4 mr-2" />
                Back to Admin
              </Button>
              <div>
                <Heading level={1} className="flex items-center gap-2">
                  <Database className="h-6 w-6" />
                  Memory Management
                </Heading>
                {stats && (
                  <Text className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                    {stats.total_memories} total memories • {stats.categories} categories
                  </Text>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => setShowStats(!showStats)} outline>
                <TrendingUp className="h-4 w-4 mr-2" />
                {showStats ? 'Hide' : 'Show'} Stats
              </Button>
              <Button onClick={() => exportMemories('json')} outline>
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
              <Button onClick={() => exportMemories('csv')} outline>
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
              <label>
                <Button outline>
                  <Upload className="h-4 w-4 mr-2" />
                  Import
                </Button>
                <input
                  type="file"
                  accept=".json,.csv"
                  onChange={handleImport}
                  className="hidden"
                />
              </label>
              <Button onClick={cleanupMemories} color="amber" outline>
                Clean Old
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Dashboard */}
      {showStats && stats && (
        <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
          <div className="container mx-auto px-6 py-4">
            <div className="grid grid-cols-4 gap-6">
              <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4">
                <Text className="text-sm text-zinc-600 dark:text-zinc-400">Total Memories</Text>
                <Text className="text-2xl font-bold">{stats.total_memories}</Text>
              </div>
              <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4">
                <Text className="text-sm text-zinc-600 dark:text-zinc-400">Categories</Text>
                <Text className="text-2xl font-bold">{stats.categories}</Text>
              </div>
              <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4">
                <Text className="text-sm text-zinc-600 dark:text-zinc-400">Avg Importance</Text>
                <Text className="text-2xl font-bold">{stats.avg_importance?.toFixed(2) || '0'}</Text>
              </div>
              <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4">
                <Text className="text-sm text-zinc-600 dark:text-zinc-400">Total Accesses</Text>
                <Text className="text-2xl font-bold">{stats.total_accesses || 0}</Text>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div className="container mx-auto px-6 py-4">
          <div className="flex gap-4 items-center">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
              <Input
                type="text"
                placeholder="Search memories semantically..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10"
              />
            </div>
            
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              className="px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-md bg-white dark:bg-zinc-800"
            >
              <option value="">All Users</option>
              <option value="1">User 1</option>
              <option value="2">User 2</option>
            </select>

            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-md bg-white dark:bg-zinc-800"
            >
              <option value="">All Categories</option>
              <option value="products">Products</option>
              <option value="preferences">Preferences</option>
              <option value="interactions">Interactions</option>
              <option value="facts">Facts</option>
              <option value="problems">Problems</option>
              <option value="solutions">Solutions</option>
              <option value="general">General</option>
            </select>

            <select
              value={minImportance}
              onChange={(e) => setMinImportance(parseFloat(e.target.value))}
              className="px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-md bg-white dark:bg-zinc-800"
            >
              <option value="0">All Importance</option>
              <option value="0.3">Low+ (≥0.3)</option>
              <option value="0.5">Medium+ (≥0.5)</option>
              <option value="0.7">High+ (≥0.7)</option>
              <option value="0.9">Critical (≥0.9)</option>
            </select>

            <Button onClick={fetchMemories} outline>
              <RefreshCw className="h-4 w-4" />
            </Button>

            {selectedMemories.size > 0 && (
              <Button onClick={bulkDelete} color="red">
                Delete {selectedMemories.size} Selected
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Memory List */}
      <div className="container mx-auto px-6 py-6">
        {loading ? (
          <div className="text-center py-12">
            <Text className="text-zinc-500">Loading memories...</Text>
          </div>
        ) : memories.length === 0 ? (
          <div className="text-center py-12">
            <Database className="h-12 w-12 mx-auto text-zinc-400 mb-4" />
            <Text className="text-zinc-500">No memories found</Text>
            <Text className="text-sm text-zinc-400 mt-2">
              Memories are automatically extracted from conversations
            </Text>
          </div>
        ) : (
          <div className="space-y-4">
            {memories.map((memory) => (
              <div
                key={memory.id}
                className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6"
              >
                {editingMemory?.id === memory.id ? (
                  <div className="space-y-3">
                    <Textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      rows={3}
                      className="w-full"
                    />
                    <div className="flex gap-2">
                      <Button onClick={updateMemory}>Save</Button>
                      <Button 
                        onClick={() => {
                          setEditingMemory(null);
                          setEditContent('');
                        }} 
                        outline
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-4">
                    <input
                      type="checkbox"
                      checked={selectedMemories.has(memory.id)}
                      onChange={(e) => {
                        const newSet = new Set(selectedMemories);
                        if (e.target.checked) {
                          newSet.add(memory.id);
                        } else {
                          newSet.delete(memory.id);
                        }
                        setSelectedMemories(newSet);
                      }}
                      className="mt-1"
                    />
                    
                    <div className="flex-1">
                      <Text className="text-zinc-900 dark:text-zinc-100 text-base leading-relaxed">
                        {memory.content}
                      </Text>
                      
                      <div className="flex items-center gap-3 mt-3 flex-wrap">
                        <Badge color={getCategoryColor(memory.category)}>
                          <Tag className="h-3 w-3 mr-1" />
                          {memory.category}
                        </Badge>
                        
                        <Badge color={getImportanceColor(memory.importance_score)}>
                          Importance: {memory.importance_score.toFixed(1)}
                        </Badge>
                        
                        {memory.similarity_score && (
                          <Badge color="indigo">
                            Match: {(memory.similarity_score * 100).toFixed(0)}%
                          </Badge>
                        )}
                        
                        <Badge color="zinc">
                          Accessed: {memory.access_count}x
                        </Badge>
                        
                        <Text className="text-xs text-zinc-500">
                          <Calendar className="h-3 w-3 inline mr-1" />
                          {new Date(memory.created_at).toLocaleDateString()}
                        </Text>
                        
                        {memory.metadata?.agent && (
                          <Badge color="purple" small>
                            via {memory.metadata.agent}
                          </Badge>
                        )}
                      </div>
                      
                      {memory.metadata && Object.keys(memory.metadata).length > 0 && (
                        <details className="mt-2">
                          <summary className="text-sm text-zinc-600 dark:text-zinc-400 cursor-pointer">
                            Metadata
                          </summary>
                          <pre className="mt-2 p-2 bg-zinc-100 dark:bg-zinc-800 rounded text-xs overflow-x-auto">
                            {JSON.stringify(memory.metadata, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                    
                    <div className="flex gap-2">
                      <Button
                        onClick={() => {
                          setEditingMemory(memory);
                          setEditContent(memory.content);
                        }}
                        outline
                        small
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        onClick={() => deleteMemory(memory.id, memory.user_id)}
                        outline
                        color="red"
                        small
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* How Memories Work Info Box */}
      <div className="container mx-auto px-6 pb-6">
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <Heading level={3} className="flex items-center gap-2 mb-3">
            <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            How Memory Extraction Works
          </Heading>
          <div className="space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
            <Text>• <strong>Automatic Extraction:</strong> After each conversation, GPT-5-mini analyzes the messages to extract important information</Text>
            <Text>• <strong>Categories:</strong> Memories are classified into 7 types: preferences, facts, problems, solutions, products, interactions, and general</Text>
            <Text>• <strong>Deduplication:</strong> 4-layer system prevents duplicate memories (exact hash → fuzzy match → key phrases → semantic similarity)</Text>
            <Text>• <strong>Semantic Search:</strong> Memories are embedded using text-embedding-3-large for similarity search</Text>
            <Text>• <strong>Context Building:</strong> Relevant memories are automatically retrieved for agents based on conversation context</Text>
            <Text>• <strong>Importance Scoring:</strong> Each memory has an importance score (0.1-1.0) that affects retrieval priority</Text>
          </div>
        </div>
      </div>
    </div>
  );
}