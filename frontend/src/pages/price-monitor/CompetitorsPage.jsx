import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@common/table';
import { Dialog, DialogTitle, DialogDescription, DialogActions } from '@common/dialog';
import { Field, Label } from '@common/fieldset';
import { Input } from '@common/input';
import { Select } from '@common/select';
import { Textarea } from '@common/textarea';
import { useToast } from '@common/toast';

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingCompetitor, setEditingCompetitor] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    domain: '',
    collections: '',
    scraping_strategy: 'collections', // 'collections', 'url_patterns', 'search_terms'
    url_patterns: '',
    search_terms: '',
    exclude_patterns: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [scrapingCompetitors, setScrapingCompetitors] = useState(new Set());
  const { toast } = useToast();

  const fetchCompetitors = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/price-monitor/competitors');
      if (response.ok) {
        const data = await response.json();
        console.log('Fetched competitors:', data.competitors);
        setCompetitors(data.competitors || []);
      } else {
        toast.error('Failed to fetch competitors');
      }
    } catch (error) {
      console.error('Error fetching competitors:', error);
      toast.error('Error loading competitors');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.domain) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setSubmitting(true);
      const isEditing = editingCompetitor !== null;
      const url = isEditing 
        ? `/api/price-monitor/competitors/${editingCompetitor.id}`
        : '/api/price-monitor/competitors';
      const method = isEditing ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          domain: formData.domain,
          collections: formData.collections.split(',').map(c => c.trim()).filter(c => c),
          scraping_strategy: formData.scraping_strategy,
          url_patterns: formData.url_patterns.split('\n').map(p => p.trim()).filter(p => p),
          search_terms: formData.search_terms.split(',').map(t => t.trim()).filter(t => t),
          exclude_patterns: formData.exclude_patterns.split('\n').map(p => p.trim()).filter(p => p),
          is_active: true
        }),
      });

      if (response.ok) {
        toast.success(isEditing ? 'Competitor updated successfully' : 'Competitor added successfully');
        setShowAddForm(false);
        setShowEditForm(false);
        setEditingCompetitor(null);
        setFormData({ 
          name: '', 
          domain: '', 
          collections: '', 
          scraping_strategy: 'collections',
          url_patterns: '',
          search_terms: '',
          exclude_patterns: ''
        });
        fetchCompetitors(); // Refresh the list
      } else {
        const error = await response.json();
        toast.error(error.error || `Failed to ${isEditing ? 'update' : 'add'} competitor`);
      }
    } catch (error) {
      console.error(`Error ${editingCompetitor ? 'updating' : 'adding'} competitor:`, error);
      toast.error(`Error ${editingCompetitor ? 'updating' : 'adding'} competitor`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (competitor) => {
    setEditingCompetitor(competitor);
    setFormData({
      name: competitor.name,
      domain: competitor.domain,
      collections: competitor.collections ? competitor.collections.join(', ') : '',
      scraping_strategy: competitor.scraping_strategy || 'collections',
      url_patterns: competitor.url_patterns ? competitor.url_patterns.join('\n') : '',
      search_terms: competitor.search_terms ? competitor.search_terms.join(', ') : '',
      exclude_patterns: competitor.exclude_patterns ? competitor.exclude_patterns.join('\n') : ''
    });
    setShowEditForm(true);
  };

  const handleCancelEdit = () => {
    setShowEditForm(false);
    setEditingCompetitor(null);
    setFormData({ 
      name: '', 
      domain: '', 
      collections: '', 
      scraping_strategy: 'collections',
      url_patterns: '',
      search_terms: '',
      exclude_patterns: ''
    });
  };

  const handleDelete = async (competitorId) => {
    if (!confirm('Are you sure you want to delete this competitor?')) {
      return;
    }

    try {
      const response = await fetch(`/api/price-monitor/competitors/${competitorId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast.success('Competitor deleted successfully');
        fetchCompetitors(); // Refresh the list
      } else {
        toast.error('Failed to delete competitor');
      }
    } catch (error) {
      console.error('Error deleting competitor:', error);
      toast.error('Error deleting competitor');
    }
  };

  const handleScrape = async (competitorId, competitorName) => {
    if (scrapingCompetitors.has(competitorId)) {
      return; // Already scraping
    }

    try {
      setScrapingCompetitors(prev => new Set(prev).add(competitorId));
      
      const response = await fetch(`/api/price-monitor/scraping/start-scrape`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          competitor_id: competitorId
        }),
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(`Started scraping ${competitorName}. Job ID: ${data.job_id}`);
        
        // Poll for job completion (optional - you could also just refresh manually)
        pollJobStatus(data.job_id, competitorName);
      } else {
        const error = await response.json();
        console.error('Scrape API error:', error);
        toast.error(error.error || `Failed to start scraping ${competitorName}`);
      }
    } catch (error) {
      console.error('Error starting scrape:', error);
      toast.error(`Error starting scrape for ${competitorName}: ${error.message}`);
    } finally {
      // Remove from scraping set after a delay to prevent double-clicks
      setTimeout(() => {
        setScrapingCompetitors(prev => {
          const next = new Set(prev);
          next.delete(competitorId);
          return next;
        });
      }, 2000);
    }
  };

  const pollJobStatus = async (jobId, competitorName) => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`/api/price-monitor/scraping/job/${jobId}/status`);
        if (response.ok) {
          const job = await response.json();
          
          if (job.status === 'completed') {
            toast.success(`Scraping completed for ${competitorName}. Found ${job.products_found || 0} products.`);
            fetchCompetitors(); // Refresh to show updated product counts
            return; // Stop polling
          } else if (job.status === 'failed') {
            toast.error(`Scraping failed for ${competitorName}`);
            return; // Stop polling
          }
          
          // Still running, poll again in 3 seconds
          if (job.status === 'running') {
            setTimeout(checkStatus, 3000);
          }
        }
      } catch (error) {
        console.error('Error polling job status:', error);
      }
    };
    
    // Start polling after 2 seconds
    setTimeout(checkStatus, 2000);
  };

  useEffect(() => {
    fetchCompetitors();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <div className="ml-4 text-gray-500 dark:text-gray-400">Loading competitors...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <Heading level="1">Competitors</Heading>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Manage competitor sites for price monitoring
          </p>
        </div>
        <Button 
          color="indigo"
          onClick={() => setShowAddForm(true)}
        >
          Add Competitor
        </Button>
      </div>

      {console.log('Rendering competitors, length:', competitors.length) || competitors.length > 0 ? (
        <div className="overflow-x-auto">
          <Table striped>
          <TableHead>
            <TableRow>
              <TableHeader>Name</TableHeader>
              <TableHeader>Domain</TableHeader>
              <TableHeader>Strategy</TableHeader>
              <TableHeader>Status</TableHeader>
              <TableHeader>Last Scraped</TableHeader>
              <TableHeader>Products</TableHeader>
              <TableHeader>Actions</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {competitors.map((competitor) => (
              <TableRow key={competitor.id}>
                <TableCell className="font-medium">
                  {competitor.name}
                </TableCell>
                <TableCell className="text-zinc-500">
                  {competitor.domain}
                </TableCell>
                <TableCell>
                  <Badge color="zinc">
                    {competitor.scraping_strategy || 'collections'}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge color={competitor.is_active ? 'green' : 'gray'}>
                    {competitor.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </TableCell>
                <TableCell className="text-zinc-500">
                  {competitor.last_scraped_at 
                    ? new Date(competitor.last_scraped_at).toLocaleString()
                    : 'Never'
                  }
                </TableCell>
                <TableCell className="text-zinc-500">
                  {competitor.total_products || 0}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Button 
                      outline
                      onClick={() => handleEdit(competitor)}
                    >
                      Edit
                    </Button>
                    <Button 
                      color="emerald"
                      onClick={() => handleScrape(competitor.id, competitor.name)}
                      disabled={scrapingCompetitors.has(competitor.id) || !competitor.is_active}
                    >
                      {scrapingCompetitors.has(competitor.id) ? 'Scraping...' : 'Scrape'}
                    </Button>
                    <Button 
                      color="red"
                      outline
                      onClick={() => handleDelete(competitor.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          </Table>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-500 dark:text-gray-400">
            <h3 className="text-lg font-medium mb-2">No competitors configured</h3>
            <p className="mb-4">Add competitor sites to start monitoring their prices against your MAP policies.</p>
            <Button 
              color="indigo"
              onClick={() => setShowAddForm(true)}
            >
              Add Your First Competitor
            </Button>
          </div>
        </div>
      )}

      <Dialog open={showAddForm} onClose={() => setShowAddForm(false)}>
        <DialogTitle>Add Competitor</DialogTitle>
        <DialogDescription>
          Add a new competitor site to monitor their pricing against your MAP policies.
        </DialogDescription>
        <form id="add-competitor-form" onSubmit={handleSubmit} className="space-y-6 mt-6">
          <Field>
            <Label>Name</Label>
            <Input
              name="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Home Coffee Solutions"
              required
            />
          </Field>

          <Field>
            <Label>Domain</Label>
            <Input
              name="domain"
              value={formData.domain}
              onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
              placeholder="e.g., homecoffeesolutions.com"
              required
            />
          </Field>

          <Field>
            <Label>Scraping Strategy</Label>
            <Select
              name="scraping_strategy"
              value={formData.scraping_strategy}
              onChange={(e) => setFormData({ ...formData, scraping_strategy: e.target.value })}
            >
              <option value="collections">Collection-based (e.g., /collections/ecm)</option>
              <option value="url_patterns">URL Pattern Matching</option>
              <option value="search_terms">Search Term Based</option>
            </Select>
          </Field>

                {/* Collections (for collection-based strategy) */}
                {formData.scraping_strategy === 'collections' && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Collections to Monitor
                    </label>
                    <input
                      type="text"
                      value={formData.collections}
                      onChange={(e) => setFormData({ ...formData, collections: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="e.g., ecm,profitec,eureka (comma-separated)"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Collection names from URLs like /collections/ecm
                    </p>
                  </div>
                )}

                {/* URL Patterns (for pattern-based strategy) */}
                {formData.scraping_strategy === 'url_patterns' && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      URL Patterns to Scrape
                    </label>
                    <textarea
                      value={formData.url_patterns}
                      onChange={(e) => setFormData({ ...formData, url_patterns: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                      rows="3"
                      placeholder={`/products/ecm-*\n/espresso-machines/*\n/grinders/eureka-*`}
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      One pattern per line. Use * for wildcards. Good for sites without collections.
                    </p>
                  </div>
                )}

                {/* Search Terms (for search-based strategy) */}
                {formData.scraping_strategy === 'search_terms' && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Search Terms
                    </label>
                    <input
                      type="text"
                      value={formData.search_terms}
                      onChange={(e) => setFormData({ ...formData, search_terms: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="ECM,Profitec,Eureka,espresso machine,grinder"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Brand names and product categories to search for (comma-separated)
                    </p>
                  </div>
                )}

                {/* Exclude Patterns (common to all strategies) */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Exclude Patterns (Optional)
                  </label>
                  <textarea
                    value={formData.exclude_patterns}
                    onChange={(e) => setFormData({ ...formData, exclude_patterns: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    rows="2"
                    placeholder={`/products/sale-*\n*clearance*\n*discontinued*`}
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    URL patterns to exclude (one per line). Useful to skip sale/clearance items.
                  </p>
                </div>
        </form>
        
        <DialogActions>
          <Button plain onClick={() => setShowAddForm(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button color="indigo" type="submit" form="add-competitor-form" disabled={submitting}>
            {submitting ? 'Adding...' : 'Add Competitor'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Form Modal */}
      {showEditForm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white dark:bg-gray-800">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Edit Competitor
              </h3>
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="e.g., Home Coffee Solutions"
                    required
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Domain
                  </label>
                  <input
                    type="text"
                    value={formData.domain}
                    onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="e.g., homecoffeesolutions.com"
                    required
                  />
                </div>
                {/* Scraping Strategy Selection */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Scraping Strategy
                  </label>
                  <select
                    value={formData.scraping_strategy}
                    onChange={(e) => setFormData({ ...formData, scraping_strategy: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="collections">Collection-based (e.g., /collections/ecm)</option>
                    <option value="url_patterns">URL Pattern Matching</option>
                    <option value="search_terms">Search Term Based</option>
                  </select>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Choose how to find products on this competitor site
                  </p>
                </div>

                {/* Collections (for collection-based strategy) */}
                {formData.scraping_strategy === 'collections' && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Collections to Monitor
                    </label>
                    <input
                      type="text"
                      value={formData.collections}
                      onChange={(e) => setFormData({ ...formData, collections: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="e.g., ecm,profitec,eureka (comma-separated)"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Collection names from URLs like /collections/ecm
                    </p>
                  </div>
                )}

                {/* URL Patterns (for pattern-based strategy) */}
                {formData.scraping_strategy === 'url_patterns' && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      URL Patterns to Scrape
                    </label>
                    <textarea
                      value={formData.url_patterns}
                      onChange={(e) => setFormData({ ...formData, url_patterns: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                      rows="3"
                      placeholder={`/products/ecm-*\n/espresso-machines/*\n/grinders/eureka-*`}
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      One pattern per line. Use * for wildcards. Good for sites without collections.
                    </p>
                  </div>
                )}

                {/* Search Terms (for search-based strategy) */}
                {formData.scraping_strategy === 'search_terms' && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Search Terms
                    </label>
                    <input
                      type="text"
                      value={formData.search_terms}
                      onChange={(e) => setFormData({ ...formData, search_terms: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="ECM,Profitec,Eureka,espresso machine,grinder"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Brand names and product categories to search for (comma-separated)
                    </p>
                  </div>
                )}

                {/* Exclude Patterns (common to all strategies) */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Exclude Patterns (Optional)
                  </label>
                  <textarea
                    value={formData.exclude_patterns}
                    onChange={(e) => setFormData({ ...formData, exclude_patterns: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    rows="2"
                    placeholder={`/products/sale-*\n*clearance*\n*discontinued*`}
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    URL patterns to exclude (one per line). Useful to skip sale/clearance items.
                  </p>
                </div>
                <div className="flex justify-end space-x-3">
                  <Button
                    type="button"
                    outline
                    onClick={handleCancelEdit}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                    disabled={submitting}
                  >
                    {submitting ? 'Updating...' : 'Update Competitor'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}