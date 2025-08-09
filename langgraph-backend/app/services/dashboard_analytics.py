"""
Dashboard Analytics Service
Provides direct access to analytics data without LLM processing
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import User
from app.tools.mcp_client import get_mcp_manager

logger = logging.getLogger(__name__)


class DashboardAnalyticsService:
    """Service for fetching dashboard analytics data from multiple sources"""
    
    def __init__(self):
        self.mcp_manager = None
    
    async def _get_mcp_manager(self):
        """Get or initialize MCP manager"""
        if self.mcp_manager is None:
            self.mcp_manager = await get_mcp_manager()
        return self.mcp_manager
    
    async def get_shopify_analytics(
        self, 
        start_date: str, 
        end_date: str, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get Shopify analytics using existing MCP client
        """
        try:
            logger.info(f"[Shopify Analytics] Calling analytics_order_summary directly for {start_date}")
            
            mcp_manager = await self._get_mcp_manager()
            
            # Use the orders MCP server for analytics data
            result = await mcp_manager.call_tool('orders', 'analytics_order_summary', {
                'start_date': start_date,
                'end_date': end_date,
                'include_products': True,
                'product_limit': 10
            })
            
            logger.info(f"[Shopify Analytics] Raw MCP response: {result}")
            
            # Handle different MCP response formats
            # Format 1: Direct success/data format
            if result and result.get('success') and result.get('data'):
                data = result['data']
                return {
                    'total_revenue': str(data.get('summary', {}).get('total_revenue', '0')),
                    'order_count': data.get('summary', {}).get('order_count', 0),
                    'average_order_value': str(data.get('summary', {}).get('average_order_value', '0')),
                    'top_products': data.get('top_products', []),
                    'raw_response': result
                }
            # Format 2: MCP content array format
            elif result and 'content' in result:
                content = result.get('content', [])
                if content and len(content) > 0:
                    # Parse the text content as JSON
                    import json
                    try:
                        text_data = content[0].get('text', '{}')
                        parsed_data = json.loads(text_data)
                        
                        if parsed_data.get('success') and parsed_data.get('data'):
                            data = parsed_data['data']
                            return {
                                'total_revenue': str(data.get('summary', {}).get('total_revenue', '0')),
                                'order_count': data.get('summary', {}).get('order_count', 0),
                                'average_order_value': str(data.get('summary', {}).get('average_order_value', '0')),
                                'top_products': data.get('top_products', []),
                                'raw_response': parsed_data
                            }
                    except json.JSONDecodeError as e:
                        logger.error(f"[Shopify Analytics] Failed to parse JSON from MCP response: {e}")
            
            # Default fallback
            logger.error(f"[Shopify Analytics] Unexpected result format: {result}")
            return {
                'total_revenue': '0', 
                'order_count': 0, 
                'average_order_value': '0', 
                'top_products': []
            }
                
        except Exception as error:
            logger.error(f"[Shopify Analytics] Error calling MCP tool: {error}")
            return {
                'total_revenue': '0', 
                'order_count': 0, 
                'average_order_value': '0', 
                'top_products': []
            }
    
    async def _get_google_auth_client(self, user: User) -> Optional[Credentials]:
        """Get OAuth2 credentials for Google APIs"""
        if not user.google_access_token:
            raise Exception("User not authenticated with Google")
        
        credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        )
        
        return credentials
    
    async def get_google_tasks(self, user: User) -> Dict[str, Any]:
        """Get Google Tasks data using direct API calls"""
        try:
            logger.info("[Google Tasks] Fetching tasks from Google Tasks API...")
            
            if not user.google_access_token:
                logger.info("[Google Tasks] User not authenticated with Google")
                return {'tasks': [], 'error': 'Not authenticated with Google'}
            
            credentials = await self._get_google_auth_client(user)
            service = build('tasks', 'v1', credentials=credentials)
            
            # Get tasks from default task list
            results = service.tasks().list(
                tasklist='@default',
                showCompleted=False,
                showHidden=False,
                maxResults=10
            ).execute()
            
            items = results.get('items', [])
            tasks = []
            
            for task in items:
                tasks.append({
                    'id': task.get('id'),
                    'title': task.get('title'),
                    'notes': task.get('notes'),
                    'status': task.get('status'),
                    'due': task.get('due'),
                    'updated': task.get('updated')
                })
            
            logger.info(f"[Google Tasks] Successfully fetched {len(tasks)} tasks")
            return {'tasks': tasks}
            
        except Exception as error:
            logger.error(f"[Google Tasks] Error fetching tasks: {error}")
            return {'tasks': [], 'error': str(error)}
    
    async def get_recent_emails(self, user: User, max_results: int = 10) -> Dict[str, Any]:
        """Get recent emails from Gmail using direct API calls"""
        try:
            logger.info("[Gmail] Fetching recent emails from Gmail API...")
            
            if not user.google_access_token:
                logger.info("[Gmail] User not authenticated with Google")
                return {'emails': [], 'error': 'Not authenticated with Google'}
            
            credentials = await self._get_google_auth_client(user)
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get recent emails from inbox
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                try:
                    detail = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['Subject', 'From', 'Date']
                    ).execute()
                    
                    headers = detail.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                    
                    emails.append({
                        'id': msg['id'],
                        'subject': subject,
                        'from': from_addr,
                        'date': date,
                        'snippet': detail.get('snippet', '')
                    })
                except Exception as err:
                    logger.error(f"[Gmail] Error fetching email details: {err}")
                    continue
            
            logger.info(f"[Gmail] Successfully fetched {len(emails)} emails")
            return {'emails': emails}
            
        except Exception as error:
            logger.error(f"[Gmail] Error fetching emails: {error}")
            return {'emails': [], 'error': str(error)}
    
    async def get_upcoming_calendar(self, user: User, max_results: int = 10) -> Dict[str, Any]:
        """Get upcoming calendar events using direct API calls"""
        try:
            logger.info("[Calendar] Fetching upcoming events from Google Calendar API...")
            
            if not user.google_access_token:
                logger.info("[Calendar] User not authenticated with Google")
                return {'events': [], 'error': 'Not authenticated with Google'}
            
            credentials = await self._get_google_auth_client(user)
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get upcoming events
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            formatted_events = []
            
            for event in events:
                formatted_events.append({
                    'id': event.get('id'),
                    'summary': event.get('summary', 'No Title'),
                    'description': event.get('description'),
                    'start': event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
                    'end': event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
                    'location': event.get('location'),
                    'htmlLink': event.get('htmlLink')
                })
            
            logger.info(f"[Calendar] Successfully fetched {len(formatted_events)} upcoming events")
            return {'events': formatted_events}
            
        except Exception as error:
            logger.error(f"[Calendar] Error fetching calendar events: {error}")
            return {'events': [], 'error': str(error)}
    
    async def get_ga4_analytics(
        self, 
        start_date: str, 
        end_date: str, 
        user: User
    ) -> Dict[str, Any]:
        """Get real GA4 analytics data using direct API calls"""
        try:
            logger.info(f"[GA4 Analytics] Calling GA4 API directly for {start_date}")
            
            if not user.ga4_enabled:
                raise Exception("GA4 integration not enabled for this user")
            
            if not user.ga4_property_id:
                raise Exception("GA4 property ID not configured")
            
            credentials = await self._get_google_auth_client(user)
            
            # Create analytics data client
            client = BetaAnalyticsDataClient(credentials=credentials)
            
            # Get ecommerce data with users
            logger.info("[GA4 Analytics] Fetching ecommerce metrics...")
            ecommerce_request = {
                'property': f'properties/{user.ga4_property_id}',
                'date_ranges': [{'start_date': start_date, 'end_date': end_date}],
                'metrics': [
                    {'name': 'totalRevenue'},
                    {'name': 'transactions'},
                    {'name': 'averagePurchaseRevenue'},
                    {'name': 'purchaseToViewRate'},
                    {'name': 'activeUsers'}
                ]
            }
            
            ecommerce_response = client.run_report(request=ecommerce_request)
            
            # Get traffic sources
            logger.info("[GA4 Analytics] Fetching traffic sources...")
            traffic_request = {
                'property': f'properties/{user.ga4_property_id}',
                'date_ranges': [{'start_date': start_date, 'end_date': end_date}],
                'dimensions': [{'name': 'sessionDefaultChannelGroup'}],
                'metrics': [
                    {'name': 'sessions'},
                    {'name': 'totalRevenue'}
                ],
                'order_bys': [{'metric': {'metric_name': 'sessions'}, 'desc': True}],
                'limit': 5
            }
            
            traffic_response = client.run_report(request=traffic_request)
            
            # Get ads performance
            logger.info("[GA4 Analytics] Fetching ads performance...")
            ads_response = None
            try:
                ads_request = {
                    'property': f'properties/{user.ga4_property_id}',
                    'date_ranges': [{'start_date': start_date, 'end_date': end_date}],
                    'dimensions': [{'name': 'sessionCampaignName'}],
                    'metrics': [
                        {'name': 'advertiserAdClicks'},
                        {'name': 'advertiserAdCost'},
                        {'name': 'advertiserAdCostPerClick'},
                        {'name': 'returnOnAdSpend'},
                        {'name': 'sessions'},
                        {'name': 'totalRevenue'},
                        {'name': 'conversions'}
                    ]
                }
                
                ads_response = client.run_report(request=ads_request)
            except Exception as ads_error:
                logger.info(f"[GA4 Analytics] Ads metrics not available (likely no ad data): {ads_error}")
                ads_response = type('Response', (), {'rows': []})()
            
            # Parse ecommerce data
            ecommerce_summary = {}
            if ecommerce_response.rows:
                row = ecommerce_response.rows[0]
                ecommerce_summary = {
                    'revenue': f"{float(row.metric_values[0].value or '0'):.2f}",
                    'transactions': int(row.metric_values[1].value or '0'),
                    'aov': f"{float(row.metric_values[2].value or '0'):.2f}",
                    'conversion_rate': f"{float(row.metric_values[3].value or '0') * 100:.1f}%",
                    'users': int(row.metric_values[4].value or '0')
                }
            else:
                ecommerce_summary = {
                    'revenue': '0',
                    'transactions': 0,
                    'aov': '0',
                    'conversion_rate': '0%',
                    'users': 0
                }
            
            # Parse traffic sources
            traffic_sources = []
            for row in traffic_response.rows:
                traffic_sources.append({
                    'source': row.dimension_values[0].value or 'Unknown',
                    'users': int(row.metric_values[0].value or '0'),
                    'revenue': f"{float(row.metric_values[1].value or '0'):.2f}"
                })
            
            # Parse ads data - aggregate across all campaigns
            total_clicks = 0
            total_spend = 0.0
            total_sessions = 0
            total_revenue = 0.0
            total_conversions = 0
            
            for row in ads_response.rows:
                total_clicks += int(row.metric_values[0].value or '0')
                total_spend += float(row.metric_values[1].value or '0')
                total_sessions += int(row.metric_values[4].value or '0')
                total_revenue += float(row.metric_values[5].value or '0')
                total_conversions += int(row.metric_values[6].value or '0')
            
            ads_performance = {
                'total_spend': f"{total_spend:.2f}",
                'total_clicks': total_clicks,
                'cpc': f"{(total_spend / total_clicks):.2f}" if total_clicks > 0 else '0',
                'roas': f"{(total_revenue / total_spend):.2f}" if total_spend > 0 else '0'
            }
            
            logger.info(f"[GA4 Analytics] Successfully fetched GA4 data: {ecommerce_summary}")
            
            return {
                'ecommerce': ecommerce_summary,
                'traffic_sources': traffic_sources,
                'ads_performance': ads_performance
            }
            
        except Exception as error:
            logger.error(f"[GA4 Analytics] Error calling GA4 API: {error}")
            return {
                'ecommerce': {
                    'revenue': '0', 
                    'transactions': 0, 
                    'aov': '0', 
                    'conversion_rate': '0%', 
                    'users': '0'
                },
                'traffic_sources': [],
                'ads_performance': {
                    'total_spend': '0', 
                    'total_clicks': 0, 
                    'cpc': '0', 
                    'roas': '0'
                }
            }
    
    async def get_dashboard_analytics(
        self,
        db: AsyncSession,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get complete dashboard analytics data"""
        
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise Exception(f"User {user_id} not found")
        
        # Set default date range if not provided
        if not start_date or not end_date:
            yesterday = datetime.now()
            yesterday = yesterday.replace(day=yesterday.day - 1)
            start_date = end_date = yesterday.strftime('%Y-%m-%d')
        
        logger.info(f"[Dashboard Analytics] Fetching data for {start_date} to {end_date}")
        
        # Fetch all data concurrently
        shopify_task = asyncio.create_task(
            self.get_shopify_analytics(start_date, end_date, user_id)
        )
        ga4_task = asyncio.create_task(
            self.get_ga4_analytics(start_date, end_date, user)
        )
        tasks_task = asyncio.create_task(
            self.get_google_tasks(user)
        )
        emails_task = asyncio.create_task(
            self.get_recent_emails(user, 10)
        )
        calendar_task = asyncio.create_task(
            self.get_upcoming_calendar(user, 10)
        )
        
        # Wait for all tasks to complete
        shopify_data, ga4_data, tasks_data, emails_data, calendar_data = await asyncio.gather(
            shopify_task,
            ga4_task,
            tasks_task,
            emails_task,
            calendar_task,
            return_exceptions=True
        )
        
        # Handle any exceptions
        if isinstance(shopify_data, Exception):
            logger.error(f"Shopify data fetch failed: {shopify_data}")
            shopify_data = {'total_revenue': '0', 'order_count': 0, 'average_order_value': '0', 'top_products': []}
        
        if isinstance(ga4_data, Exception):
            logger.error(f"GA4 data fetch failed: {ga4_data}")
            ga4_data = {
                'ecommerce': {'revenue': '0', 'transactions': 0, 'aov': '0', 'conversion_rate': '0%', 'users': '0'},
                'traffic_sources': [],
                'ads_performance': {'total_spend': '0', 'total_clicks': 0, 'cpc': '0', 'roas': '0'}
            }
        
        if isinstance(tasks_data, Exception):
            logger.error(f"Tasks data fetch failed: {tasks_data}")
            tasks_data = {'tasks': [], 'error': str(tasks_data)}
        
        if isinstance(emails_data, Exception):
            logger.error(f"Emails data fetch failed: {emails_data}")
            emails_data = {'emails': [], 'error': str(emails_data)}
        
        if isinstance(calendar_data, Exception):
            logger.error(f"Calendar data fetch failed: {calendar_data}")
            calendar_data = {'events': [], 'error': str(calendar_data)}
        
        # Calculate insights
        insights = self._calculate_insights(shopify_data, ga4_data)
        
        # Compile response
        return {
            'date': start_date,
            'endDate': end_date,
            'dateRange': start_date if start_date == end_date else f"{start_date} to {end_date}",
            'lastUpdated': datetime.utcnow().isoformat(),
            'shopify': {
                'revenue': shopify_data.get('total_revenue', '0'),
                'orders': shopify_data.get('order_count', 0),
                'aov': shopify_data.get('average_order_value', '0'),
                'top_products': shopify_data.get('top_products', [])
            },
            'ga4': {
                'revenue': ga4_data['ecommerce'].get('revenue', '0'),
                'users': ga4_data['ecommerce'].get('users', '0'),
                'transactions': ga4_data['ecommerce'].get('transactions', 0),
                'conversion_rate': ga4_data['ecommerce'].get('conversion_rate', '0%'),
                'roas': ga4_data['ads_performance'].get('roas', '0'),
                'ad_spend': ga4_data['ads_performance'].get('total_spend', '0'),
                'traffic_sources': ga4_data.get('traffic_sources', [])
            },
            'workspace': {
                'tasks': {
                    'items': tasks_data.get('tasks', []),
                    'error': tasks_data.get('error'),
                    'count': len(tasks_data.get('tasks', []))
                },
                'emails': {
                    'items': emails_data.get('emails', []),
                    'error': emails_data.get('error'),
                    'count': len(emails_data.get('emails', []))
                },
                'calendar': {
                    'items': calendar_data.get('events', []),
                    'error': calendar_data.get('error'),
                    'count': len(calendar_data.get('events', []))
                }
            },
            'insights': insights,
            'raw_data': {
                'shopify': shopify_data,
                'ga4': ga4_data,
                'workspace': {
                    'tasks': tasks_data,
                    'emails': emails_data,
                    'calendar': calendar_data
                }
            }
        }
    
    async def get_dashboard_summary(
        self,
        db: AsyncSession,
        user_id: int,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Provide a conversational summary of analytics data"""
        
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise Exception(f"User {user_id} not found")
        
        # Use provided date or default to yesterday
        if not date:
            yesterday = datetime.now()
            yesterday = yesterday.replace(day=yesterday.day - 1)
            date = yesterday.strftime('%Y-%m-%d')
        
        logger.info(f"[Dashboard Summary] Generating conversational summary for {date}")
        
        # Fetch the same data as the dashboard using direct tool calls
        shopify_data = await self.get_shopify_analytics(date, date, user_id)
        ga4_data = await self.get_ga4_analytics(date, date, user)
        
        # Create a conversational summary
        return {
            'date': date,
            'performance_overview': f"On {date}, the store generated ${shopify_data.get('total_revenue', '0')} in revenue from {shopify_data.get('order_count', 0)} orders, with an average order value of ${shopify_data.get('average_order_value', '0')}.",
            
            'shopify_highlights': {
                'revenue': shopify_data.get('total_revenue', '0'),
                'orders': shopify_data.get('order_count', 0),
                'aov': shopify_data.get('average_order_value', '0'),
                'top_product': (
                    f"{shopify_data['top_products'][0]['name']} was the top seller with {shopify_data['top_products'][0]['quantity_sold']} units sold for ${shopify_data['top_products'][0]['revenue']} in revenue."
                    if shopify_data.get('top_products') else 'No top product data available.'
                )
            },
            
            'ga4_highlights': {
                'users': ga4_data['ecommerce'].get('users', 'N/A'),
                'conversion_rate': ga4_data['ecommerce'].get('conversion_rate', '0%'),
                'ad_performance': f"Google Ads spent ${ga4_data['ads_performance'].get('total_spend', '0')} with a {ga4_data['ads_performance'].get('roas', '0')}x return on ad spend.",
                'top_traffic_source': (
                    f"{ga4_data['traffic_sources'][0]['source']} was the top traffic source with {ga4_data['traffic_sources'][0]['users']} users generating ${ga4_data['traffic_sources'][0]['revenue']} in revenue."
                    if ga4_data.get('traffic_sources') else 'No traffic source data available.'
                )
            },
            
            'key_insights': [
                insight for insight in [
                    f"Revenue comparison: Shopify reports ${shopify_data.get('total_revenue', '0')} while GA4 shows ${ga4_data['ecommerce'].get('revenue', '0')}",
                    f"Advertising efficiency: {ga4_data['ads_performance'].get('roas', '0')}x ROAS on ${ga4_data['ads_performance'].get('total_spend', '0')} ad spend",
                    (
                        f"Best performer: {shopify_data['top_products'][0]['name']} with ${shopify_data['top_products'][0]['revenue']} revenue"
                        if shopify_data.get('top_products') else None
                    )
                ] if insight is not None
            ],
            
            'formatted_summary': self._generate_formatted_summary(date, shopify_data, ga4_data),
            
            'raw_data': {
                'shopify': shopify_data,
                'ga4': ga4_data
            }
        }
    
    def _calculate_insights(self, shopify_data: Dict, ga4_data: Dict) -> List[str]:
        """Calculate business insights from the data"""
        insights = []
        
        # Revenue comparison
        shopify_revenue = float(str(shopify_data.get('total_revenue', '0')).replace(',', '').replace('$', '') or '0')
        ga4_revenue = float(str(ga4_data['ecommerce'].get('revenue', '0')).replace(',', '').replace('$', '') or '0')
        revenue_diff = abs(shopify_revenue - ga4_revenue)
        revenue_discrepancy = (revenue_diff / shopify_revenue * 100) if shopify_revenue > 0 else 0
        
        if revenue_discrepancy > 5:
            insights.append(f"Revenue discrepancy detected: Shopify reports ${shopify_data.get('total_revenue', '0')} while GA4 shows ${ga4_data['ecommerce'].get('revenue', '0')} ({revenue_discrepancy:.1f}% difference)")
        else:
            insights.append(f"Revenue data is aligned between Shopify (${shopify_data.get('total_revenue', '0')}) and GA4 (${ga4_data['ecommerce'].get('revenue', '0')})")
        
        # Performance insights
        if shopify_data.get('top_products'):
            top_product = shopify_data['top_products'][0]
            insights.append(f"Top performing product: {top_product['name']} generated ${top_product['revenue']} from {top_product['quantity_sold']} units sold")
        
        # ROAS insight
        roas = float(ga4_data['ads_performance'].get('roas', '0') or '0')
        if roas > 3:
            insights.append(f"Excellent advertising performance with {roas}x ROAS on ${ga4_data['ads_performance'].get('total_spend', '0')} ad spend")
        elif roas > 2:
            insights.append(f"Good advertising performance with {roas}x ROAS, consider optimizing high-performing campaigns")
        elif roas > 0:
            insights.append(f"Ad performance needs attention - {roas}x ROAS on ${ga4_data['ads_performance'].get('total_spend', '0')} spend suggests optimization needed")
        
        return insights
    
    def _generate_formatted_summary(self, date: str, shopify_data: Dict, ga4_data: Dict) -> str:
        """Generate a formatted markdown summary"""
        top_product_line = ""
        if shopify_data.get('top_products'):
            top_product = shopify_data['top_products'][0]
            top_product_line = f"- Top Product: {top_product['name']} (${top_product['revenue']})"
        
        top_traffic_line = ""
        if ga4_data.get('traffic_sources'):
            top_traffic = ga4_data['traffic_sources'][0]
            top_traffic_line = f"- Top Traffic Source: {top_traffic['source']} ({top_traffic['users']} users)"
        
        revenue_alignment = ""
        shopify_revenue = float(str(shopify_data.get('total_revenue', '0')).replace(',', '').replace('$', '') or '0')
        ga4_revenue = float(str(ga4_data['ecommerce'].get('revenue', '0')).replace(',', '').replace('$', '') or '0')
        
        if shopify_revenue > 0 and ga4_revenue > 0:
            diff = abs(shopify_revenue - ga4_revenue)
            is_aligned = diff < 100
            revenue_alignment = f"- Revenue tracking is {'aligned' if is_aligned else 'showing discrepancies'} between platforms"
        else:
            revenue_alignment = "- Revenue comparison requires both platforms to be reporting"
        
        roas = float(ga4_data['ads_performance'].get('roas', '0') or '0')
        ad_performance = f"- Advertising performance {'is strong with good ROAS' if roas > 2 else 'may need optimization'}"
        
        product_insight = ""
        if shopify_data.get('top_products'):
            product_insight = f"- {shopify_data['top_products'][0]['name']} is driving significant revenue"
        
        return f"""**Daily Performance Summary for {date}**

**Shopify Performance:**
- Revenue: ${shopify_data.get('total_revenue', '0')}
- Orders: {shopify_data.get('order_count', 0)}
- Average Order Value: ${shopify_data.get('average_order_value', '0')}
{top_product_line}

**Google Analytics Performance:**
- Active Users: {ga4_data['ecommerce'].get('users', 'N/A')}
- Conversion Rate: {ga4_data['ecommerce'].get('conversion_rate', '0%')}
- Ad Spend: ${ga4_data['ads_performance'].get('total_spend', '0')}
- ROAS: {ga4_data['ads_performance'].get('roas', '0')}x
{top_traffic_line}

**Key Insights:**
{revenue_alignment}
{ad_performance}
{product_insight}"""


# Global service instance
_analytics_service: Optional[DashboardAnalyticsService] = None

def get_dashboard_analytics_service() -> DashboardAnalyticsService:
    """Get or create the global dashboard analytics service"""
    global _analytics_service
    
    if _analytics_service is None:
        _analytics_service = DashboardAnalyticsService()
    
    return _analytics_service