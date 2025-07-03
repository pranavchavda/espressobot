import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@common/button';
import { Input } from '@common/input';
import { Field, Label } from '@common/fieldset';
import { Select } from '@common/select';
import { Textarea } from '@common/textarea';
import { Badge } from '@common/badge';
import { Dialog, DialogTitle, DialogDescription, DialogActions } from '@common/dialog';
import { Alert } from '@common/alert';
import { Heading } from '@common/heading';
import { Divider } from '@common/divider';
import { Plus, Search, Download, Upload, Edit, Trash2, ChevronLeft } from 'lucide-react';
import { useToast } from '@common/toast';

const CATEGORIES = ['tools', 'workflows', 'constraints', 'patterns', 'errors', 'domain', 'general'];
const AGENT_TYPES = ['all', 'orchestrator', 'bash', 'swe'];
const PRIORITIES = ['high', 'medium', 'low'];

export default function PromptLibraryManager() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [fragments, setFragments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    category: 'all',
    agent_type: 'all',
    priority: 'all'
  });
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingFragment, setEditingFragment] = useState(null);
  const [formData, setFormData] = useState({
    fragment: '',
    category: 'general',
    priority: 'medium',
    agent_type: 'all',
    tags: ''
  });
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchFragments();
    fetchStats();
  }, [filters]);

  const fetchFragments = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const params = new URLSearchParams();
      if (filters.category !== 'all') params.append('category', filters.category);
      if (filters.agent_type !== 'all') params.append('agent_type', filters.agent_type);
      if (filters.priority !== 'all') params.append('priority', filters.priority);

      const response = await fetch(`/api/prompt-library?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      if (data.success) {
        setFragments(data.fragments);
      } else {
        toast.error('Failed to load fragments');
      }
    } catch (error) {
      toast.error('Error loading fragments');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/prompt-library/stats', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchFragments();
      return;
    }

    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/prompt-library/search?query=${encodeURIComponent(searchQuery)}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      if (data.success) {
        setFragments(data.fragments);
      }
    } catch (error) {
      toast.error('Search failed');
    }
  };

  const handleAdd = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/prompt-library', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(',').map(t => t.trim()).filter(t => t)
        })
      });
      
      const data = await response.json();
      if (data.success) {
        toast.success('Fragment added successfully');
        setShowAddModal(false);
        resetForm();
        fetchFragments();
        fetchStats();
      } else {
        toast.error(data.error || 'Failed to add fragment');
      }
    } catch (error) {
      toast.error('Error adding fragment');
    }
  };

  const handleUpdate = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/prompt-library/${editingFragment.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(',').map(t => t.trim()).filter(t => t)
        })
      });
      
      const data = await response.json();
      if (data.success) {
        toast.success('Fragment updated successfully');
        setEditingFragment(null);
        resetForm();
        fetchFragments();
      } else {
        toast.error(data.error || 'Failed to update fragment');
      }
    } catch (error) {
      toast.error('Error updating fragment');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this fragment?')) return;
    
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/prompt-library/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      if (data.success) {
        toast.success('Fragment deleted successfully');
        fetchFragments();
        fetchStats();
      } else {
        toast.error('Failed to delete fragment');
      }
    } catch (error) {
      toast.error('Error deleting fragment');
    }
  };

  const handleExport = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/prompt-library/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          category: filters.category !== 'all' ? filters.category : undefined,
          agent_type: filters.agent_type !== 'all' ? filters.agent_type : undefined
        })
      });
      
      const data = await response.json();
      if (data.success) {
        const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `prompt-library-export-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success(`Exported ${data.count} fragments`);
      }
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const handleImport = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const token = localStorage.getItem('authToken');
      
      const response = await fetch('/api/prompt-library/import', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ data, mode: 'merge' })
      });
      
      const result = await response.json();
      if (result.success) {
        toast.success(`Imported ${result.imported} fragments`);
        fetchFragments();
        fetchStats();
      } else {
        toast.error('Import failed');
      }
    } catch (error) {
      toast.error('Invalid import file');
    }
    
    event.target.value = '';
  };

  const resetForm = () => {
    setFormData({
      fragment: '',
      category: 'general',
      priority: 'medium',
      agent_type: 'all',
      tags: ''
    });
  };

  const openEditModal = (fragment) => {
    setEditingFragment(fragment);
    setFormData({
      fragment: fragment.memory,
      category: fragment.metadata?.category || 'general',
      priority: fragment.metadata?.priority || 'medium',
      agent_type: fragment.metadata?.agent_type || 'all',
      tags: (fragment.metadata?.tags || []).join(', ')
    });
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      {/* Header */}
      <div className="mb-6 flex justify-between items-start">
        <div>
          <Button
            onClick={() => navigate('/admin')}
            outline
            className="mb-4 text-sm"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back to Admin
          </Button>
          <Heading level={1}>Prompt Library Manager</Heading>
          <p className="text-zinc-600 dark:text-zinc-400 mt-2">
            Manage system prompt fragments for RAG-enhanced agent instructions
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowAddModal(true)} color="blue">
            <Plus className="w-4 h-4 mr-2" />
            Add Fragment
          </Button>
          <Button onClick={handleExport} outline>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Field className="cursor-pointer">
            <Label>
              <Button outline>
                <Upload className="w-4 h-4 mr-2" />
                Import
              </Button>
              <Input
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleImport}
              />
            </Label>
          </Field>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-zinc-100 dark:bg-zinc-800 p-4 rounded-lg">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">Total Fragments</div>
          </div>
          <div className="bg-zinc-100 dark:bg-zinc-800 p-4 rounded-lg">
            <div className="text-2xl font-bold">{Object.keys(stats.by_category).length}</div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">Categories</div>
          </div>
          <div className="bg-zinc-100 dark:bg-zinc-800 p-4 rounded-lg">
            <div className="text-2xl font-bold">{Object.keys(stats.by_agent_type).length}</div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">Agent Types</div>
          </div>
          <div className="bg-zinc-100 dark:bg-zinc-800 p-4 rounded-lg">
            <div className="text-2xl font-bold">{stats.by_priority.high || 0}</div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">High Priority</div>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 flex gap-2">
          <Input
            placeholder="Search fragments..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button onClick={handleSearch} outline>
            <Search className="w-4 h-4" />
          </Button>
        </div>
        <Select 
          value={filters.category} 
          onChange={(e) => setFilters({...filters, category: e.target.value})}
        >
          <option value="all">All Categories</option>
          {CATEGORIES.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </Select>
        <Select 
          value={filters.agent_type} 
          onChange={(e) => setFilters({...filters, agent_type: e.target.value})}
        >
          <option value="all">All Agents</option>
          {AGENT_TYPES.map(type => (
            <option key={type} value={type}>{type}</option>
          ))}
        </Select>
        <Select 
          value={filters.priority} 
          onChange={(e) => setFilters({...filters, priority: e.target.value})}
        >
          <option value="all">All Priorities</option>
          {PRIORITIES.map(p => (
            <option key={p} value={p}>{p}</option>
          ))}
        </Select>
      </div>

      <Divider />

      {/* Fragments List */}
      <div className="mt-6">
        {loading ? (
          <div className="text-center py-8 text-zinc-500">Loading...</div>
        ) : fragments.length === 0 ? (
          <div className="text-center py-8 text-zinc-500">No fragments found</div>
        ) : (
          <div className="space-y-4">
            {fragments.map((fragment) => (
              <div key={fragment.id} className="border rounded-lg p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800">
                <div className="flex justify-between items-start">
                  <div className="flex-1 mr-4">
                    <p className="text-sm mb-2">{fragment.memory}</p>
                    <div className="flex gap-2 items-center">
                      <Badge color={fragment.metadata?.category === 'tools' ? 'blue' : 
                                   fragment.metadata?.category === 'errors' ? 'red' : 'zinc'}>
                        {fragment.metadata?.category || 'general'}
                      </Badge>
                      <Badge color="amber">
                        {fragment.metadata?.agent_type || 'all'}
                      </Badge>
                      <Badge color={fragment.metadata?.priority === 'high' ? 'red' : 
                                   fragment.metadata?.priority === 'medium' ? 'yellow' : 'green'}>
                        {fragment.metadata?.priority || 'medium'}
                      </Badge>
                      {(fragment.metadata?.tags || []).map((tag, i) => (
                        <Badge key={i} color="zinc" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      outline
                      className="text-sm py-1 px-2"
                      onClick={() => openEditModal(fragment)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      outline
                      color="red"
                      className="text-sm py-1 px-2"
                      onClick={() => handleDelete(fragment.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add/Edit Modal */}
      <Dialog open={showAddModal || !!editingFragment} onClose={() => {
        setShowAddModal(false);
        setEditingFragment(null);
        resetForm();
      }}>
        <DialogTitle>
          {editingFragment ? 'Edit Fragment' : 'Add New Fragment'}
        </DialogTitle>
        <DialogDescription>
          {editingFragment ? 'Update the prompt fragment details' : 'Create a new prompt fragment for the RAG system'}
        </DialogDescription>
        
        <div className="mt-4 space-y-4">
          <Field>
            <Label htmlFor="fragment">Fragment Content</Label>
            <Textarea
              id="fragment"
              value={formData.fragment}
              onChange={(e) => setFormData({...formData, fragment: e.target.value})}
              rows={4}
              placeholder="Enter the prompt fragment..."
            />
          </Field>
          
          <div className="grid grid-cols-3 gap-4">
            <Field>
              <Label htmlFor="category">Category</Label>
              <Select 
                id="category"
                value={formData.category} 
                onChange={(e) => setFormData({...formData, category: e.target.value})}
              >
                {CATEGORIES.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </Select>
            </Field>
            
            <Field>
              <Label htmlFor="agent_type">Agent Type</Label>
              <Select 
                id="agent_type"
                value={formData.agent_type} 
                onChange={(e) => setFormData({...formData, agent_type: e.target.value})}
              >
                {AGENT_TYPES.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </Select>
            </Field>
            
            <Field>
              <Label htmlFor="priority">Priority</Label>
              <Select 
                id="priority"
                value={formData.priority} 
                onChange={(e) => setFormData({...formData, priority: e.target.value})}
              >
                {PRIORITIES.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </Select>
            </Field>
          </div>
          
          <Field>
            <Label htmlFor="tags">Tags (comma-separated)</Label>
            <Input
              id="tags"
              value={formData.tags}
              onChange={(e) => setFormData({...formData, tags: e.target.value})}
              placeholder="bash, tools, error-handling"
            />
          </Field>
        </div>
        
        <DialogActions>
          <Button outline onClick={() => {
            setShowAddModal(false);
            setEditingFragment(null);
            resetForm();
          }}>
            Cancel
          </Button>
          <Button color="blue" onClick={editingFragment ? handleUpdate : handleAdd}>
            {editingFragment ? 'Update' : 'Add'} Fragment
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}