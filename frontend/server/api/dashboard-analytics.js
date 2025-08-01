/**
 * Dashboard Analytics API
 * Provides direct access to analytics data without LLM processing
 */

import { Router } from 'express';
import { authenticateToken } from '../auth.js';
import { callMCPTool } from '../tools/mcp-client.js';
import { BetaAnalyticsDataClient } from '@google-analytics/data';
import { google } from 'googleapis';
import { db } from '../config/database.js';

const prisma = db;

const router = Router();

/**
 * Call Shopify analytics tool directly without LLM
 */
async function getShopifyAnalytics(startDate, endDate, userId) {
  try {
    console.log(`[Shopify Analytics] Calling analytics_order_summary directly for ${startDate}`);
    
    const result = await callMCPTool('analytics_order_summary', {
      start_date: startDate,
      end_date: endDate,
      include_products: true,
      product_limit: 10
    });
    
    console.log('[Shopify Analytics] Raw MCP response:', JSON.stringify(result, null, 2));
    console.log('[Shopify Analytics] Top products data:', JSON.stringify(result?.data?.top_products, null, 2));
    
    // The MCP tool returns nested data structure
    if (result && result.success && result.data) {
      const data = result.data;
      return {
        total_revenue: data.summary?.total_revenue?.toString() || '0',
        order_count: data.summary?.order_count || 0,
        average_order_value: data.summary?.average_order_value?.toString() || '0',
        top_products: data.top_products || [],
        raw_response: result
      };
    } else {
      console.error('[Shopify Analytics] Unexpected result format:', result);
      return { total_revenue: '0', order_count: 0, average_order_value: '0', top_products: [] };
    }
  } catch (error) {
    console.error('[Shopify Analytics] Error calling MCP tool:', error);
    return { total_revenue: '0', order_count: 0, average_order_value: '0', top_products: [] };
  }
}

/**
 * Get OAuth2 client for Google APIs
 */
async function getAuthClient(userId) {
  const user = await prisma.users.findUnique({
    where: { id: userId },
    select: { 
      google_access_token: true, 
      google_refresh_token: true,
      ga4_property_id: true,
      ga4_enabled: true
    }
  });

  if (!user?.google_access_token) {
    throw new Error('User not authenticated with Google');
  }

  if (!user.ga4_enabled) {
    throw new Error('GA4 integration not enabled for this user');
  }

  if (!user.ga4_property_id) {
    throw new Error('GA4 property ID not configured');
  }

  const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET
  );

  oauth2Client.setCredentials({
    access_token: user.google_access_token,
    refresh_token: user.google_refresh_token
  });

  return { oauth2Client, propertyId: user.ga4_property_id };
}

/**
 * Get Google Tasks data using direct API calls
 */
async function getGoogleTasks(userId) {
  try {
    console.log('[Google Tasks] Fetching tasks from Google Tasks API...');
    
    const user = await prisma.users.findUnique({
      where: { id: userId },
      select: { 
        google_access_token: true, 
        google_refresh_token: true
      }
    });

    if (!user?.google_access_token) {
      console.log('[Google Tasks] User not authenticated with Google');
      return { tasks: [], error: 'Not authenticated with Google' };
    }

    const oauth2Client = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET
    );

    oauth2Client.setCredentials({
      access_token: user.google_access_token,
      refresh_token: user.google_refresh_token
    });

    const tasks = google.tasks({ version: 'v1', auth: oauth2Client });
    
    // Get tasks from default task list
    const response = await tasks.tasks.list({
      tasklist: '@default',
      showCompleted: false,
      showHidden: false,
      maxResults: 10
    });

    const taskItems = (response.data.items || []).map(task => ({
      id: task.id,
      title: task.title,
      notes: task.notes,
      status: task.status,
      due: task.due,
      updated: task.updated
    }));

    console.log(`[Google Tasks] Successfully fetched ${taskItems.length} tasks`);
    return { tasks: taskItems };
    
  } catch (error) {
    console.error('[Google Tasks] Error fetching tasks:', error);
    return { tasks: [], error: error.message };
  }
}

/**
 * Get recent emails from Gmail using direct API calls
 */
async function getRecentEmails(userId, maxResults = 10) {
  try {
    console.log('[Gmail] Fetching recent emails from Gmail API...');
    
    const user = await prisma.users.findUnique({
      where: { id: userId },
      select: { 
        google_access_token: true, 
        google_refresh_token: true
      }
    });

    if (!user?.google_access_token) {
      console.log('[Gmail] User not authenticated with Google');
      return { emails: [], error: 'Not authenticated with Google' };
    }

    const oauth2Client = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET
    );

    oauth2Client.setCredentials({
      access_token: user.google_access_token,
      refresh_token: user.google_refresh_token
    });

    const gmail = google.gmail({ version: 'v1', auth: oauth2Client });
    
    // Get recent emails from inbox
    const response = await gmail.users.messages.list({
      userId: 'me',
      labelIds: ['INBOX'],
      maxResults: maxResults
    });

    // Fetch details for each email
    const emails = await Promise.all(
      (response.data.messages || []).map(async (msg) => {
        try {
          const detail = await gmail.users.messages.get({
            userId: 'me',
            id: msg.id,
            format: 'metadata',
            metadataHeaders: ['Subject', 'From', 'Date']
          });
          
          const headers = detail.data.payload.headers;
          return {
            id: msg.id,
            subject: headers.find(h => h.name === 'Subject')?.value || 'No Subject',
            from: headers.find(h => h.name === 'From')?.value || 'Unknown',
            date: headers.find(h => h.name === 'Date')?.value || '',
            snippet: detail.data.snippet || ''
          };
        } catch (err) {
          console.error('[Gmail] Error fetching email details:', err);
          return null;
        }
      })
    );

    const validEmails = emails.filter(email => email !== null);
    console.log(`[Gmail] Successfully fetched ${validEmails.length} emails`);
    return { emails: validEmails };
    
  } catch (error) {
    console.error('[Gmail] Error fetching emails:', error);
    return { emails: [], error: error.message };
  }
}

/**
 * Get upcoming calendar events using direct API calls
 */
async function getUpcomingCalendar(userId, maxResults = 10) {
  try {
    console.log('[Calendar] Fetching upcoming events from Google Calendar API...');
    
    const user = await prisma.users.findUnique({
      where: { id: userId },
      select: { 
        google_access_token: true, 
        google_refresh_token: true
      }
    });

    if (!user?.google_access_token) {
      console.log('[Calendar] User not authenticated with Google');
      return { events: [], error: 'Not authenticated with Google' };
    }

    const oauth2Client = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET
    );

    oauth2Client.setCredentials({
      access_token: user.google_access_token,
      refresh_token: user.google_refresh_token
    });

    const calendar = google.calendar({ version: 'v3', auth: oauth2Client });
    
    // Get upcoming events
    const now = new Date().toISOString();
    const response = await calendar.events.list({
      calendarId: 'primary',
      timeMin: now,
      maxResults: maxResults,
      singleEvents: true,
      orderBy: 'startTime'
    });

    const events = (response.data.items || []).map(event => ({
      id: event.id,
      summary: event.summary || 'No Title',
      description: event.description,
      start: event.start?.dateTime || event.start?.date,
      end: event.end?.dateTime || event.end?.date,
      location: event.location,
      htmlLink: event.htmlLink
    }));

    console.log(`[Calendar] Successfully fetched ${events.length} upcoming events`);
    return { events };
    
  } catch (error) {
    console.error('[Calendar] Error fetching calendar events:', error);
    return { events: [], error: error.message };
  }
}

/**
 * Get real GA4 analytics data using direct API calls
 */
async function getGA4Analytics(startDate, endDate, userId) {
  try {
    console.log(`[GA4 Analytics] Calling GA4 API directly for ${startDate}`);
    
    const { oauth2Client, propertyId } = await getAuthClient(userId);
    
    const analyticsDataClient = new BetaAnalyticsDataClient({
      authClient: oauth2Client
    });

    // Get ecommerce data with users
    console.log('[GA4 Analytics] Fetching ecommerce metrics...');
    const [ecommerceResponse] = await analyticsDataClient.runReport({
      property: `properties/${propertyId}`,
      dateRanges: [{ startDate, endDate }],
      metrics: [
        { name: 'totalRevenue' },
        { name: 'transactions' },
        { name: 'averagePurchaseRevenue' },
        { name: 'purchaseToViewRate' },
        { name: 'activeUsers' }
      ]
    });

    // Get traffic sources
    console.log('[GA4 Analytics] Fetching traffic sources...');
    const [trafficResponse] = await analyticsDataClient.runReport({
      property: `properties/${propertyId}`,
      dateRanges: [{ startDate, endDate }],
      dimensions: [{ name: 'sessionDefaultChannelGroup' }],
      metrics: [
        { name: 'sessions' },
        { name: 'totalRevenue' }
      ],
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
      limit: 5
    });

    // Get ads performance (with required sessionCampaignName dimension)
    console.log('[GA4 Analytics] Fetching ads performance...');
    let adsResponse = null;
    try {
      [adsResponse] = await analyticsDataClient.runReport({
        property: `properties/${propertyId}`,
        dateRanges: [{ startDate, endDate }],
        dimensions: [{ name: 'sessionCampaignName' }], // Required for ads metrics
        metrics: [
          { name: 'advertiserAdClicks' },
          { name: 'advertiserAdCost' },
          { name: 'advertiserAdCostPerClick' },
          { name: 'returnOnAdSpend' },
          { name: 'sessions' },
          { name: 'totalRevenue' },
          { name: 'conversions' }
        ]
      });
    } catch (adsError) {
      console.log('[GA4 Analytics] Ads metrics not available (likely no ad data):', adsError.message);
      adsResponse = { rows: [] };
    }

    // Parse ecommerce data
    const ecommerceSummary = ecommerceResponse.rows?.[0] || {};
    const ecommerce = {
      revenue: parseFloat(ecommerceSummary.metricValues?.[0]?.value || '0').toFixed(2),
      transactions: parseInt(ecommerceSummary.metricValues?.[1]?.value || '0'),
      aov: parseFloat(ecommerceSummary.metricValues?.[2]?.value || '0').toFixed(2),
      conversion_rate: (parseFloat(ecommerceSummary.metricValues?.[3]?.value || '0') * 100).toFixed(1) + '%',
      users: parseInt(ecommerceSummary.metricValues?.[4]?.value || '0')
    };

    // Parse traffic sources
    const traffic_sources = trafficResponse.rows?.map(row => ({
      source: row.dimensionValues[0]?.value || 'Unknown',
      users: parseInt(row.metricValues[0]?.value || '0'),
      revenue: parseFloat(row.metricValues[1]?.value || '0').toFixed(2)
    })) || [];

    // Parse ads data - aggregate across all campaigns
    let total_clicks = 0;
    let total_spend = 0;
    let total_sessions = 0;
    let total_revenue = 0;
    let total_conversions = 0;

    if (adsResponse?.rows?.length > 0) {
      adsResponse.rows.forEach(row => {
        total_clicks += parseInt(row.metricValues?.[0]?.value || '0');
        total_spend += parseFloat(row.metricValues?.[1]?.value || '0');
        total_sessions += parseInt(row.metricValues?.[4]?.value || '0');
        total_revenue += parseFloat(row.metricValues?.[5]?.value || '0');
        total_conversions += parseInt(row.metricValues?.[6]?.value || '0');
      });
    }

    const ads_performance = {
      total_spend: total_spend.toFixed(2),
      total_clicks: total_clicks,
      cpc: total_clicks > 0 ? (total_spend / total_clicks).toFixed(2) : '0',
      roas: total_spend > 0 ? (total_revenue / total_spend).toFixed(2) : '0'
    };

    console.log('[GA4 Analytics] Successfully fetched GA4 data:', {
      ecommerce,
      traffic_sources: traffic_sources.length,
      ads_performance
    });

    return { ecommerce, traffic_sources, ads_performance };
    
  } catch (error) {
    console.error('[GA4 Analytics] Error calling GA4 API:', error);
    return {
      ecommerce: { revenue: '0', transactions: 0, aov: '0', conversion_rate: '0%', users: '0' },
      traffic_sources: [],
      ads_performance: { total_spend: '0', total_clicks: 0, cpc: '0', roas: '0' }
    };
  }
}

/**
 * GET /api/dashboard/analytics
 * Fetch dashboard analytics data directly for dashboard UI
 */
router.get('/analytics', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id || 1;
    
    // Get date parameters from query string or default to yesterday
    const { start_date, end_date } = req.query;
    
    let startDate, endDate;
    if (start_date && end_date) {
      startDate = start_date;
      endDate = end_date;
    } else {
      // Default to yesterday
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const yesterdayStr = yesterday.toISOString().split('T')[0];
      startDate = yesterdayStr;
      endDate = yesterdayStr;
    }

    console.log(`[Dashboard Analytics] Fetching data for ${startDate} to ${endDate}`);

    // Fetch Shopify data using proper agent
    console.log('[Dashboard Analytics] Calling Shopify analytics...');
    const shopifyData = await getShopifyAnalytics(startDate, endDate, userId);

    // Fetch GA4 data using proper agent
    console.log('[Dashboard Analytics] Calling GA4 analytics...');
    const ga4Data = await getGA4Analytics(startDate, endDate, userId);

    // Fetch Google Workspace data
    console.log('[Dashboard Analytics] Calling Google Workspace APIs...');
    const [tasksData, emailsData, calendarData] = await Promise.all([
      getGoogleTasks(userId),
      getRecentEmails(userId, 10),
      getUpcomingCalendar(userId, 10)
    ]);

    // Calculate insights
    const insights = [];
    
    // Revenue comparison
    const shopifyRevenue = parseFloat(shopifyData.total_revenue?.replace(/[,$]/g, '') || '0');
    const ga4Revenue = parseFloat(ga4Data.ecommerce.revenue?.replace(/[,$]/g, '') || '0');
    const revenueDiff = Math.abs(shopifyRevenue - ga4Revenue);
    const revenueDiscrepancy = shopifyRevenue > 0 ? (revenueDiff / shopifyRevenue * 100) : 0;

    if (revenueDiscrepancy > 5) {
      insights.push(`Revenue discrepancy detected: Shopify reports $${shopifyData.total_revenue} while GA4 shows $${ga4Data.ecommerce.revenue} (${revenueDiscrepancy.toFixed(1)}% difference)`);
    } else {
      insights.push(`Revenue data is aligned between Shopify ($${shopifyData.total_revenue}) and GA4 ($${ga4Data.ecommerce.revenue})`);
    }

    // Performance insights
    if (shopifyData.top_products && shopifyData.top_products.length > 0) {
      const topProduct = shopifyData.top_products[0];
      insights.push(`Top performing product: ${topProduct.name} generated $${topProduct.revenue} from ${topProduct.quantity_sold} units sold`);
    }

    // ROAS insight
    const roas = parseFloat(ga4Data.ads_performance.roas || '0');
    if (roas > 3) {
      insights.push(`Excellent advertising performance with ${roas}x ROAS on $${ga4Data.ads_performance.total_spend} ad spend`);
    } else if (roas > 2) {
      insights.push(`Good advertising performance with ${roas}x ROAS, consider optimizing high-performing campaigns`);
    } else if (roas > 0) {
      insights.push(`Ad performance needs attention - ${roas}x ROAS on $${ga4Data.ads_performance.total_spend} spend suggests optimization needed`);
    }

    // Compile response
    const dashboardData = {
      date: startDate,
      endDate: endDate,
      dateRange: startDate === endDate ? startDate : `${startDate} to ${endDate}`,
      lastUpdated: new Date().toISOString(),
      shopify: {
        revenue: shopifyData.total_revenue || '0',
        orders: shopifyData.order_count || 0,
        aov: shopifyData.average_order_value || '0',
        top_products: shopifyData.top_products || []
      },
      ga4: {
        revenue: ga4Data.ecommerce.revenue || '0',
        users: ga4Data.ecommerce.users || '0',
        transactions: ga4Data.ecommerce.transactions || 0,
        conversion_rate: ga4Data.ecommerce.conversion_rate || '0%',
        roas: ga4Data.ads_performance.roas || '0',
        ad_spend: ga4Data.ads_performance.total_spend || '0',
        traffic_sources: ga4Data.traffic_sources || []
      },
      workspace: {
        tasks: {
          items: tasksData.tasks || [],
          error: tasksData.error || null,
          count: tasksData.tasks?.length || 0
        },
        emails: {
          items: emailsData.emails || [],
          error: emailsData.error || null,
          count: emailsData.emails?.length || 0
        },
        calendar: {
          items: calendarData.events || [],
          error: calendarData.error || null,
          count: calendarData.events?.length || 0
        }
      },
      insights,
      raw_data: {
        shopify: shopifyData,
        ga4: ga4Data,
        workspace: {
          tasks: tasksData,
          emails: emailsData,
          calendar: calendarData
        }
      }
    };

    console.log('[Dashboard Analytics] Successfully compiled dashboard data');
    res.json(dashboardData);

  } catch (error) {
    console.error('[Dashboard Analytics] Error:', error);
    res.status(500).json({
      error: 'Failed to fetch analytics data',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * GET /api/dashboard/summary
 * Provide a conversational summary of analytics data for agents
 */
router.get('/summary', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id || 1;
    const { date } = req.query;
    
    // Use provided date or default to yesterday
    let targetDate;
    if (date) {
      targetDate = date;
    } else {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      targetDate = yesterday.toISOString().split('T')[0];
    }

    console.log(`[Dashboard Summary] Generating conversational summary for ${targetDate}`);

    // Fetch the same data as the dashboard using direct tool calls
    const shopifyData = await getShopifyAnalytics(targetDate, targetDate, userId);
    const ga4Data = await getGA4Analytics(targetDate, targetDate, userId);

    // Create a conversational summary
    const summary = {
      date: targetDate,
      performance_overview: `On ${targetDate}, the store generated $${shopifyData.total_revenue || '0'} in revenue from ${shopifyData.order_count || 0} orders, with an average order value of $${shopifyData.average_order_value || '0'}.`,
      
      shopify_highlights: {
        revenue: shopifyData.total_revenue || '0',
        orders: shopifyData.order_count || 0,
        aov: shopifyData.average_order_value || '0',
        top_product: shopifyData.top_products?.[0] ? 
          `${shopifyData.top_products[0].name} was the top seller with ${shopifyData.top_products[0].quantity_sold} units sold for $${shopifyData.top_products[0].revenue} in revenue.` :
          'No top product data available.'
      },
      
      ga4_highlights: {
        users: ga4Data.ecommerce.users || 'N/A',
        conversion_rate: ga4Data.ecommerce.conversion_rate || '0%',
        ad_performance: `Google Ads spent $${ga4Data.ads_performance.total_spend || '0'} with a ${ga4Data.ads_performance.roas || '0'}x return on ad spend.`,
        top_traffic_source: ga4Data.traffic_sources?.[0] ? 
          `${ga4Data.traffic_sources[0].source} was the top traffic source with ${ga4Data.traffic_sources[0].users} users generating $${ga4Data.traffic_sources[0].revenue} in revenue.` :
          'No traffic source data available.'
      },
      
      key_insights: [
        `Revenue comparison: Shopify reports $${shopifyData.total_revenue || '0'} while GA4 shows $${ga4Data.ecommerce.revenue || '0'}`,
        `Advertising efficiency: ${ga4Data.ads_performance.roas || '0'}x ROAS on $${ga4Data.ads_performance.total_spend || '0'} ad spend`,
        shopifyData.top_products?.[0] ? 
          `Best performer: ${shopifyData.top_products[0].name} with $${shopifyData.top_products[0].revenue} revenue` :
          'Top product performance data not available'
      ].filter(insight => !insight.includes('not available')),
      
      formatted_summary: `**Daily Performance Summary for ${targetDate}**

**Shopify Performance:**
- Revenue: $${shopifyData.total_revenue || '0'}
- Orders: ${shopifyData.order_count || 0}
- Average Order Value: $${shopifyData.average_order_value || '0'}
${shopifyData.top_products?.[0] ? `- Top Product: ${shopifyData.top_products[0].name} ($${shopifyData.top_products[0].revenue})` : ''}

**Google Analytics Performance:**
- Active Users: ${ga4Data.ecommerce.users || 'N/A'}
- Conversion Rate: ${ga4Data.ecommerce.conversion_rate || '0%'}
- Ad Spend: $${ga4Data.ads_performance.total_spend || '0'}
- ROAS: ${ga4Data.ads_performance.roas || '0'}x
${ga4Data.traffic_sources?.[0] ? `- Top Traffic Source: ${ga4Data.traffic_sources[0].source} (${ga4Data.traffic_sources[0].users} users)` : ''}

**Key Insights:**
${shopifyData.total_revenue && ga4Data.ecommerce.revenue ? 
  `- Revenue tracking is ${Math.abs(parseFloat(shopifyData.total_revenue.replace(/[,$]/g, '')) - parseFloat(ga4Data.ecommerce.revenue.replace(/[,$]/g, ''))) < 100 ? 'aligned' : 'showing discrepancies'} between platforms` : 
  '- Revenue comparison requires both platforms to be reporting'
}
${parseFloat(ga4Data.ads_performance.roas || '0') > 2 ? '- Advertising performance is strong with good ROAS' : '- Advertising performance may need optimization'}
${shopifyData.top_products?.[0] ? `- ${shopifyData.top_products[0].name} is driving significant revenue` : ''}`,

      raw_data: {
        shopify: shopifyData,
        ga4: ga4Data
      }
    };

    console.log('[Dashboard Summary] Successfully generated conversational summary');
    res.json(summary);

  } catch (error) {
    console.error('[Dashboard Summary] Error:', error);
    res.status(500).json({
      error: 'Failed to generate analytics summary',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

export default router;