import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
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
    collections: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();

  const fetchCompetitors = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/price-monitor/competitors');
      if (response.ok) {
        const data = await response.json();
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
          is_active: true
        }),
      });

      if (response.ok) {
        toast.success(isEditing ? 'Competitor updated successfully' : 'Competitor added successfully');
        setShowAddForm(false);
        setShowEditForm(false);
        setEditingCompetitor(null);
        setFormData({ name: '', domain: '', collections: '' });
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
      collections: competitor.collections.join(', ')
    });
    setShowEditForm(true);
  };

  const handleCancelEdit = () => {
    setShowEditForm(false);
    setEditingCompetitor(null);
    setFormData({ name: '', domain: '', collections: '' });
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
          onClick={() => setShowAddForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          Add Competitor
        </Button>
      </div>

      {competitors.length > 0 ? (
        <div className="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Domain
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Collections
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Last Scraped
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Products
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {competitors.map((competitor) => (
                <tr key={competitor.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    {competitor.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {competitor.domain}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {competitor.collections?.join(', ') || 'None'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge color={competitor.is_active ? 'green' : 'gray'}>
                      {competitor.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {competitor.last_scraped_at 
                      ? new Date(competitor.last_scraped_at).toLocaleString()
                      : 'Never'
                    }
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {competitor.total_products || 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Button 
                      size="sm" 
                      outline 
                      className="mr-2"
                      onClick={() => handleEdit(competitor)}
                    >
                      Edit
                    </Button>
                    <Button 
                      size="sm" 
                      color="red" 
                      outline
                      onClick={() => handleDelete(competitor.id)}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-500 dark:text-gray-400">
            <h3 className="text-lg font-medium mb-2">No competitors configured</h3>
            <p className="mb-4">Add competitor sites to start monitoring their prices against your MAP policies.</p>
            <Button 
              onClick={() => setShowAddForm(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Add Your First Competitor
            </Button>
          </div>
        </div>
      )}

      {showAddForm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white dark:bg-gray-800">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Add Competitor
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
                </div>
                <div className="flex justify-end space-x-3">
                  <Button
                    type="button"
                    outline
                    onClick={() => setShowAddForm(false)}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                    disabled={submitting}
                  >
                    {submitting ? 'Adding...' : 'Add Competitor'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

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