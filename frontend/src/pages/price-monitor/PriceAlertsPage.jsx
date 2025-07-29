import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@common/table';
import { useToast } from '@common/toast';

export default function PriceAlertsPage() {
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('active');
  const [summary, setSummary] = useState(null);
  const [minSimilarity, setMinSimilarity] = useState(0); // 0-100 range
  const [sortBy, setSortBy] = useState('similarity'); // 'similarity' or 'severity'
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

  // Filter and sort violations
  const processedViolations = violations
    .filter(violation => {
      // Filter by minimum similarity
      const matchScore = violation.product_matches?.is_manual_match ? 1.0 : (violation.product_matches?.overall_score || 0);
      const similarityPercent = matchScore * 100;
      return similarityPercent >= minSimilarity;
    })
    .sort((a, b) => {
      // Pin manual matches to the top
      const isManualA = a.product_match?.is_manual_match || false;
      const isManualB = b.product_match?.is_manual_match || false;
      
      if (isManualA && !isManualB) return -1;
      if (!isManualA && isManualB) return 1;
      
      if (sortBy === 'similarity') {
        // Sort by similarity score (highest first)
        const scoreA = isManualA ? 1.0 : (a.product_match?.overall_score || 0);
        const scoreB = isManualB ? 1.0 : (b.product_match?.overall_score || 0);
        return scoreB - scoreA;
      } else {
        // Sort by severity (severe > moderate > minor)
        const severityOrder = { severe: 3, moderate: 2, minor: 1 };
        const severityA = severityOrder[a.severity] || 0;
        const severityB = severityOrder[b.severity] || 0;
        return severityB - severityA;
      }
    });

  // Calculate filtered revenue impact
  const filteredRevenueImpact = processedViolations.reduce((total, violation) => {
    return total + Math.abs(parseFloat(violation.price_change || 0));
  }, 0);

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
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-8 gap-4">
        <div>
          <Heading level="1">Price Alerts</Heading>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Monitor and manage price change alerts and MAP violations
          </p>
        </div>
        
        {/* Controls */}
        <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
          {/* Status Filter */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white text-sm"
          >
            <option value="active">Active Violations</option>
            <option value="resolved">Resolved Violations</option>
          </select>

          {/* Sort By */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white text-sm"
          >
            <option value="similarity">Sort by Similarity</option>
            <option value="severity">Sort by Severity</option>
          </select>

          {/* Similarity Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">Min Similarity:</span>
            <select
              value={minSimilarity}
              onChange={(e) => setMinSimilarity(parseInt(e.target.value))}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white text-sm"
            >
              <option value={0}>All (0%+)</option>
              <option value={50}>50%+</option>
              <option value={60}>60%+</option>
              <option value={70}>70%+</option>
              <option value={80}>80%+</option>
              <option value={90}>90%+</option>
            </select>
          </div>

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
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{processedViolations.length}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Shown ({violations.length} total)</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-600">
              {processedViolations.length > 0 ? 
                ((processedViolations.reduce((sum, v) => sum + (v.product_match?.is_manual_match ? 1.0 : (v.product_match?.overall_score || 0)), 0) / processedViolations.length) * 100).toFixed(1) + '%' 
                : '0%'
              }
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Avg Similarity</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-red-600">{processedViolations.filter(v => v.severity === 'severe').length}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Severe</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-orange-600">{processedViolations.filter(v => v.severity === 'moderate').length}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Moderate</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-yellow-600">{processedViolations.filter(v => v.severity === 'minor').length}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Minor</div>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-600">${filteredRevenueImpact.toFixed(2)}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Revenue Impact</div>
          </div>
        </div>
      )}

      {processedViolations.length > 0 ? (
        <div className="overflow-x-auto">
          <Table striped>
          <TableHead>
            <TableRow>
              <TableHeader>Product</TableHeader>
              <TableHeader>Competitor</TableHeader>
              <TableHeader>Similarity</TableHeader>
              <TableHeader>Severity</TableHeader>
              <TableHeader>Price Violation</TableHeader>
              <TableHeader>Detected</TableHeader>
              <TableHeader>Actions</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {processedViolations.map((violation) => (
              <TableRow key={violation.id}>
                <TableCell>
                  <div className="font-medium">
                    {violation.product_matches?.idc_products?.handle ? (
                      <a 
                        href={`https://idrinkcoffee.com/products/${violation.product_matches.idc_products.handle}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {violation.product_matches.idc_products.title || 'Unknown Product'}
                      </a>
                    ) : (
                      violation.product_matches?.idc_products?.title || 'Unknown Product'
                    )}
                  </div>
                  <div className="text-zinc-500 text-xs">
                    {violation.product_matches?.idc_products?.vendor} • SKU: {violation.product_matches?.idc_products?.sku}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="font-medium">
                    {violation.product_matches?.competitor_products?.product_url ? (
                      <a 
                        href={violation.product_matches.competitor_products.product_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {violation.product_matches.competitor_products.title || 'Unknown Product'}
                      </a>
                    ) : (
                      violation.product_matches?.competitor_products?.title || 'Unknown Product'
                    )}
                  </div>
                  <div className="text-zinc-500 text-xs">
                    {violation.product_matches?.competitor_products?.competitors?.name || 'Unknown'} • ${parseFloat(violation.product_matches?.competitor_products?.price || 0).toFixed(2)}
                  </div>
                  <div className="text-zinc-500 text-xs">
                    {violation.product_matches?.competitor_products?.competitors?.domain}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Badge color={
                      violation.product_matches?.is_manual_match ? 'green' :
                      (violation.product_matches?.overall_score || 0) >= 0.8 ? 'green' :
                      (violation.product_matches?.overall_score || 0) >= 0.7 ? 'blue' :
                      (violation.product_matches?.overall_score || 0) >= 0.6 ? 'yellow' : 'red'
                    }>
                      {violation.product_matches?.is_manual_match ? '100.0%' : ((violation.product_matches?.overall_score || 0) * 100).toFixed(1) + '%'}
                    </Badge>
                    {violation.product_matches?.is_manual_match && (
                      <span className="text-xs text-blue-600 font-medium">📌 Manual</span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge color={
                    violation.severity === 'severe' ? 'red' :
                    violation.severity === 'moderate' ? 'orange' :
                    violation.severity === 'minor' ? 'yellow' : 'gray'
                  }>
                    {violation.severity}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div>
                    <span className="text-zinc-500">MAP: ${parseFloat(violation.old_price || 0).toFixed(2)}</span>
                    {' → '}
                    <span className="text-red-600 font-medium">
                      ${parseFloat(violation.new_price || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="text-xs text-red-600">
                    -{((parseFloat(violation.old_price || 0) - parseFloat(violation.new_price || 0)) / parseFloat(violation.old_price || 1) * 100).toFixed(1)}% (${parseFloat(violation.price_change || 0).toFixed(2)})
                  </div>
                </TableCell>
                <TableCell className="text-zinc-500">
                  {violation.created_at ? new Date(violation.created_at).toLocaleString() : 'Unknown'}
                </TableCell>
                <TableCell>
                  {/* Actions removed for now */}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          </Table>
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