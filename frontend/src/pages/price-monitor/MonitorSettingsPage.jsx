import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
import { useToast } from '@common/toast';

export default function MonitorSettingsPage() {
  const [monitoredBrands, setMonitoredBrands] = useState([]);
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [competitorsLoading, setCompetitorsLoading] = useState(false);
  const [showAddBrandForm, setShowAddBrandForm] = useState(false);
  const [showAddCompetitorForm, setShowAddCompetitorForm] = useState(false);
  const [newBrandName, setNewBrandName] = useState('');
  const [newCompetitor, setNewCompetitor] = useState({ name: '', domain: '', collections: '' });
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();

  const fetchMonitoredBrands = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/price-monitor/settings/monitored-brands');
      if (response.ok) {
        const data = await response.json();
        setMonitoredBrands(data.brands || []);
      } else {
        toast.error('Failed to fetch monitored brands');
      }
    } catch (error) {
      console.error('Error fetching monitored brands:', error);
      toast.error('Error loading monitored brands');
    } finally {
      setLoading(false);
    }
  };

  const fetchCompetitors = async () => {
    try {
      setCompetitorsLoading(true);
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
      setCompetitorsLoading(false);
    }
  };

  const addBrand = async (e) => {
    e.preventDefault();
    if (!newBrandName.trim()) {
      toast.error('Please enter a brand name');
      return;
    }

    try {
      setSubmitting(true);
      const response = await fetch('/api/price-monitor/settings/monitored-brands', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_name: newBrandName.trim(),
          is_active: true
        }),
      });

      if (response.ok) {
        toast.success('Brand added successfully');
        setNewBrandName('');
        setShowAddBrandForm(false);
        fetchMonitoredBrands();
      } else {
        const error = await response.json();
        toast.error(error.error || 'Failed to add brand');
      }
    } catch (error) {
      console.error('Error adding brand:', error);
      toast.error('Error adding brand');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleBrand = async (brandId, currentStatus) => {
    try {
      const response = await fetch(`/api/price-monitor/settings/monitored-brands/${brandId}/toggle`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_active: !currentStatus
        }),
      });

      if (response.ok) {
        toast.success(`Brand ${!currentStatus ? 'activated' : 'deactivated'} successfully`);
        fetchMonitoredBrands();
      } else {
        toast.error('Failed to update brand status');
      }
    } catch (error) {
      console.error('Error toggling brand:', error);
      toast.error('Error updating brand status');
    }
  };

  const deleteBrand = async (brandId, brandName) => {
    if (!confirm(`Are you sure you want to delete "${brandName}"? This will remove all associated product data.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/price-monitor/settings/monitored-brands/${brandId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast.success('Brand deleted successfully');
        fetchMonitoredBrands();
      } else {
        toast.error('Failed to delete brand');
      }
    } catch (error) {
      console.error('Error deleting brand:', error);
      toast.error('Error deleting brand');
    }
  };

  const addCompetitor = async (e) => {
    e.preventDefault();
    if (!newCompetitor.name.trim() || !newCompetitor.domain.trim()) {
      toast.error('Please enter competitor name and domain');
      return;
    }

    try {
      setSubmitting(true);
      const collections = newCompetitor.collections.split(',').map(c => c.trim()).filter(c => c);
      
      const response = await fetch('/api/price-monitor/competitors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newCompetitor.name.trim(),
          domain: newCompetitor.domain.trim().replace(/^https?:\/\//, '').replace(/\/$/, ''),
          collections: collections.length > 0 ? collections : ['products'],
          is_active: true
        }),
      });

      if (response.ok) {
        toast.success('Competitor added successfully');
        setNewCompetitor({ name: '', domain: '', collections: '' });
        setShowAddCompetitorForm(false);
        fetchCompetitors();
      } else {
        const error = await response.json();
        toast.error(error.error || 'Failed to add competitor');
      }
    } catch (error) {
      console.error('Error adding competitor:', error);
      toast.error('Error adding competitor');
    } finally {
      setSubmitting(false);
    }
  };

  const runScraping = async (competitorId, competitorName) => {
    try {
      const response = await fetch('/api/price-monitor/scraping/start-scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ competitor_id: competitorId })
      });

      if (response.ok) {
        toast.success(`Started scraping ${competitorName}`);
      } else {
        toast.error('Failed to start scraping');
      }
    } catch (error) {
      console.error('Error starting scraping:', error);
      toast.error('Error starting scraping');
    }
  };

  useEffect(() => {
    fetchMonitoredBrands();
    fetchCompetitors();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <div className="ml-4 text-gray-500 dark:text-gray-400">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <Heading level="1">Monitor Settings</Heading>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Configure which brands to monitor for MAP compliance from your iDC store
        </p>
      </div>

      {/* Monitored Brands Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Monitored Brands
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Select which brands to monitor for MAP compliance. Products from these brands will be synchronized from your Shopify store.
            </p>
          </div>
          <Button 
            onClick={() => setShowAddBrandForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            Add Brand
          </Button>
        </div>

        {monitoredBrands.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {monitoredBrands.map((brand) => (
              <div 
                key={brand.id}
                className="flex flex-col p-4 border border-gray-200 dark:border-gray-600 rounded-lg min-h-[120px]"
              >
                <div className="flex items-center mb-3">
                  <input
                    type="checkbox"
                    checked={brand.is_active}
                    onChange={() => toggleBrand(brand.id, brand.is_active)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <div className="ml-3 flex-1">
                    <label className="text-sm font-medium text-gray-900 dark:text-white block">
                      {brand.brand_name}
                    </label>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {brand._count?.idc_products || 0} products
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-auto">
                  <Badge color={brand.is_active ? 'green' : 'gray'}>
                    {brand.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                  <Button
                    size="sm"
                    color="red"
                    outline
                    onClick={() => deleteBrand(brand.id, brand.brand_name)}
                    className="ml-2"
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              No brands configured for monitoring
            </p>
            <Button 
              onClick={() => setShowAddBrandForm(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Add Your First Brand
            </Button>
          </div>
        )}

        {/* Add Brand Form */}
        {showAddBrandForm && (
          <div className="mt-6 p-4 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700">
            <h4 className="text-md font-medium text-gray-900 dark:text-white mb-3">
              Add New Brand to Monitor
            </h4>
            <form onSubmit={addBrand} className="flex gap-3">
              <input
                type="text"
                value={newBrandName}
                onChange={(e) => setNewBrandName(e.target.value)}
                placeholder="e.g., ECM, Profitec, Eureka"
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
                required
              />
              <Button
                type="submit"
                disabled={submitting}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {submitting ? 'Adding...' : 'Add'}
              </Button>
              <Button
                type="button"
                outline
                onClick={() => {
                  setShowAddBrandForm(false);
                  setNewBrandName('');
                }}
              >
                Cancel
              </Button>
            </form>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Brand names should match the vendor names in your Shopify store exactly.
            </p>
          </div>
        )}
      </div>

      {/* Competitors Management */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Competitor Management
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Configure competitors to monitor for pricing data
            </p>
          </div>
          <Button 
            onClick={() => setShowAddCompetitorForm(true)}
            className="bg-purple-600 hover:bg-purple-700 text-white"
          >
            Add Competitor
          </Button>
        </div>

        {competitorsLoading ? (
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        ) : competitors.length > 0 ? (
          <div className="space-y-4">
            {competitors.map((competitor) => (
              <div 
                key={competitor.id}
                className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-600 rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                        {competitor.name}
                      </h4>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {competitor.domain}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Collections: {competitor.collections?.join(', ') || 'None'}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Products: {competitor.total_products || 0} • 
                        Last scraped: {competitor.last_scraped_at 
                          ? new Date(competitor.last_scraped_at).toLocaleDateString() 
                          : 'Never'}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge color={competitor.is_active ? 'green' : 'gray'}>
                        {competitor.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                      <Button
                        size="sm"
                        onClick={() => runScraping(competitor.id, competitor.name)}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        Scrape Now
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              No competitors configured
            </p>
            <Button 
              onClick={() => setShowAddCompetitorForm(true)}
              className="bg-purple-600 hover:bg-purple-700 text-white"
            >
              Add Your First Competitor
            </Button>
          </div>
        )}

        {/* Add Competitor Form */}
        {showAddCompetitorForm && (
          <div className="mt-6 p-4 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700">
            <h4 className="text-md font-medium text-gray-900 dark:text-white mb-3">
              Add New Competitor
            </h4>
            <form onSubmit={addCompetitor} className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input
                  type="text"
                  value={newCompetitor.name}
                  onChange={(e) => setNewCompetitor({...newCompetitor, name: e.target.value})}
                  placeholder="Competitor name (e.g., Whole Latte Love)"
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
                  required
                />
                <input
                  type="text"
                  value={newCompetitor.domain}
                  onChange={(e) => setNewCompetitor({...newCompetitor, domain: e.target.value})}
                  placeholder="Domain (e.g., wholelattelove.com)"
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
                  required
                />
              </div>
              <input
                type="text"
                value={newCompetitor.collections}
                onChange={(e) => setNewCompetitor({...newCompetitor, collections: e.target.value})}
                placeholder="Collections to scrape (e.g., ecm, espresso-machines)"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
              />
              <div className="flex gap-3">
                <Button
                  type="submit"
                  disabled={submitting}
                  className="bg-purple-600 hover:bg-purple-700 text-white"
                >
                  {submitting ? 'Adding...' : 'Add Competitor'}
                </Button>
                <Button
                  type="button"
                  outline
                  onClick={() => {
                    setShowAddCompetitorForm(false);
                    setNewCompetitor({ name: '', domain: '', collections: '' });
                  }}
                >
                  Cancel
                </Button>
              </div>
            </form>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Collections are paths like 'ecm' or 'espresso-machines' that exist on the competitor's website.
            </p>
          </div>
        )}
      </div>

      {/* Sync Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Synchronization
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Sync products from your Shopify store for the monitored brands.
        </p>
        <Button 
          onClick={async () => {
            try {
              const activeBrands = monitoredBrands.filter(b => b.is_active).map(b => b.brand_name);
              if (activeBrands.length === 0) {
                toast.error('No active brands to sync');
                return;
              }

              const response = await fetch('/api/price-monitor/shopify-sync-safe/sync-idc-products-safe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ brands: activeBrands, force: true })
              });

              if (response.ok) {
                const result = await response.json();
                toast.success(`Synced products: ${result.total_products_created} created, ${result.total_products_updated} updated, ${result.manual_matches_preserved} manual matches preserved`);
              } else {
                toast.error('Failed to sync products');
              }
            } catch (error) {
              console.error('Error syncing products:', error);
              toast.error('Error syncing products');
            }
          }}
          className="bg-green-600 hover:bg-green-700 text-white"
        >
          Sync Products from Shopify
        </Button>
      </div>
    </div>
  );
}