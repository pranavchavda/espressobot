/**
 * GA4 Analytics Direct Tools
 * Provides tools for accessing Google Analytics 4 data including advertising metrics
 */

import { z } from 'zod';
import { tool } from '@openai/agents';
import { BetaAnalyticsDataClient } from '@google-analytics/data';
import { PrismaClient } from '@prisma/client';
import { google } from 'googleapis';

const prisma = new PrismaClient();

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
    throw new Error('GA4 property ID not configured. Please set your GA4 property ID in settings.');
  }

  const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET
  );

  oauth2Client.setCredentials({
    access_token: user.google_access_token,
    refresh_token: user.google_refresh_token
  });

  // Handle token refresh if needed
  oauth2Client.on('tokens', async (tokens) => {
    await prisma.users.update({
      where: { id: userId },
      data: {
        google_access_token: tokens.access_token,
        google_token_expiry: new Date(Date.now() + (tokens.expiry_date || 3600000))
      }
    });
  });

  // Check if user has analytics scope
  try {
    const tokenInfo = await oauth2Client.getTokenInfo(user.google_access_token);
    const scopes = tokenInfo.scopes || [];
    
    if (!scopes.includes('https://www.googleapis.com/auth/analytics.readonly')) {
      throw new Error('Google Analytics permission not granted. Please log out and log in again to authorize analytics access.');
    }
  } catch (error) {
    if (error.message?.includes('Google Analytics permission')) {
      throw error;
    }
    // Token might be expired, let OAuth client handle refresh
    console.log('Token validation failed, will attempt refresh:', error.message);
  }

  return { oauth2Client, propertyId: user.ga4_property_id };
}

/**
 * Core Analytics Tools
 */
export function createGA4CoreTools() {
  return [
    tool({
      name: 'analytics_run_report',
      description: 'Run a custom GA4 report with specified dimensions and metrics',
      parameters: z.object({
        startDate: z.string().describe('Start date (YYYY-MM-DD or relative like "7daysAgo")'),
        endDate: z.string().describe('End date (YYYY-MM-DD or relative like "today")'),
        dimensions: z.array(z.string()).describe('Dimension names (e.g., ["date", "country", "deviceCategory"])'),
        metrics: z.array(z.string()).describe('Metric names (e.g., ["activeUsers", "sessions", "bounceRate"])'),
        dimensionFilter: z.object({
          dimension: z.string(),
          operator: z.enum(['EXACT', 'BEGINS_WITH', 'ENDS_WITH', 'CONTAINS', 'NUMERIC_EQUAL', 'NUMERIC_GREATER_THAN', 'NUMERIC_LESS_THAN']),
          value: z.string()
        }).nullable().default(null).describe('Optional dimension filter'),
        orderBy: z.string().nullable().default(null).describe('Metric or dimension to order by'),
        limit: z.number().default(10).describe('Maximum number of rows to return')
      }),
      execute: async ({ startDate, endDate, dimensions, metrics, dimensionFilter, orderBy, limit }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const request = {
          property: `properties/${propertyId}`,
          dateRanges: [{ startDate, endDate }],
          dimensions: dimensions.map(name => ({ name })),
          metrics: metrics.map(name => ({ name })),
          limit
        };

        if (dimensionFilter) {
          request.dimensionFilter = {
            filter: {
              fieldName: dimensionFilter.dimension,
              stringFilter: {
                matchType: dimensionFilter.operator,
                value: dimensionFilter.value
              }
            }
          };
        }

        if (orderBy) {
          request.orderBys = [{
            metric: { metricName: orderBy },
            desc: true
          }];
        }

        const [response] = await analyticsDataClient.runReport(request);
        
        return {
          rows: response.rows?.map(row => ({
            dimensions: row.dimensionValues.map((v, i) => ({
              name: dimensions[i],
              value: v.value
            })),
            metrics: row.metricValues.map((v, i) => ({
              name: metrics[i],
              value: v.value
            }))
          })) || [],
          rowCount: response.rowCount,
          metadata: {
            dimensions: response.dimensionHeaders,
            metrics: response.metricHeaders
          }
        };
      }
    }),

    tool({
      name: 'analytics_get_realtime',
      description: 'Get real-time visitor data from GA4',
      parameters: z.object({
        dimensions: z.array(z.string()).default(['unifiedScreenName']).describe('Dimensions for real-time data'),
        metrics: z.array(z.string()).default(['activeUsers']).describe('Metrics for real-time data')
      }),
      execute: async ({ dimensions, metrics }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const [response] = await analyticsDataClient.runRealtimeReport({
          property: `properties/${propertyId}`,
          dimensions: dimensions.map(name => ({ name })),
          metrics: metrics.map(name => ({ name }))
        });

        const totalActiveUsers = response.rows?.reduce((sum, row) => {
          const activeUsersValue = row.metricValues[0]?.value || '0';
          return sum + parseInt(activeUsersValue);
        }, 0) || 0;

        return {
          totalActiveUsers,
          byPage: response.rows?.map(row => ({
            page: row.dimensionValues[0]?.value || 'Unknown',
            activeUsers: parseInt(row.metricValues[0]?.value || '0')
          })) || []
        };
      }
    }),

    tool({
      name: 'analytics_get_ecommerce',
      description: 'Get ecommerce metrics including revenue, transactions, and conversion rate',
      parameters: z.object({
        startDate: z.string().describe('Start date (YYYY-MM-DD or relative)'),
        endDate: z.string().describe('End date (YYYY-MM-DD or relative)'),
        groupBy: z.enum(['date', 'week', 'month', 'deviceCategory', 'country']).nullable().default(null).describe('Group results by dimension')
      }),
      execute: async ({ startDate, endDate, groupBy }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const dimensions = groupBy ? [{ name: groupBy }] : [];
        
        const [response] = await analyticsDataClient.runReport({
          property: `properties/${propertyId}`,
          dateRanges: [{ startDate, endDate }],
          dimensions,
          metrics: [
            { name: 'totalRevenue' },
            { name: 'transactions' },
            { name: 'ecommercePurchases' },
            { name: 'averagePurchaseRevenue' },
            { name: 'purchaseToViewRate' },
            { name: 'cartToViewRate' }
          ]
        });

        const summary = response.rows?.[0] || {};
        
        return {
          summary: {
            revenue: parseFloat(summary.metricValues?.[0]?.value || '0'),
            transactions: parseInt(summary.metricValues?.[1]?.value || '0'),
            purchases: parseInt(summary.metricValues?.[2]?.value || '0'),
            averageOrderValue: parseFloat(summary.metricValues?.[3]?.value || '0'),
            purchaseToViewRate: parseFloat(summary.metricValues?.[4]?.value || '0'),
            cartToViewRate: parseFloat(summary.metricValues?.[5]?.value || '0')
          },
          breakdown: groupBy ? response.rows?.map(row => ({
            [groupBy]: row.dimensionValues[0]?.value || 'Unknown',
            revenue: parseFloat(row.metricValues[0]?.value || '0'),
            transactions: parseInt(row.metricValues[1]?.value || '0')
          })) : null
        };
      }
    }),

    tool({
      name: 'analytics_get_traffic_sources',
      description: 'Analyze traffic sources and channels',
      parameters: z.object({
        startDate: z.string().describe('Start date'),
        endDate: z.string().describe('End date'),
        includeOrganicVsPaid: z.boolean().default(true).describe('Include organic vs paid breakdown')
      }),
      execute: async ({ startDate, endDate, includeOrganicVsPaid }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const [response] = await analyticsDataClient.runReport({
          property: `properties/${propertyId}`,
          dateRanges: [{ startDate, endDate }],
          dimensions: [
            { name: 'sessionDefaultChannelGroup' },
            { name: 'sessionSource' }
          ],
          metrics: [
            { name: 'sessions' },
            { name: 'activeUsers' },
            { name: 'totalRevenue' },
            { name: 'conversions' }
          ],
          orderBys: [{
            metric: { metricName: 'sessions' },
            desc: true
          }],
          limit: 20
        });

        const channels = {};
        response.rows?.forEach(row => {
          const channel = row.dimensionValues[0]?.value || 'Unknown';
          const source = row.dimensionValues[1]?.value || 'Unknown';
          
          if (!channels[channel]) {
            channels[channel] = {
              sessions: 0,
              users: 0,
              revenue: 0,
              conversions: 0,
              sources: []
            };
          }
          
          channels[channel].sessions += parseInt(row.metricValues[0]?.value || '0');
          channels[channel].users += parseInt(row.metricValues[1]?.value || '0');
          channels[channel].revenue += parseFloat(row.metricValues[2]?.value || '0');
          channels[channel].conversions += parseInt(row.metricValues[3]?.value || '0');
          channels[channel].sources.push(source);
        });

        return {
          channels: Object.entries(channels).map(([name, data]) => ({
            name,
            ...data,
            sources: [...new Set(data.sources)].slice(0, 5)
          })),
          organicVsPaid: includeOrganicVsPaid ? {
            organic: Object.entries(channels)
              .filter(([name]) => ['Organic Search', 'Direct', 'Organic Social'].includes(name))
              .reduce((sum, [, data]) => sum + data.sessions, 0),
            paid: Object.entries(channels)
              .filter(([name]) => ['Paid Search', 'Paid Social', 'Display'].includes(name))
              .reduce((sum, [, data]) => sum + data.sessions, 0)
          } : null
        };
      }
    }),

    tool({
      name: 'analytics_get_product_performance',
      description: 'Get product-level analytics data',
      parameters: z.object({
        startDate: z.string().describe('Start date'),
        endDate: z.string().describe('End date'),
        limit: z.number().default(20).describe('Number of products to return')
      }),
      execute: async ({ startDate, endDate, limit }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const [response] = await analyticsDataClient.runReport({
          property: `properties/${propertyId}`,
          dateRanges: [{ startDate, endDate }],
          dimensions: [
            { name: 'itemName' },
            { name: 'itemId' }
          ],
          metrics: [
            { name: 'itemRevenue' },
            { name: 'itemsPurchased' },
            { name: 'itemsViewed' },
            { name: 'itemsAddedToCart' },
            { name: 'cartToViewRate' },
            { name: 'purchaseToViewRate' }
          ],
          orderBys: [{
            metric: { metricName: 'itemRevenue' },
            desc: true
          }],
          limit
        });

        return {
          products: response.rows?.map(row => ({
            name: row.dimensionValues[0]?.value || 'Unknown',
            id: row.dimensionValues[1]?.value || 'Unknown',
            revenue: parseFloat(row.metricValues[0]?.value || '0'),
            quantitySold: parseInt(row.metricValues[1]?.value || '0'),
            views: parseInt(row.metricValues[2]?.value || '0'),
            addedToCart: parseInt(row.metricValues[3]?.value || '0'),
            cartToViewRate: parseFloat(row.metricValues[4]?.value || '0'),
            purchaseToViewRate: parseFloat(row.metricValues[5]?.value || '0')
          })) || []
        };
      }
    })
  ];
}

/**
 * Advertising/AdWords Tools (via GA4)
 */
export function createGA4AdvertisingTools() {
  return [
    tool({
      name: 'analytics_get_ads_performance',
      description: 'Get Google Ads performance metrics including spend, clicks, and ROI',
      parameters: z.object({
        startDate: z.string().describe('Start date'),
        endDate: z.string().describe('End date'),
        groupBy: z.enum(['date', 'campaign', 'adGroup', 'keyword']).nullable().default(null).describe('Group results by dimension')
      }),
      execute: async ({ startDate, endDate, groupBy }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const dimensionMap = {
          campaign: 'sessionGoogleAdsCampaignName',
          adGroup: 'sessionGoogleAdsAdGroupName',
          keyword: 'sessionGoogleAdsKeyword',
          date: 'date'
        };

        const dimensions = groupBy ? [{ name: dimensionMap[groupBy] }] : [];

        const [response] = await analyticsDataClient.runReport({
          property: `properties/${propertyId}`,
          dateRanges: [{ startDate, endDate }],
          dimensions,
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

        const summary = response.rows?.[0] || {};
        
        return {
          summary: {
            clicks: parseInt(summary.metricValues?.[0]?.value || '0'),
            cost: parseFloat(summary.metricValues?.[1]?.value || '0'),
            cpc: parseFloat(summary.metricValues?.[2]?.value || '0'),
            roas: parseFloat(summary.metricValues?.[3]?.value || '0'),
            sessions: parseInt(summary.metricValues?.[4]?.value || '0'),
            revenue: parseFloat(summary.metricValues?.[5]?.value || '0'),
            conversions: parseInt(summary.metricValues?.[6]?.value || '0')
          },
          breakdown: groupBy ? response.rows?.map(row => ({
            [groupBy]: row.dimensionValues[0]?.value || 'Unknown',
            clicks: parseInt(row.metricValues[0]?.value || '0'),
            cost: parseFloat(row.metricValues[1]?.value || '0'),
            revenue: parseFloat(row.metricValues[5]?.value || '0'),
            roas: parseFloat(row.metricValues[3]?.value || '0')
          })) : null
        };
      }
    }),

    tool({
      name: 'analytics_get_campaign_performance',
      description: 'Get detailed campaign performance with conversion attribution',
      parameters: z.object({
        startDate: z.string().describe('Start date'),
        endDate: z.string().describe('End date'),
        campaignName: z.string().nullable().default(null).describe('Filter by specific campaign name')
      }),
      execute: async ({ startDate, endDate, campaignName }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const request = {
          property: `properties/${propertyId}`,
          dateRanges: [{ startDate, endDate }],
          dimensions: [
            { name: 'sessionGoogleAdsCampaignName' },
            { name: 'sessionSourceMedium' }
          ],
          metrics: [
            { name: 'sessions' },
            { name: 'activeUsers' },
            { name: 'conversions' },
            { name: 'totalRevenue' },
            { name: 'advertiserAdCost' },
            { name: 'returnOnAdSpend' }
          ],
          orderBys: [{
            metric: { metricName: 'totalRevenue' },
            desc: true
          }]
        };

        if (campaignName) {
          request.dimensionFilter = {
            filter: {
              fieldName: 'sessionGoogleAdsCampaignName',
              stringFilter: {
                matchType: 'CONTAINS',
                value: campaignName
              }
            }
          };
        }

        const [response] = await analyticsDataClient.runReport(request);

        return {
          campaigns: response.rows?.map(row => ({
            name: row.dimensionValues[0]?.value || 'Unknown',
            sourceMedium: row.dimensionValues[1]?.value || 'Unknown',
            sessions: parseInt(row.metricValues[0]?.value || '0'),
            users: parseInt(row.metricValues[1]?.value || '0'),
            conversions: parseInt(row.metricValues[2]?.value || '0'),
            revenue: parseFloat(row.metricValues[3]?.value || '0'),
            cost: parseFloat(row.metricValues[4]?.value || '0'),
            roas: parseFloat(row.metricValues[5]?.value || '0'),
            conversionRate: row.metricValues[0]?.value ? 
              (parseInt(row.metricValues[2]?.value || '0') / parseInt(row.metricValues[0]?.value || '1') * 100).toFixed(2) : '0'
          })) || []
        };
      }
    }),

    tool({
      name: 'analytics_get_ads_keywords',
      description: 'Get keyword performance data from Google Ads',
      parameters: z.object({
        startDate: z.string().describe('Start date'),
        endDate: z.string().describe('End date'),
        limit: z.number().default(50).describe('Number of keywords to return')
      }),
      execute: async ({ startDate, endDate, limit }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const [response] = await analyticsDataClient.runReport({
          property: `properties/${propertyId}`,
          dateRanges: [{ startDate, endDate }],
          dimensions: [
            { name: 'sessionGoogleAdsKeyword' },
            { name: 'sessionGoogleAdsQuery' }
          ],
          metrics: [
            { name: 'advertiserAdClicks' },
            { name: 'advertiserAdCost' },
            { name: 'conversions' },
            { name: 'totalRevenue' }
          ],
          orderBys: [{
            metric: { metricName: 'totalRevenue' },
            desc: true
          }],
          limit
        });

        return {
          keywords: response.rows?.map(row => ({
            keyword: row.dimensionValues[0]?.value || 'Unknown',
            searchQuery: row.dimensionValues[1]?.value || 'Not provided',
            clicks: parseInt(row.metricValues[0]?.value || '0'),
            cost: parseFloat(row.metricValues[1]?.value || '0'),
            conversions: parseInt(row.metricValues[2]?.value || '0'),
            revenue: parseFloat(row.metricValues[3]?.value || '0'),
            cpa: row.metricValues[2]?.value && parseInt(row.metricValues[2]?.value) > 0 ?
              (parseFloat(row.metricValues[1]?.value || '0') / parseInt(row.metricValues[2]?.value)).toFixed(2) : 'N/A'
          })) || []
        };
      }
    }),

    tool({
      name: 'analytics_compare_channels',
      description: 'Compare performance across different marketing channels including organic vs paid',
      parameters: z.object({
        startDate: z.string().describe('Start date'),
        endDate: z.string().describe('End date')
      }),
      execute: async ({ startDate, endDate }) => {
        const userId = global.currentUserId;
        const { oauth2Client, propertyId } = await getAuthClient(userId);
        
        const analyticsDataClient = new BetaAnalyticsDataClient({
          authClient: oauth2Client
        });

        const [response] = await analyticsDataClient.runReport({
          property: `properties/${propertyId}`,
          dateRanges: [{ startDate, endDate }],
          dimensions: [
            { name: 'sessionDefaultChannelGroup' },
            { name: 'sessionSourceMedium' }
          ],
          metrics: [
            { name: 'sessions' },
            { name: 'activeUsers' },
            { name: 'conversions' },
            { name: 'totalRevenue' },
            { name: 'advertiserAdCost' }
          ]
        });

        const channelData = {};
        response.rows?.forEach(row => {
          const channel = row.dimensionValues[0]?.value || 'Unknown';
          const sourceMedium = row.dimensionValues[1]?.value || 'Unknown';
          
          if (!channelData[channel]) {
            channelData[channel] = {
              sessions: 0,
              users: 0,
              conversions: 0,
              revenue: 0,
              cost: 0,
              sources: new Set()
            };
          }
          
          channelData[channel].sessions += parseInt(row.metricValues[0]?.value || '0');
          channelData[channel].users += parseInt(row.metricValues[1]?.value || '0');
          channelData[channel].conversions += parseInt(row.metricValues[2]?.value || '0');
          channelData[channel].revenue += parseFloat(row.metricValues[3]?.value || '0');
          channelData[channel].cost += parseFloat(row.metricValues[4]?.value || '0');
          channelData[channel].sources.add(sourceMedium);
        });

        const channels = Object.entries(channelData).map(([name, data]) => ({
          channel: name,
          sessions: data.sessions,
          users: data.users,
          conversions: data.conversions,
          revenue: data.revenue,
          cost: data.cost,
          conversionRate: data.sessions > 0 ? (data.conversions / data.sessions * 100).toFixed(2) : '0',
          roas: data.cost > 0 ? (data.revenue / data.cost).toFixed(2) : 'N/A',
          avgOrderValue: data.conversions > 0 ? (data.revenue / data.conversions).toFixed(2) : '0',
          topSources: Array.from(data.sources).slice(0, 3)
        }));

        // Calculate organic vs paid
        const organic = channels.filter(c => 
          ['Organic Search', 'Direct', 'Organic Social', 'Referral', 'Email'].includes(c.channel)
        );
        const paid = channels.filter(c => 
          ['Paid Search', 'Paid Social', 'Display', 'Paid Shopping', 'Affiliates'].includes(c.channel)
        );

        return {
          channels: channels.sort((a, b) => b.revenue - a.revenue),
          comparison: {
            organic: {
              sessions: organic.reduce((sum, c) => sum + c.sessions, 0),
              revenue: organic.reduce((sum, c) => sum + c.revenue, 0),
              conversions: organic.reduce((sum, c) => sum + c.conversions, 0),
              cost: 0
            },
            paid: {
              sessions: paid.reduce((sum, c) => sum + c.sessions, 0),
              revenue: paid.reduce((sum, c) => sum + c.revenue, 0),
              conversions: paid.reduce((sum, c) => sum + c.conversions, 0),
              cost: paid.reduce((sum, c) => sum + c.cost, 0)
            }
          }
        };
      }
    })
  ];
}

/**
 * Create all GA4 tools
 */
export function createGA4Tools() {
  return [
    ...createGA4CoreTools(),
    ...createGA4AdvertisingTools()
  ];
}