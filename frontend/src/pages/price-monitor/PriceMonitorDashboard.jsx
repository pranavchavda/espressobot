import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
import { useToast } from '@common/toast';

export default function PriceMonitorDashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncLoading, setSyncLoading] = useState(false);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [scrapingLoading, setScrapingLoading] = useState(false);
  const { toast } = useToast();

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/price-monitor/dashboard/overview');
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      } else {
        toast.error('Failed to load dashboard data');
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Error loading dashboard');
    } finally {
      setLoading(false);
    }
  };

  const syncShopifyProducts = async () => {
    try {
      setSyncLoading(true);
      const response = await fetch('/api/price-monitor/shopify-sync/sync-idc-products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true })
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Synced ${result.total_synced} products successfully`);
        fetchDashboardData(); // Refresh dashboard
      } else {
        toast.error('Failed to sync Shopify products');
      }
    } catch (error) {
      console.error('Error syncing products:', error);
      toast.error('Error syncing products');
    } finally {
      setSyncLoading(false);
    }
  };

  const runProductMatching = async () => {
    try {
      setMatchingLoading(true);
      const response = await fetch('/api/price-monitor/product-matching/auto-match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          min_confidence: 'medium', 
          dry_run: false
        })
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Found ${result.matches_found} product matches`);
        fetchDashboardData(); // Refresh dashboard
      } else {
        toast.error('Failed to run product matching');
      }
    } catch (error) {
      console.error('Error running product matching:', error);
      toast.error('Error running product matching');
    } finally {
      setMatchingLoading(false);
    }
  };

  const runCompetitorScraping = async () => {
    try {
      setScrapingLoading(true);
      // Get the first active competitor for demo
      const competitorsResponse = await fetch('/api/price-monitor/competitors');
      if (!competitorsResponse.ok) {
        throw new Error('Failed to fetch competitors');
      }
      
      const competitorsData = await competitorsResponse.json();
      const activeCompetitor = competitorsData.competitors.find(c => c.is_active);
      
      if (!activeCompetitor) {
        toast.error('No active competitors found');
        return;
      }

      const response = await fetch('/api/price-monitor/scraping/start-scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          competitor_id: activeCompetitor.id,
          collections: activeCompetitor.collections.slice(0, 2) // Limit to first 2 collections
        })
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Started scraping job for ${activeCompetitor.name}`);
        fetchDashboardData(); // Refresh dashboard
      } else {
        toast.error('Failed to start competitor scraping');
      }
    } catch (error) {
      console.error('Error running competitor scraping:', error);
      toast.error('Error running competitor scraping');
    } finally {
      setScrapingLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <Heading level="1">MAP Enforcement Dashboard</Heading>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <div className="ml-4 text-gray-500 dark:text-gray-400">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 md:mb-8 gap-4">
        <div>
          <Heading level="1">MAP Enforcement Dashboard</Heading>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Monitor competitor pricing compliance and MAP violations
          </p>
        </div>
        <Button 
          onClick={fetchDashboardData} 
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white w-full sm:w-auto"
        >
          Refresh
        </Button>
      </div>

      {/* Stats Grid */}
      {dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <div className="text-3xl font-bold text-blue-600">{dashboardData.total_idc_products || 0}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">IDC Products</div>
            <div className="text-xs text-gray-500 mt-1">Monitored products</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <div className="text-3xl font-bold text-green-600">{dashboardData.total_competitor_products || 0}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Competitor Products</div>
            <div className="text-xs text-gray-500 mt-1">From all competitors</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <div className="text-3xl font-bold text-orange-600">{dashboardData.total_matches || 0}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Product Matches</div>
            <div className="text-xs text-gray-500 mt-1">AI-powered matching</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <div className="text-3xl font-bold text-red-600">{dashboardData.active_violations || 0}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Active Violations</div>
            <div className="text-xs text-gray-500 mt-1">MAP violations</div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2">Sync Shopify Products</h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
            Import products from your Shopify store and generate embeddings for semantic matching.
          </p>
          <Button 
            onClick={syncShopifyProducts} 
            disabled={syncLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          >
            {syncLoading ? 'Syncing...' : 'Sync Products'}
          </Button>
        </div>

        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2">Run Product Matching</h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
            Use AI embeddings to match your products with competitor products.
          </p>
          <Button 
            onClick={runProductMatching} 
            disabled={matchingLoading}
            className="w-full bg-green-600 hover:bg-green-700 text-white"
          >
            {matchingLoading ? 'Matching...' : 'Match Products'}
          </Button>
        </div>

        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2">Scrape Competitors</h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
            Scrape competitor websites to collect product data and pricing information.
          </p>
          <Button 
            onClick={runCompetitorScraping} 
            disabled={scrapingLoading}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white"
          >
            {scrapingLoading ? 'Scraping...' : 'Start Scraping'}
          </Button>
        </div>
      </div>

      {/* Recent Activity */}
      {dashboardData?.recent_activity && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {dashboardData.recent_activity.map((activity, index) => (
              <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">{activity.title}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">{activity.description}</div>
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {new Date(activity.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!dashboardData && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-500 dark:text-gray-400">
            <h3 className="text-lg font-medium mb-2">No data available</h3>
            <p className="mb-4">Start by syncing products from Shopify to begin monitoring.</p>
            <Button 
              onClick={syncShopifyProducts} 
              disabled={syncLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {syncLoading ? 'Syncing...' : 'Sync Products Now'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}