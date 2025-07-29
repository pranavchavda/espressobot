import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
import { useToast } from '@common/toast';

export default function PriceAlertsPage() {
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('active');
  const [summary, setSummary] = useState(null);
  const { toast } = useToast();

  const fetchViolations = async () => {
    try {
      setLoading(true);
      const resolved = filter === 'resolved' ? 'true' : 'false';
      const response = await fetch(`/api/price-monitor/map-violations/violations?resolved=${resolved}&limit=100`);
      
      if (response.ok) {
        const data = await response.json();
        setViolations(data.violations || []);
        setSummary(data.summary || null);
      } else {
        toast.error('Failed to fetch violations');
      }
    } catch (error) {
      console.error('Error fetching violations:', error);
      toast.error('Error loading violations');
    } finally {
      setLoading(false);
    }
  };

  const resolveViolation = async (violationId) => {
    try {
      const response = await fetch(`/api/price-monitor/map-violations/violations/${violationId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved_by: 'User' })
      });

      if (response.ok) {
        toast.success('Violation resolved successfully');
        fetchViolations(); // Refresh the list
      } else {
        toast.error('Failed to resolve violation');
      }
    } catch (error) {
      console.error('Error resolving violation:', error);
      toast.error('Error resolving violation');
    }
  };

  useEffect(() => {
    fetchViolations();
  }, [filter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <div className="ml-4 text-gray-500 dark:text-gray-400">Loading violations...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <Heading level="1">Price Alerts</Heading>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Monitor and manage price change alerts and MAP violations
          </p>
        </div>
        <div className="flex space-x-3">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          >
            <option value="active">Active Violations</option>
            <option value="resolved">Resolved Violations</option>
          </select>
          <Button 
            onClick={fetchViolations}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Summary Statistics */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{summary.total_active}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Active Violations</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-red-600">{summary.by_severity?.severe?.count || 0}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Severe</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-orange-600">{summary.by_severity?.moderate?.count || 0}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Moderate</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-yellow-600">{summary.by_severity?.minor?.count || 0}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Minor</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-600">${summary.total_impact?.toFixed(2) || '0.00'}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Revenue Impact</div>
          </div>
        </div>
      )}

      {violations.length > 0 ? (
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
                  Severity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Price Violation
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Detected
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {violations.map((violation) => (
                <tr key={violation.id}>
                  <td className="px-6 py-4 text-sm">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {violation.product_match?.idc_product?.title || 'Unknown Product'}
                    </div>
                    <div className="text-gray-500 dark:text-gray-400 text-xs">
                      {violation.product_match?.idc_product?.vendor} • SKU: {violation.product_match?.idc_product?.sku}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {violation.product_match?.competitor_product?.title || 'Unknown Product'}
                    </div>
                    <div className="text-gray-500 dark:text-gray-400 text-xs">
                      {violation.product_match?.competitor_product?.competitor?.name || 'Unknown'} • ${parseFloat(violation.product_match?.competitor_product?.price || 0).toFixed(2)}
                    </div>
                    <div className="text-gray-500 dark:text-gray-400 text-xs">
                      {violation.product_match?.competitor_product?.competitor?.domain}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge color={
                      violation.severity === 'severe' ? 'red' :
                      violation.severity === 'moderate' ? 'orange' :
                      violation.severity === 'minor' ? 'yellow' : 'gray'
                    }>
                      {violation.severity}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">MAP: ${parseFloat(violation.old_price || 0).toFixed(2)}</span>
                      {' → '}
                      <span className="text-red-600 font-medium">
                        ${parseFloat(violation.new_price || 0).toFixed(2)}
                      </span>
                    </div>
                    <div className="text-xs text-red-600">
                      -{((parseFloat(violation.old_price || 0) - parseFloat(violation.new_price || 0)) / parseFloat(violation.old_price || 1) * 100).toFixed(1)}% (${parseFloat(violation.price_change || 0).toFixed(2)})
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {violation.created_at ? new Date(violation.created_at).toLocaleString() : 'Unknown'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    {/* Actions removed for now */}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-500 dark:text-gray-400">
            <h3 className="text-lg font-medium mb-2">
              {filter === 'active' ? 'No active violations found' : 'No resolved violations found'}
            </h3>
            <p className="mb-4">
              {filter === 'active' 
                ? 'MAP violations will appear here when competitors price below your minimum advertised price.'
                : 'Resolved violations will appear here once you mark active violations as resolved.'
              }
            </p>
            <Button 
              onClick={fetchViolations}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}