/**
 * GA4 Analytics Agent
 * Specialized agent for Google Analytics 4 data analysis including advertising metrics
 */

import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { createGA4Tools } from '../tools/ga4-analytics-direct-tools.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

/**
 * Create GA4 Analytics agent with appropriate tools
 */
async function createAgent(task, conversationId, richContext = {}) {
  let tools = [];
  
  // Get GA4 tools
  const ga4Tools = createGA4Tools();
  tools = [...tools, ...ga4Tools];

  // Build system prompt with GA4 expertise
  const today = new Date().toISOString().split('T')[0];
  let systemPrompt = `You are a Google Analytics 4 specialist agent with expertise in ecommerce analytics and advertising metrics.

Today's date: ${today}

Your task: ${task}

You have access to the following GA4 tools:

## Core Analytics Tools:
- **analytics_run_report**: Run custom reports with any combination of dimensions and metrics
  - Common dimensions: date, country, deviceCategory, city, pagePath, sessionDefaultChannelGroup
  - Common metrics: activeUsers, sessions, bounceRate, engagementRate, totalRevenue
  
- **analytics_get_realtime**: Get real-time visitor data
  - Shows current active users and their locations
  
- **analytics_get_ecommerce**: Get ecommerce performance metrics
  - Revenue, transactions, AOV, conversion rates
  - Can group by date, device, country
  
- **analytics_get_traffic_sources**: Analyze traffic channels
  - Breakdown by channel (Organic, Paid, Direct, etc.)
  - Shows revenue and conversions by source
  
- **analytics_get_product_performance**: Product-level analytics
  - Best sellers, views, add-to-cart rates
  - Revenue by product

## Advertising/AdWords Tools:
- **analytics_get_ads_performance**: Google Ads metrics overview
  - Ad spend, clicks, CPC, ROAS
  - Can group by date, campaign, ad group, keyword
  
- **analytics_get_campaign_performance**: Detailed campaign analysis
  - Campaign-level revenue, conversions, ROAS
  - Includes attribution data
  
- **analytics_get_ads_keywords**: Keyword performance from Google Ads
  - Cost per acquisition by keyword
  - Revenue attribution by search terms
  
- **analytics_compare_channels**: Compare all marketing channels
  - Organic vs Paid performance
  - Channel contribution to revenue
  - Multi-channel analysis

## Date Formatting:
- Use relative dates: "today", "yesterday", "7daysAgo", "30daysAgo"
- Or specific dates: "2025-01-01"
- For ranges: startDate="30daysAgo", endDate="today"

## Common Ecommerce Queries:
- "What's today's revenue?" → Use analytics_get_ecommerce
- "Show Google Ads spend this month" → Use analytics_get_ads_performance
- "Which products are selling best?" → Use analytics_get_product_performance
- "Compare organic vs paid traffic" → Use analytics_compare_channels
- "What's my ROAS by campaign?" → Use analytics_get_campaign_performance

## Advertising Metrics:
- **ROAS**: Return on Ad Spend (Revenue / Cost)
- **CPC**: Cost Per Click
- **CPA**: Cost Per Acquisition (Cost / Conversions)
- **CTR**: Click Through Rate (Clicks / Impressions)

## Important Notes:
- All monetary values are in the store's currency
- Ensure Google Ads is properly linked to GA4 for advertising data
- Some metrics may show as 0 if tracking is not configured
- Format currency values with appropriate symbols
- Present data in clear, business-friendly language

## Response Guidelines:
- Always include the date range in your response
- Format large numbers with commas (e.g., 1,234)
- Show percentages with one decimal place (e.g., 12.3%)
- Highlight key insights and trends
- Suggest actionable recommendations when appropriate

IMPORTANT:
- Handle missing data gracefully
- Explain if certain metrics require additional configuration
- Be clear about what each metric means in business terms`;

  // Create the agent
  const agent = new Agent({
    name: 'GA4 Analytics Agent',
    instructions: systemPrompt,
    tools,
    model: 'gpt-4.1'
  });

  return agent;
}

/**
 * Execute a GA4 analytics task
 */
export async function executeGA4Task(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[GA4 Analytics Agent] Starting task execution...');
    console.log('[GA4 Analytics Agent] Task:', task);
    
    // Set the current user ID for direct tools
    if (richContext.userId) {
      global.currentUserId = richContext.userId;
    }
    
    // Create agent
    const agent = await createAgent(task, conversationId, richContext);
    
    // Set reasonable limits
    const maxTurns = 10;
    const timeout = 60000; // 60 seconds
    
    // Create a promise that rejects after timeout
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Task execution timed out after ${timeout/1000} seconds`));
      }, timeout);
    });
    
    const executionPromise = run(agent, task, { maxTurns });
    const result = await Promise.race([executionPromise, timeoutPromise]);
    
    console.log('[GA4 Analytics Agent] Task completed successfully');
    
    // Debug: Log the result structure
    if (process.env.NODE_ENV === 'development') {
      console.log('[GA4 Analytics Agent] Result structure:', {
        hasState: !!result?.state,
        hasGeneratedItems: !!result?.state?._generatedItems,
        generatedItemsCount: result?.state?._generatedItems?.length || 0,
        resultKeys: result ? Object.keys(result) : []
      });
    }
    
    // Extract meaningful output
    let finalOutput = '';
    
    if (result.finalOutput) {
      finalOutput = result.finalOutput;
    } else if (result.state && result.state._generatedItems) {
      // Look for message_output_item type (OpenAI SDK v0.11 structure)
      const messages = result.state._generatedItems
        .filter(item => item.type === 'message_output_item')
        .map(item => item.rawItem?.content?.[0]?.text || '')
        .filter(text => text);
      
      if (messages.length > 0) {
        finalOutput = messages[messages.length - 1];
      }
    } else if (result.state && result.state.currentStep && result.state.currentStep.output) {
      finalOutput = result.state.currentStep.output;
    }
    
    // Log token usage if available
    if (result.state?.context?.usage) {
      const usage = result.state.context.usage;
      console.log(`[GA4 Analytics Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'ga4_analytics',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[GA4 Analytics Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}