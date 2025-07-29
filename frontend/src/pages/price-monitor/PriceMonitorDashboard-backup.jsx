import React, { useState, useEffect } from 'react';
import { Heading } from '@common/heading';
import { Button } from '@common/button';
import { Badge } from '@common/badge';

// Stats card component
function StatCard({ title, value, change, color = 'blue', description }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700 dark:bg-blue-900 dark:text-blue-200',
    green: 'bg-green-50 text-green-700 dark:bg-green-900 dark:text-green-200',
    red: 'bg-red-50 text-red-700 dark:bg-red-900 dark:text-red-200',
    yellow: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-200'
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-semibold text-gray-900 dark:text-white">{value}</p>
          {change && (
            <p className={`text-sm ${colorClasses[color]} mt-1 px-2 py-1 rounded-full inline-block`}>
              {change}
            </p>
          )}
          {description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{description}</p>
          )}
        </div>
      </div>
    </div>
  );
}

// Competitor status card
function CompetitorCard({ name, domain, status, lastUpdated, productsTracked, violationCount }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{name}</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{domain}</p>
        </div>
        <Badge 
          color={status === 'Active' ? 'green' : 'gray'}
        >
          {status}
        </Badge>
      </div>
      <div className="flex items-center justify-between text-sm">
        <div>
          <p className="text-gray-500 dark:text-gray-400">Products: {productsTracked}</p>
          <p className="text-gray-500 dark:text-gray-400">Updated {lastUpdated}</p>
        </div>
        <div className="text-right">
          <p className={`font-medium ${violationCount > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {violationCount} violations
          </p>
        </div>
      </div>
    </div>
  );
}

export default function PriceMonitorDashboard() {
  const [stats, setStats] = useState(null);
  const [competitors, setCompetitors] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // TODO: Replace with actual API call
      // const response = await fetch('/api/price-monitor/dashboard/stats');
      // const data = await response.json();
      
      // Mock data for now
      const mockData = {
        stats: {
          products_monitored: 0,
          active_alerts: 0,
          competitors_tracked: 0,
          map_violations: 0,
          revenue_at_risk: 0,
          worst_offender: null
        },
        competitor_status: [],
        recent_alerts: []
      };
      
      setStats(mockData.stats);
      setCompetitors(mockData.competitor_status);
      setAlerts(mockData.recent_alerts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <div className="ml-4 text-gray-500 dark:text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded-lg p-6">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
            <div className="mt-2 text-sm text-red-700 dark:text-red-300">
              <p>{error}</p>
            </div>
            <div className="mt-4">
              <Button
                color="red"
                onClick={fetchDashboardData}
              >
                Retry
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center justify-between mb-8">
        <div>
          <Heading level="1">MAP Enforcement Dashboard</Heading>
          <p className="mt-2 text-gray-600 dark:text-gray-400">Monitor competitor pricing compliance and MAP violations</p>
        </div>
        <Button 
          onClick={fetchDashboardData}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          Refresh Data
        </Button>
      </div>
      
      {/* Stats Grid */}
      <div className="mt-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-4 mb-8">
        <StatCard 
          title="Product Matches" 
          value={stats?.products_monitored?.toString() || '0'} 
          change="MAP enforcement records"
          description="Products being monitored for MAP compliance"
        />
        <StatCard 
          title="MAP Violations" 
          value={stats?.map_violations?.toString() || '0'} 
          change={stats?.map_violations && stats.map_violations > 0 ? `⚠️ ${stats.map_violations} Active` : '✓ All Compliant'}
          color={stats?.map_violations && stats.map_violations > 0 ? 'red' : 'green'}
          description="Active pricing violations requiring attention"
        />
        <StatCard 
          title="Revenue at Risk" 
          value={`$${stats?.revenue_at_risk?.toFixed(2) || '0.00'}`} 
          change={stats?.worst_offender ? `Worst: ${stats.worst_offender.name}` : 'No violations'} 
          color={stats?.revenue_at_risk && stats.revenue_at_risk > 0 ? 'red' : 'green'}
          description="Potential revenue impact from violations"
        />
        <StatCard 
          title="Competitors Monitored" 
          value={stats?.competitors_tracked?.toString() || '0'} 
          change="Active monitoring"
          description="Retail partners being tracked"
        />
      </div>

      {/* Competitor Status Section */}
      <Heading level="2" className="mt-12 mb-6">Competitor Status</Heading>
      {competitors.length > 0 ? (
        <div className="grid gap-6 sm:grid-cols-1 lg:grid-cols-3 mb-8">
          {competitors.map((competitor, index) => (
            <CompetitorCard 
              key={index}
              name={competitor.name}
              domain={competitor.domain}
              status={competitor.status}
              lastUpdated={competitor.last_updated}
              productsTracked={competitor.products_tracked}
              violationCount={competitor.total_violations || 0}
            />
          ))}
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center mb-8">
          <p className="text-gray-500 dark:text-gray-400">No competitors configured</p>
          <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">Add competitors in Settings to start monitoring</p>
        </div>
      )}

      {/* Recent Alerts Section */}
      <Heading level="2" className="mt-12 mb-6">Recent MAP Violations</Heading>
      {alerts.length > 0 ? (
        <div className="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Product
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Competitor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Violation Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Price Difference
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Our Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Impact
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Detected
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {alerts.map((alert) => (
                <tr key={alert.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    {alert.product_title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {alert.competitor}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge 
                      color={alert.alert_type === 'map_violation' ? 'red' : 'yellow'}
                    >
                      {alert.alert_type.replace('_', ' ')}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {alert.price_difference !== null ? (
                      <span className={alert.price_difference > 0 ? 'text-red-600' : 'text-green-600'}>
                        ${Math.abs(alert.price_difference).toFixed(2)} 
                        ({alert.price_difference > 0 ? '+' : ''}{alert.price_difference_percent?.toFixed(1)}%)
                      </span>
                    ) : (
                      <span className="text-gray-500 dark:text-gray-400">New Product</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    ${alert.idc_price?.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={alert.competitive_advantage > 0 ? 'text-green-600' : 'text-red-600'}>
                      ${alert.competitive_advantage?.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {new Date(alert.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center">
          <p className="text-gray-500 dark:text-gray-400">No recent violations</p>
          <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">Price violations will appear here when competitors change their pricing</p>
        </div>
      )}
    </>
  );
}