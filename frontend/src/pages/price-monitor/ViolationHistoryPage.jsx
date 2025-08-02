import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Badge } from '@common/badge';
import { Heading } from '@common/heading';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@common/table';
import { useToast } from '@common/toast';
import { CalendarIcon, ChartBarIcon, ArrowDownTrayIcon, FunnelIcon } from '@heroicons/react/20/solid';

export default function ViolationHistoryPage() {
  const [violations, setViolations] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    brand: '',
    competitor: '',
    startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 7 days ago
    endDate: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Tomorrow to include all of today
    groupBy: 'day'
  });
  const { toast } = useToast();

  const fetchStatistics = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        start_date: filters.startDate,
        end_date: filters.endDate,
        group_by: filters.groupBy
      });
      
      if (filters.brand) params.append('brand', filters.brand);
      if (filters.competitor) params.append('competitor', filters.competitor);

      const response = await fetch(`/api/price-monitor/violation-history/statistics?${params}`);
      
      if (response.ok) {
        const data = await response.json();
        setStatistics(data);
        setLoading(false);
        
        // Also fetch recent violations for display
        fetchRecentViolations();
      } else {
        console.error('Statistics response:', await response.text());
        toast.error('Failed to fetch violation statistics');
        setLoading(false);
      }
    } catch (error) {
      console.error('Error fetching statistics:', error);
      toast.error('Error loading violation statistics');
      setLoading(false);
    }
  };

  const fetchRecentViolations = async () => {
    try {
      // For demo, let's fetch from the regular violations endpoint
      const response = await fetch(`/api/price-monitor/map-violations/violations?limit=50&resolved=true`);
      
      if (response.ok) {
        const data = await response.json();
        setViolations(data.violations || []);
      }
    } catch (error) {
      console.error('Error fetching violations:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportData = async (format = 'csv') => {
    try {
      const params = new URLSearchParams({
        format,
        start_date: filters.startDate,
        end_date: filters.endDate
      });
      
      if (filters.brand) params.append('brand', filters.brand);
      if (filters.competitor) params.append('competitor', filters.competitor);

      const response = await fetch(`/api/price-monitor/violation-history/export?${params}`);
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `violation-history-${filters.startDate}-to-${filters.endDate}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        toast.success(`Exported violation history as ${format.toUpperCase()}`);
      } else {
        toast.error('Failed to export data');
      }
    } catch (error) {
      console.error('Error exporting data:', error);
      toast.error('Error exporting violation history');
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    fetchStatistics();
  }, [filters]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <div className="ml-4 text-gray-500 dark:text-gray-400">Loading violation history...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-8 gap-4">
        <div>
          <Heading level="1">Violation History</Heading>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Track MAP violation trends and export historical data
          </p>
        </div>
        
        <Button 
          onClick={() => exportData('csv')}
          className="bg-green-600 hover:bg-green-700 text-white"
        >
          <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <FunnelIcon className="h-5 w-5 text-gray-500" />
          <h3 className="font-medium">Filters</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Start Date</label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">End Date</label>
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Brand</label>
            <select
              value={filters.brand}
              onChange={(e) => handleFilterChange('brand', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700"
            >
              <option value="">All Brands</option>
              <option value="Profitec">Profitec</option>
              <option value="Eureka">Eureka</option>
              <option value="ECM">ECM</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Competitor</label>
            <select
              value={filters.competitor}
              onChange={(e) => handleFilterChange('competitor', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700"
            >
              <option value="">All Competitors</option>
              <option value="The Kitchen Barista">The Kitchen Barista</option>
              <option value="HomeCoffeeSolutions.com">HomeCoffeeSolutions.com</option>
              <option value="Cafe Liegeois">Cafe Liegeois</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Group By</label>
            <select
              value={filters.groupBy}
              onChange={(e) => handleFilterChange('groupBy', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700"
            >
              <option value="day">Daily</option>
              <option value="week">Weekly</option>
              <option value="month">Monthly</option>
            </select>
          </div>
        </div>
      </div>

      {/* Summary Statistics */}
      {statistics?.summary && (
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {statistics.summary.total_violations}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Violations</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-600">
              {statistics.summary.active_violations}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Currently Active</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-orange-600">
              {statistics.summary.average_violation_percent?.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Avg Violation</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-red-600">
              {statistics.summary.max_violation_percent?.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Max Violation</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-600">
              ${statistics.summary.average_violation_amount?.toFixed(2)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Avg $ Impact</div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="text-2xl font-bold text-purple-600">
              ${statistics.summary.max_violation_amount?.toFixed(2)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Max $ Impact</div>
          </div>
        </div>
      )}

      {/* No Data Message */}
      {statistics && (!statistics.time_series || statistics.time_series.length === 0) && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-12 text-center mb-6">
          <div className="text-gray-500 dark:text-gray-400">
            <h3 className="text-lg font-medium mb-2">No Violation History Found</h3>
            <p className="mb-4">
              No MAP violations have been recorded for the selected time period.
            </p>
            <p className="text-sm">
              Violations will appear here after running a violation scan. You can trigger a scan from the Price Alerts page or wait for the automated cron job to run.
            </p>
          </div>
        </div>
      )}

      {/* Time Series Chart (placeholder) */}
      {statistics?.time_series && statistics.time_series.length > 0 && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <ChartBarIcon className="h-5 w-5 text-gray-500" />
            <h3 className="font-medium">Violation Trends</h3>
          </div>
          
          <div className="overflow-x-auto">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeader>Period</TableHeader>
                  <TableHeader>Violations</TableHeader>
                  <TableHeader>Avg %</TableHeader>
                  <TableHeader>Total Impact</TableHeader>
                  <TableHeader>Unique Products</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {statistics.time_series.slice(0, 10).map((period, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      {new Date(period.period).toLocaleDateString()}
                    </TableCell>
                    <TableCell>{period.violation_count}</TableCell>
                    <TableCell>{parseFloat(period.avg_violation_pct).toFixed(1)}%</TableCell>
                    <TableCell>${parseFloat(period.total_impact).toFixed(2)}</TableCell>
                    <TableCell>{period.unique_products}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Violations by Type */}
      {statistics?.by_type && statistics.by_type.length > 0 && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="font-medium mb-4">Violations by Type</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {statistics.by_type.map((type) => (
              <div key={type.violation_type} className="border border-gray-200 dark:border-gray-700 rounded p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{type.violation_type.replace('map_violation_', '').toUpperCase()}</span>
                  <Badge color={
                    type.violation_type.includes('severe') ? 'red' :
                    type.violation_type.includes('moderate') ? 'orange' : 'yellow'
                  }>
                    {type._count.id} violations
                  </Badge>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  <div>Avg: {type._avg.violation_percent?.toFixed(1)}%</div>
                  <div>Total: ${type._sum.violation_amount?.toFixed(2)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}