import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
import { useToast } from '@common/toast';
import {
  ArchiveBoxIcon,
  BuildingStorefrontIcon,
  Square2StackIcon,
  ExclamationTriangleIcon,
  ShoppingBagIcon,
  SparklesIcon,
  GlobeAltIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/20/solid';

export default function PriceMonitorDashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncLoading, setSyncLoading] = useState(false);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [scrapingLoading, setScrapingLoading] = useState(false);
  const [violationScanLoading, setViolationScanLoading] = useState(false);
  const [matchingThreshold, setMatchingThreshold] = useState('medium'); // New state for threshold
  const [lastRuns, setLastRuns] = useState({});
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

  const fetchLastRuns = async () => {
    try {
      const response = await fetch('/api/price-monitor/job-status/last-runs');
      if (response.ok) {
        const data = await response.json();
        setLastRuns(data);
      }
    } catch (error) {
      console.error('Error fetching last runs:', error);
    }
  };

  const formatLastRun = (lastRun) => {
    if (!lastRun) return 'Never';
    
    const date = new Date(lastRun.executed_at);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffMins < 60) {
      return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  // Badge color by recency for better at-a-glance status
  const getLastRunBadgeColor = (lastRun) => {
    if (!lastRun) return 'zinc';
    const date = new Date(lastRun.executed_at);
    const diffMs = Date.now() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    if (diffMins < 60) return 'green';
    if (diffMins < 60 * 24) return 'amber';
    return 'red';
  };

  const recordJobExecution = async (jobType) => {
    try {
      await fetch('/api/price-monitor/job-status/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_type: jobType, status: 'completed' })
      });
      // Refresh last runs
      fetchLastRuns();
    } catch (error) {
      console.error('Error recording job execution:', error);
    }
  };


  const syncShopifyProducts = async () => {
    try {
      setSyncLoading(true);
      const response = await fetch('/api/price-monitor/shopify-sync-safe/sync-idc-products-safe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true })
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Safe sync complete: ${result.total_products_created} created, ${result.total_products_updated} updated`);
        await recordJobExecution('shopify_sync');
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
          min_confidence: matchingThreshold, 
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
        await recordJobExecution('competitor_scrape');
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

  const scanForViolations = async () => {
    try {
      setViolationScanLoading(true);
      const response = await fetch('/api/price-monitor/map-violations/scan-violations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          create_alerts: true,
          dry_run: false
        })
      });

      if (response.ok) {
        const result = await response.json();
        const violationsMsg = result.violations_found === 1 ? 'violation' : 'violations';
        toast.success(`Found ${result.violations_found} MAP ${violationsMsg} from ${result.total_matches_scanned} matches`);
        await recordJobExecution('violation_scan');
        fetchDashboardData(); // Refresh dashboard
      } else {
        toast.error('Failed to scan for violations');
      }
    } catch (error) {
      console.error('Error scanning for violations:', error);
      toast.error('Error scanning for violations');
    } finally {
      setViolationScanLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    fetchLastRuns();
  }, []);

  if (loading) {
    return (
      <div className="p-4 md:p-6 bg-zinc-50 dark:bg-zinc-950 min-h-[calc(100vh-56px)]">
        <Heading level="1">MAP Enforcement Dashboard</Heading>
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 bg-white dark:bg-zinc-900 p-6">
              <div className="h-5 w-20 rounded bg-zinc-200 dark:bg-zinc-800 mb-4" />
              <div className="h-8 w-24 rounded bg-zinc-200 dark:bg-zinc-800" />
            </div>
          ))}
        </div>
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 bg-white dark:bg-zinc-900 p-6 h-32" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 bg-zinc-50 dark:bg-zinc-950 min-h-[calc(100vh-56px)]">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 md:mb-8 gap-4">
        <div>
          <Heading level="1">MAP Enforcement Dashboard</Heading>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Monitor competitor pricing compliance and MAP violations
          </p>
          {lastRuns.cron_job && (
            <div className="mt-2">
              <Badge color={getLastRunBadgeColor(lastRuns.cron_job)} className="align-middle">
                🕐 Automated sync: {formatLastRun(lastRuns.cron_job)}
              </Badge>
            </div>
          )}
        </div>
        <Button 
          onClick={fetchDashboardData} 
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-700 text-white w-full sm:w-auto transition-colors focus-visible:ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-zinc-900"
        >
          Refresh
        </Button>
      </div>

      {/* Stats Grid */}
      {dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6 shadow-sm hover:shadow-md transition-shadow hover:-translate-y-0.5 transition-transform">
            <div className="flex items-center justify-between mb-3">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-600">
                <ArchiveBoxIcon className="h-5 w-5" />
              </span>
            </div>
            <div className="text-5xl font-semibold tracking-tight text-indigo-600">{dashboardData.total_idc_products || 0}</div>
            <div className="text-xs uppercase text-zinc-500 dark:text-zinc-400 mt-1">IDC Products</div>
            <div className="text-xs text-zinc-500 mt-1">Monitored products</div>
          </div>
          
          <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6 shadow-sm hover:shadow-md transition-shadow hover:-translate-y-0.5 transition-transform">
            <div className="flex items-center justify-between mb-3">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-green-500/10 text-green-600">
                <BuildingStorefrontIcon className="h-5 w-5" />
              </span>
            </div>
            <div className="text-5xl font-semibold tracking-tight text-green-600">{dashboardData.total_competitor_products || 0}</div>
            <div className="text-xs uppercase text-zinc-500 dark:text-zinc-400 mt-1">Competitor Products</div>
            <div className="text-xs text-zinc-500 mt-1">From all competitors</div>
          </div>
          
          <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6 shadow-sm hover:shadow-md transition-shadow hover:-translate-y-0.5 transition-transform">
            <div className="flex items-center justify-between mb-3">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-orange-500/10 text-orange-600">
                <Square2StackIcon className="h-5 w-5" />
              </span>
            </div>
            <div className="text-5xl font-semibold tracking-tight text-orange-600">{dashboardData.total_matches || 0}</div>
            <div className="text-xs uppercase text-zinc-500 dark:text-zinc-400 mt-1">Product Matches</div>
            <div className="text-xs text-zinc-500 mt-1">AI-powered matching</div>
          </div>
          
          <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6 shadow-sm hover:shadow-md transition-shadow hover:-translate-y-0.5 transition-transform">
            <div className="flex items-center justify-between mb-3">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-red-500/10 text-red-600">
                <ExclamationTriangleIcon className="h-5 w-5" />
              </span>
            </div>
            <div className="text-5xl font-semibold tracking-tight text-red-600">{dashboardData.active_violations || 0}</div>
            <div className="text-xs uppercase text-zinc-500 dark:text-zinc-400 mt-1">Active Violations</div>
            <div className="text-xs text-zinc-500 mt-1">MAP violations</div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-6 md:mb-8">
        <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6 shadow-sm hover:shadow-md transition-shadow hover:-translate-y-0.5 transition-transform">
          <div className="-mt-6 -mx-6 mb-4 h-1.5 rounded-t-xl bg-gradient-to-r from-indigo-500/60 to-transparent" />
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600">
              <ShoppingBagIcon className="h-5 w-5" />
            </span>
            <h3 className="text-lg font-semibold">Sync Shopify Products</h3>
          </div>
          <p className="text-zinc-600 dark:text-zinc-400 text-sm mb-4">
            Import products from your Shopify store and generate embeddings for semantic matching.
          </p>
          {lastRuns.shopify_sync && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-3">
              Last run: {formatLastRun(lastRuns.shopify_sync)}
            </p>
          )}
          <Button 
            onClick={syncShopifyProducts} 
            disabled={syncLoading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white transition-colors focus-visible:ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-zinc-900"
          >
            {syncLoading ? 'Syncing...' : 'Sync Products'}
          </Button>
        </div>
        
        <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6 shadow-sm hover:shadow-md transition-shadow hover:-translate-y-0.5 transition-transform">
          <div className="-mt-6 -mx-6 mb-4 h-1.5 rounded-t-xl bg-gradient-to-r from-indigo-500/60 to-transparent" />
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600">
              <SparklesIcon className="h-5 w-5" />
            </span>
            <h3 className="text-lg font-semibold">Run Product Matching</h3>
          </div>
          <p className="text-zinc-600 dark:text-zinc-400 text-sm mb-4">
            Use AI embeddings to match your products with competitor products.
          </p>
          
          {/* Confidence Threshold Segmented Control */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
              Confidence Threshold
            </label>
            <div className="inline-flex rounded-lg bg-zinc-100 dark:bg-zinc-800 p-1">
              <button
                type="button"
                disabled={matchingLoading}
                onClick={() => setMatchingThreshold('low')}
                className={`${matchingThreshold === 'low' ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white shadow ring-1 ring-zinc-200 dark:ring-zinc-700' : 'text-zinc-600 dark:text-zinc-300'} px-3 py-1.5 text-sm rounded-md transition-colors`}
              >
                Low
              </button>
              <button
                type="button"
                disabled={matchingLoading}
                onClick={() => setMatchingThreshold('medium')}
                className={`${matchingThreshold === 'medium' ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white shadow ring-1 ring-zinc-200 dark:ring-zinc-700' : 'text-zinc-600 dark:text-zinc-300'} px-3 py-1.5 text-sm rounded-md transition-colors`}
              >
                Medium
              </button>
              <button
                type="button"
                disabled={matchingLoading}
                onClick={() => setMatchingThreshold('high')}
                className={`${matchingThreshold === 'high' ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white shadow ring-1 ring-zinc-200 dark:ring-zinc-700' : 'text-zinc-600 dark:text-zinc-300'} px-3 py-1.5 text-sm rounded-md transition-colors`}
              >
                High
              </button>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              {matchingThreshold === 'low' && 'Find more potential matches, may include false positives'}
              {matchingThreshold === 'medium' && 'Recommended balance between precision and recall'}
              {matchingThreshold === 'high' && 'Only very confident matches, may miss some valid matches'}
            </p>
          </div>
          
          <Button 
            onClick={runProductMatching} 
            disabled={matchingLoading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white transition-colors focus-visible:ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-zinc-900"
          >
            {matchingLoading ? 'Matching...' : `Match Products (${matchingThreshold} confidence)`}
          </Button>
        </div>
        
        <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6 shadow-sm hover:shadow-md transition-shadow hover:-translate-y-0.5 transition-transform">
          <div className="-mt-6 -mx-6 mb-4 h-1.5 rounded-t-xl bg-gradient-to-r from-purple-500/60 to-transparent" />
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-600">
              <GlobeAltIcon className="h-5 w-5" />
            </span>
            <h3 className="text-lg font-semibold">Scrape Competitors</h3>
          </div>
          <p className="text-zinc-600 dark:text-zinc-400 text-sm mb-4">
            Scrape competitor websites to collect product data and pricing information.
          </p>
          {lastRuns.competitor_scrape && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-3">
              Last run: {formatLastRun(lastRuns.competitor_scrape)}
            </p>
          )}
          <Button 
            onClick={runCompetitorScraping} 
            disabled={scrapingLoading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white transition-colors focus-visible:ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-zinc-900"
          >
            {scrapingLoading ? 'Scraping...' : 'Start Scraping'}
          </Button>
        </div>
        
        <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6 shadow-sm hover:shadow-md transition-shadow hover:-translate-y-0.5 transition-transform">
          <div className="-mt-6 -mx-6 mb-4 h-1.5 rounded-t-xl bg-gradient-to-r from-red-500/60 to-transparent" />
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-500/10 text-red-600">
              <ShieldExclamationIcon className="h-5 w-5" />
            </span>
            <h3 className="text-lg font-semibold">Scan for Violations</h3>
          </div>
          <p className="text-zinc-600 dark:text-zinc-400 text-sm mb-4">
            Scan existing product matches for MAP pricing violations and generate alerts.
          </p>
          {lastRuns.violation_scan && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-3">
              Last run: {formatLastRun(lastRuns.violation_scan)}
            </p>
          )}
          <Button 
            onClick={scanForViolations} 
            disabled={violationScanLoading}
            className="w-full bg-red-600 hover:bg-red-700 text-white transition-colors focus-visible:ring-2 ring-red-500 ring-offset-2 dark:ring-offset-zinc-900"
          >
            {violationScanLoading ? 'Scanning...' : 'Scan Violations'}
          </Button>
        </div>
      </div>

      {/* Recent Activity */}
      {dashboardData?.recent_activity && (
        <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
          <div className="relative">
            <div className="absolute left-3 top-0 bottom-0 w-px bg-zinc-200 dark:bg-zinc-800" />
            <div className="space-y-4">
              {dashboardData.recent_activity.map((activity, index) => (
                <div key={index} className="relative pl-8">
                  <span className="absolute left-[9px] top-2 h-2.5 w-2.5 rounded-full bg-zinc-400 ring-2 ring-white dark:ring-zinc-900" />
                  <div className="font-medium text-zinc-900 dark:text-white">{activity.title}</div>
                  <div className="text-sm text-zinc-500 dark:text-zinc-400">{activity.description}</div>
                  <div className="text-xs text-zinc-400 mt-1">{new Date(activity.created_at).toLocaleDateString()}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {!dashboardData && (
        <div className="bg-white dark:bg-zinc-900 rounded-xl ring-1 ring-zinc-200 dark:ring-zinc-800 p-12 text-center">
          <div className="text-zinc-500 dark:text-zinc-400">
            <h3 className="text-lg font-medium mb-2">No data available</h3>
            <p className="mb-4">Start by syncing products from Shopify to begin monitoring.</p>
            <Button 
              onClick={syncShopifyProducts} 
              disabled={syncLoading}
              className="bg-indigo-600 hover:bg-indigo-700 text-white transition-colors focus-visible:ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-zinc-900"
            >
              {syncLoading ? 'Syncing...' : 'Sync Products Now'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}