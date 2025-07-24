import React, { useState, useEffect } from 'react';
import { Heading } from '@common/heading';
import { Button } from '@common/button';
import { Text } from '@common/text';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@common/table';
import { Loader2Icon, BarChart3Icon, TrendingUpIcon, ShoppingCartIcon, DollarSignIcon, UsersIcon, TargetIcon, AlertCircleIcon, CalendarIcon, CheckCircleIcon, MailIcon, ClockIcon } from 'lucide-react';

const DashboardPage = () => {
  const [loading, setLoading] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [parsedMetrics, setParsedMetrics] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  // Date picker state
  const [startDate, setStartDate] = useState(() => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday.toISOString().split('T')[0]; // YYYY-MM-DD format
  });
  const [endDate, setEndDate] = useState(() => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday.toISOString().split('T')[0]; // YYYY-MM-DD format
  });

  // Function to parse key metrics from the dashboard response
  const parseMetrics = (responseText) => {
    const metrics = {
      shopify: {},
      ga4: {},
      topProducts: [],
      adCampaigns: []
    };

    try {
      // Extract Shopify revenue
      const revenueMatch = responseText.match(/Total Revenue[:\s]*\$?([\d,]+\.?\d*)/i);
      if (revenueMatch) metrics.shopify.revenue = revenueMatch[1];

      // Extract order count
      const ordersMatch = responseText.match(/Total.*Orders?[:\s]*(\d+)/i);
      if (ordersMatch) metrics.shopify.orders = ordersMatch[1];

      // Extract AOV
      const aovMatch = responseText.match(/Average Order Value.*AOV[:\s]*\$?([\d,]+\.?\d*)/i);
      if (aovMatch) metrics.shopify.aov = aovMatch[1];

      // Extract GA4 active users
      const usersMatch = responseText.match(/Active Users[:\s]*(\d+)/i);
      if (usersMatch) metrics.ga4.users = usersMatch[1];

      // Extract Ad Spend
      const adSpendMatch = responseText.match(/Ad Spend[:\s]*\$?([\d,]+\.?\d*)/i);
      if (adSpendMatch) metrics.ga4.ad_spend = adSpendMatch[1];

      return metrics;
    } catch (error) {
      console.error('Error parsing metrics:', error);
      return null;
    }
  };

  // Function to fetch dashboard data directly from analytics APIs
  const fetchDashboardData = async (queryStartDate = null, queryEndDate = null) => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('authToken');
      
      // Use provided dates or current state dates
      const finalStartDate = queryStartDate || startDate;
      const finalEndDate = queryEndDate || endDate;
      
      const params = new URLSearchParams({
        start_date: finalStartDate,
        end_date: finalEndDate
      });

      const response = await fetch(`/api/dashboard/analytics?${params}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch dashboard data: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Set the structured data
      setDashboardData(data);
      setParsedMetrics({
        shopify: {
          revenue: data.shopify.revenue,
          orders: data.shopify.orders.toString(),
          aov: data.shopify.aov
        },
        ga4: {
          users: data.ga4.users,
          ad_spend: data.ga4.ad_spend
        }
      });
      setLastUpdated(new Date().toLocaleString());
      
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Load dashboard data on component mount
  useEffect(() => {
    fetchDashboardData();
  }, []);

  return (
    <div className="container mx-auto p-6 max-w-7xl bg-zinc-50 min-h-screen">
      <div className="flex justify-between items-center mb-8">
        <div>
          <Heading level={1} className="flex items-center gap-3">
            <BarChart3Icon className="h-8 w-8 text-blue-600" />
            Performance Dashboard
          </Heading>
          <Text className="text-zinc-600 mt-2">
            {startDate === endDate ? 
              `Data for ${new Date(startDate).toLocaleDateString()}` :
              `Data from ${new Date(startDate).toLocaleDateString()} to ${new Date(endDate).toLocaleDateString()}`
            }
          </Text>
          {lastUpdated && (
            <Text className="text-sm text-zinc-500 mt-1">
              Last updated: {lastUpdated}
            </Text>
          )}
        </div>
        
        <Button 
          onClick={fetchDashboardData}
          disabled={loading}
          className="flex items-center gap-2"
        >
          {loading ? (
            <Loader2Icon className="h-4 w-4 animate-spin" />
          ) : (
            <TrendingUpIcon className="h-4 w-4" />
          )}
          {loading ? 'Refreshing...' : 'Refresh Data'}
        </Button>
      </div>

      {/* Date Picker */}
      <div className="mb-6 bg-white rounded-lg border border-zinc-200 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5 text-zinc-500" />
              <Text className="font-medium text-zinc-700">Date Range:</Text>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="border border-zinc-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <Text className="text-zinc-500">to</Text>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="border border-zinc-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const yesterday = new Date();
                yesterday.setDate(yesterday.getDate() - 1);
                const yesterdayStr = yesterday.toISOString().split('T')[0];
                setStartDate(yesterdayStr);
                setEndDate(yesterdayStr);
                fetchDashboardData(yesterdayStr, yesterdayStr);
              }}
            >
              Yesterday
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const today = new Date();
                const lastWeek = new Date();
                lastWeek.setDate(today.getDate() - 7);
                const lastWeekStr = lastWeek.toISOString().split('T')[0];
                const todayStr = today.toISOString().split('T')[0];
                setStartDate(lastWeekStr);
                setEndDate(todayStr);
                fetchDashboardData(lastWeekStr, todayStr);
              }}
            >
              Last 7 Days
            </Button>
            <Button
              size="sm"
              onClick={() => fetchDashboardData()}
              disabled={loading}
            >
              Apply
            </Button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <Text className="text-red-800 font-medium">Error Loading Dashboard</Text>
          <Text className="text-red-600 text-sm mt-1">{error}</Text>
          <Button 
            onClick={fetchDashboardData}
            className="mt-3"
            outline
            color="red"
          >
            Try Again
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading && !dashboardData && (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2Icon className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <Heading level={3} className="text-zinc-600">Generating Dashboard...</Heading>
          <Text className="text-zinc-500 text-center mt-2">
            Fetching data from Shopify and Google Analytics...
            <br />
            This may take a few moments.
          </Text>
        </div>
      )}

      {/* Dashboard Content */}
      {dashboardData && !loading && (
        <div className="space-y-8">
          {/* Quick Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg border border-zinc-200 p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Text className="text-sm font-medium text-zinc-600">Revenue</Text>
                  <div className="text-2xl font-bold text-zinc-900 mt-1">
                    {parsedMetrics?.shopify?.revenue ? `$${parsedMetrics.shopify.revenue}` : 'Loading...'}
                  </div>
                  <Text className="text-xs text-zinc-500 mt-1">
                    {startDate === endDate ? 
                      new Date(startDate).toLocaleDateString() : 
                      `${new Date(startDate).toLocaleDateString()} - ${new Date(endDate).toLocaleDateString()}`
                    }
                  </Text>
                </div>
                <div className="p-3 bg-green-100 rounded-full">
                  <DollarSignIcon className="h-8 w-8 text-green-600" />
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg border border-zinc-200 p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Text className="text-sm font-medium text-zinc-600">Orders</Text>
                  <div className="text-2xl font-bold text-zinc-900 mt-1">
                    {parsedMetrics?.shopify?.orders || 'Loading...'}
                  </div>
                  <Text className="text-xs text-zinc-500 mt-1">
                    {startDate === endDate ? 
                      new Date(startDate).toLocaleDateString() : 
                      `${new Date(startDate).toLocaleDateString()} - ${new Date(endDate).toLocaleDateString()}`
                    }
                  </Text>
                </div>
                <div className="p-3 bg-blue-100 rounded-full">
                  <ShoppingCartIcon className="h-8 w-8 text-blue-600" />
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg border border-zinc-200 p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Text className="text-sm font-medium text-zinc-600">Visitors</Text>
                  <div className="text-2xl font-bold text-zinc-900 mt-1">
                    {parsedMetrics?.ga4?.users || 'Loading...'}
                  </div>
                  <Text className="text-xs text-zinc-500 mt-1">
                    {startDate === endDate ? 
                      new Date(startDate).toLocaleDateString() : 
                      `${new Date(startDate).toLocaleDateString()} - ${new Date(endDate).toLocaleDateString()}`
                    }
                  </Text>
                </div>
                <div className="p-3 bg-purple-100 rounded-full">
                  <UsersIcon className="h-8 w-8 text-purple-600" />
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg border border-zinc-200 p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <Text className="text-sm font-medium text-zinc-600">Ad Spend</Text>
                  <div className="text-2xl font-bold text-zinc-900 mt-1">
                    {dashboardData?.ga4?.ad_spend ? `$${dashboardData.ga4.ad_spend}` : 'Loading...'}
                  </div>
                  <Text className="text-xs text-zinc-500 mt-1">
                    {startDate === endDate ? 
                      new Date(startDate).toLocaleDateString() : 
                      `${new Date(startDate).toLocaleDateString()} - ${new Date(endDate).toLocaleDateString()}`
                    }
                  </Text>
                </div>
                <div className="p-3 bg-orange-100 rounded-full">
                  <DollarSignIcon className="h-8 w-8 text-orange-600" />
                </div>
              </div>
            </div>
          </div>

          {/* Performance Sections */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Shopify Performance */}
            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
              <div className="bg-gradient-to-r from-green-50 to-green-100 px-6 py-4 border-b border-zinc-200">
                <Heading level={3} className="text-zinc-900 flex items-center gap-2">
                  <ShoppingCartIcon className="h-5 w-5 text-green-600" />
                  Shopify Performance
                </Heading>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div>
                    <Text className="text-sm font-medium text-zinc-600">Revenue</Text>
                    <Text className="text-xl font-bold text-zinc-900">${dashboardData?.shopify?.revenue || '0'}</Text>
                  </div>
                  <div>
                    <Text className="text-sm font-medium text-zinc-600">Orders</Text>
                    <Text className="text-xl font-bold text-zinc-900">{dashboardData?.shopify?.orders || '0'}</Text>
                  </div>
                  <div>
                    <Text className="text-sm font-medium text-zinc-600">AOV</Text>
                    <Text className="text-xl font-bold text-zinc-900">${dashboardData?.shopify?.aov || '0'}</Text>
                  </div>
                </div>
                
                {dashboardData?.shopify?.top_products && dashboardData.shopify.top_products.length > 0 && (
                  <div>
                    <Heading level={4} className="text-zinc-800 mb-3">Top Products</Heading>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableHeader>Rank</TableHeader>
                          <TableHeader>Product</TableHeader>
                          <TableHeader>Qty</TableHeader>
                          <TableHeader>Revenue</TableHeader>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {dashboardData.shopify.top_products.slice(0, 5).map((product, index) => (
                          <TableRow key={index}>
                            <TableCell>{index + 1}</TableCell>
                            <TableCell className="font-medium">{product.title || product.name}</TableCell>
                            <TableCell>{product.quantity_sold}</TableCell>
                            <TableCell>${product.revenue}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            </div>

            {/* GA4 Performance */}
            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
              <div className="bg-gradient-to-r from-blue-50 to-blue-100 px-6 py-4 border-b border-zinc-200">
                <Heading level={3} className="text-zinc-900 flex items-center gap-2">
                  <BarChart3Icon className="h-5 w-5 text-blue-600" />
                  Google Analytics Performance
                </Heading>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <Text className="text-sm font-medium text-zinc-600">Active Users</Text>
                    <Text className="text-xl font-bold text-zinc-900">{dashboardData?.ga4?.users || '0'}</Text>
                  </div>
                  <div>
                    <Text className="text-sm font-medium text-zinc-600">Conversion Rate</Text>
                    <Text className="text-xl font-bold text-zinc-900">{dashboardData?.ga4?.conversion_rate || '0%'}</Text>
                  </div>
                  <div>
                    <Text className="text-sm font-medium text-zinc-600">Ad Spend</Text>
                    <Text className="text-xl font-bold text-zinc-900">${dashboardData?.ga4?.ad_spend || '0'}</Text>
                  </div>
                  <div>
                    <Text className="text-sm font-medium text-zinc-600">ROAS</Text>
                    <Text className="text-xl font-bold text-zinc-900">{dashboardData?.ga4?.roas || '0'}x</Text>
                  </div>
                </div>

                {dashboardData?.ga4?.traffic_sources && dashboardData.ga4.traffic_sources.length > 0 && (
                  <div>
                    <Heading level={4} className="text-zinc-800 mb-3">Top Traffic Sources</Heading>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableHeader>Source</TableHeader>
                          <TableHeader>Users</TableHeader>
                          <TableHeader>Revenue</TableHeader>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {dashboardData.ga4.traffic_sources.slice(0, 5).map((source, index) => (
                          <TableRow key={index}>
                            <TableCell className="font-medium">{source.source}</TableCell>
                            <TableCell>{source.users}</TableCell>
                            <TableCell>${source.revenue}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Google Workspace Section */}
          {dashboardData?.workspace && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {/* Google Tasks Widget */}
              <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
                <div className="bg-gradient-to-r from-green-50 to-green-100 px-4 py-3 border-b border-zinc-200">
                  <div className="flex items-center justify-between">
                    <Heading level={4} className="text-zinc-900 flex items-center gap-2">
                      <CheckCircleIcon className="h-4 w-4 text-green-600" />
                      Google Tasks ({dashboardData.workspace.tasks.count})
                    </Heading>
                    <a 
                      href="https://tasks.google.com" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-green-700 hover:text-green-800 font-medium"
                    >
                      View All
                    </a>
                  </div>
                </div>
                <div className="p-4 max-h-64 overflow-y-auto">
                  {dashboardData.workspace.tasks.error ? (
                    <Text className="text-zinc-500 text-sm">{dashboardData.workspace.tasks.error}</Text>
                  ) : dashboardData.workspace.tasks.items.length > 0 ? (
                    <div className="space-y-2">
                      {dashboardData.workspace.tasks.items.slice(0, 5).map((task, index) => (
                        <div key={task.id || index} className="border-l-2 border-green-200 pl-3 py-1">
                          <a 
                            href="https://tasks.google.com" 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="hover:text-green-700 transition-colors"
                          >
                            <Text className="font-medium text-sm text-zinc-800 hover:text-green-700">{task.title}</Text>
                          </a>
                          {task.due && (
                            <Text className="text-xs text-zinc-500">
                              Due: {new Date(task.due).toLocaleDateString()}
                            </Text>
                          )}
                          {task.notes && (
                            <Text className="text-xs text-zinc-600 line-clamp-2">{task.notes}</Text>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Text className="text-zinc-500 text-sm">No pending tasks</Text>
                  )}
                </div>
              </div>

              {/* Recent Emails Widget */}
              <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
                <div className="bg-gradient-to-r from-blue-50 to-blue-100 px-4 py-3 border-b border-zinc-200">
                  <div className="flex items-center justify-between">
                    <Heading level={4} className="text-zinc-900 flex items-center gap-2">
                      <MailIcon className="h-4 w-4 text-blue-600" />
                      Recent Emails ({dashboardData.workspace.emails.count})
                    </Heading>
                    <a 
                      href="https://mail.google.com/mail/u/0/#inbox" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-blue-700 hover:text-blue-800 font-medium"
                    >
                      View All
                    </a>
                  </div>
                </div>
                <div className="p-4 max-h-64 overflow-y-auto">
                  {dashboardData.workspace.emails.error ? (
                    <Text className="text-zinc-500 text-sm">{dashboardData.workspace.emails.error}</Text>
                  ) : dashboardData.workspace.emails.items.length > 0 ? (
                    <div className="space-y-3">
                      {dashboardData.workspace.emails.items.slice(0, 5).map((email, index) => (
                        <div key={email.id || index} className="border-l-2 border-blue-200 pl-3 py-1">
                          <a 
                            href={`https://mail.google.com/mail/u/0/#inbox/${email.id}`}
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="hover:text-blue-700 transition-colors"
                          >
                            <Text className="font-medium text-sm text-zinc-800 hover:text-blue-700 line-clamp-1">{email.subject}</Text>
                          </a>
                          <Text className="text-xs text-zinc-600 line-clamp-1">{email.from}</Text>
                          {email.snippet && (
                            <Text className="text-xs text-zinc-500 line-clamp-2">{email.snippet}</Text>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Text className="text-zinc-500 text-sm">No recent emails</Text>
                  )}
                </div>
              </div>

              {/* Upcoming Calendar Widget */}
              <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
                <div className="bg-gradient-to-r from-purple-50 to-purple-100 px-4 py-3 border-b border-zinc-200">
                  <div className="flex items-center justify-between">
                    <Heading level={4} className="text-zinc-900 flex items-center gap-2">
                      <ClockIcon className="h-4 w-4 text-purple-600" />
                      Upcoming Events ({dashboardData.workspace.calendar.count})
                    </Heading>
                    <a 
                      href="https://calendar.google.com/calendar" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-purple-700 hover:text-purple-800 font-medium"
                    >
                      View All
                    </a>
                  </div>
                </div>
                <div className="p-4 max-h-64 overflow-y-auto">
                  {dashboardData.workspace.calendar.error ? (
                    <Text className="text-zinc-500 text-sm">{dashboardData.workspace.calendar.error}</Text>
                  ) : dashboardData.workspace.calendar.items.length > 0 ? (
                    <div className="space-y-3">
                      {dashboardData.workspace.calendar.items.slice(0, 5).map((event, index) => (
                        <div key={event.id || index} className="border-l-2 border-purple-200 pl-3 py-1">
                          {event.htmlLink ? (
                            <a 
                              href={event.htmlLink}
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="hover:text-purple-700 transition-colors"
                            >
                              <Text className="font-medium text-sm text-zinc-800 hover:text-purple-700 line-clamp-1">{event.summary}</Text>
                            </a>
                          ) : (
                            <Text className="font-medium text-sm text-zinc-800 line-clamp-1">{event.summary}</Text>
                          )}
                          <Text className="text-xs text-zinc-600">
                            {new Date(event.start).toLocaleDateString()} at{' '}
                            {new Date(event.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </Text>
                          {event.location && (
                            <Text className="text-xs text-zinc-500 line-clamp-1">📍 {event.location}</Text>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Text className="text-zinc-500 text-sm">No upcoming events</Text>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Insights Section */}
          {dashboardData?.insights && dashboardData.insights.length > 0 && (
            <div className="bg-white rounded-lg border border-zinc-200 shadow-sm overflow-hidden">
              <div className="bg-gradient-to-r from-purple-50 to-purple-100 px-6 py-4 border-b border-zinc-200">
                <Heading level={3} className="text-zinc-900 flex items-center gap-2">
                  <TrendingUpIcon className="h-5 w-5 text-purple-600" />
                  Key Insights & Recommendations
                </Heading>
              </div>
              <div className="p-6">
                <div className="space-y-3">
                  {dashboardData.insights.map((insight, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-zinc-50 rounded-lg">
                      <div className="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></div>
                      <Text className="text-zinc-700">{insight}</Text>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!dashboardData && !loading && !error && (
        <div className="text-center py-12">
          <BarChart3Icon className="h-16 w-16 text-zinc-300 mx-auto mb-4" />
          <Heading level={3} className="text-zinc-600 mb-2">No Dashboard Data</Heading>
          <Text className="text-zinc-500 mb-4">
            Click "Refresh Data" to generate your daily performance report.
          </Text>
          <Button onClick={fetchDashboardData}>Generate Report</Button>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;