"""
GA4 Analytics Agent using direct Google Analytics Data API HTTP requests
Handles Google Analytics 4 data retrieval and analysis with OAuth authentication
"""
from typing import List, Dict, Any, Optional, Union
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
import logging
import os
import asyncio
from datetime import datetime, timedelta
import json
import aiohttp
import asyncpg
import aiosqlite

logger = logging.getLogger(__name__)

# Import the model manager
from app.config.agent_model_manager import agent_model_manager

# Import context mixin for A2A context handling
from app.agents.base_context_mixin import ContextAwareMixin


async def get_user_ga4_credentials(user_id: int) -> tuple[Optional[str], Optional[str]]:
    """Get Google access token and GA4 property ID for the user from database"""
    try:
        # Get database URL and connect appropriately
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./espressobot.db")
        
        if database_url.startswith("sqlite"):
            # SQLite using aiosqlite
            db_path = database_url.replace("sqlite+aiosqlite:///", "")
            async with aiosqlite.connect(db_path) as conn:
                cursor = await conn.execute(
                    "SELECT google_access_token, google_refresh_token, google_token_expiry, ga4_property_id FROM users WHERE id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                if not row or not row[0]:
                    return None, None
                
                # Use user-specific GA4 property ID or fallback to environment
                property_id = row[3] or os.getenv("GA4_PROPERTY_ID")
                if not property_id:
                    return None, None
                
                access_token = row[0]
                refresh_token = row[1]
                token_expiry = row[2]
                
                # Check if token is expired and refresh if needed
                if token_expiry:
                    expiry_date = datetime.fromisoformat(token_expiry) if isinstance(token_expiry, str) else token_expiry
                    if expiry_date < datetime.now():
                        # Refresh token using HTTP request
                        access_token = await refresh_access_token(refresh_token, user_id, conn)
                        if not access_token:
                            return None, None
                
                return access_token, property_id
        
        else:
            # PostgreSQL using asyncpg
            if database_url.startswith("postgresql+asyncpg://"):
                database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            
            conn = await asyncpg.connect(database_url)
            try:
                row = await conn.fetchrow(
                    "SELECT google_access_token, google_refresh_token, google_token_expiry, ga4_property_id FROM users WHERE id = $1",
                    user_id
                )
                if not row or not row[0]:
                    return None, None
                
                # Use user-specific GA4 property ID or fallback to environment
                property_id = row[3] or os.getenv("GA4_PROPERTY_ID")
                if not property_id:
                    return None, None
                
                access_token = row[0]
                refresh_token = row[1]
                token_expiry = row[2]
                
                # Check if token is expired and refresh if needed
                if token_expiry and token_expiry < datetime.now():
                    # Refresh token using HTTP request
                    access_token = await refresh_access_token_pg(refresh_token, user_id, conn)
                    if not access_token:
                        return None, None
                
                return access_token, property_id
            finally:
                await conn.close()
                
    except Exception as e:
        logger.error(f"Failed to get GA4 credentials for user {user_id}: {e}")
        return None, None


async def refresh_access_token(refresh_token: str, user_id: int, conn) -> Optional[str]:
    """Refresh Google access token using HTTP request (SQLite)"""
    try:
        async with aiohttp.ClientSession() as session:
            data = {
                'client_id': os.getenv("GOOGLE_CLIENT_ID"),
                'client_secret': os.getenv("GOOGLE_CLIENT_SECRET"),
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            async with session.post('https://oauth2.googleapis.com/token', data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    new_access_token = result.get('access_token')
                    expires_in = result.get('expires_in', 3600)
                    
                    # Update database with new token
                    new_expiry = datetime.now() + timedelta(seconds=expires_in)
                    await conn.execute(
                        "UPDATE users SET google_access_token = ?, google_token_expiry = ? WHERE id = ?",
                        (new_access_token, new_expiry.isoformat(), user_id)
                    )
                    await conn.commit()
                    
                    logger.info(f"Refreshed access token for user {user_id}")
                    return new_access_token
                else:
                    logger.error(f"Token refresh failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return None


async def refresh_access_token_pg(refresh_token: str, user_id: int, conn) -> Optional[str]:
    """Refresh Google access token using HTTP request (PostgreSQL)"""
    try:
        async with aiohttp.ClientSession() as session:
            data = {
                'client_id': os.getenv("GOOGLE_CLIENT_ID"),
                'client_secret': os.getenv("GOOGLE_CLIENT_SECRET"),
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            async with session.post('https://oauth2.googleapis.com/token', data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    new_access_token = result.get('access_token')
                    expires_in = result.get('expires_in', 3600)
                    
                    # Update database with new token
                    new_expiry = datetime.now() + timedelta(seconds=expires_in)
                    await conn.execute(
                        "UPDATE users SET google_access_token = $1, google_token_expiry = $2 WHERE id = $3",
                        new_access_token, new_expiry, user_id
                    )
                    
                    logger.info(f"Refreshed access token for user {user_id}")
                    return new_access_token
                else:
                    logger.error(f"Token refresh failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return None

class GA4Error(Exception):
    """Custom exception for GA4 operations"""
    pass


class GA4RunReportTool(BaseTool):
    """Tool for running custom GA4 reports with specified dimensions and metrics using HTTP API"""
    name: str = "ga4_run_report"
    description: str = "Run a custom GA4 report with specified dimensions and metrics. Use this for flexible analytics queries."
    user_id: int
    
    class ArgsSchema(BaseModel):
        start_date: str = Field(description="Start date (YYYY-MM-DD or relative like '7daysAgo')")
        end_date: str = Field(description="End date (YYYY-MM-DD or relative like 'today')")
        dimensions: List[str] = Field(description="Dimension names (e.g., ['date', 'country', 'deviceCategory'])")
        metrics: List[str] = Field(description="Metric names (e.g., ['activeUsers', 'sessions', 'bounceRate'])")
        dimension_filter: Optional[Dict[str, str]] = Field(default=None, description="Optional dimension filter {'dimension': 'pagePath', 'operator': 'EXACT', 'value': '/products'}")
        order_by: Optional[str] = Field(default=None, description="Metric or dimension to order by")
        limit: int = Field(default=10, description="Maximum number of rows to return")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        """Run the tool synchronously - not supported for async operations"""
        raise NotImplementedError("Use async version")
    
    async def _arun(self, start_date: str, end_date: str, dimensions: List[str], metrics: List[str],
                   dimension_filter: Optional[Dict[str, str]] = None, order_by: Optional[str] = None, 
                   limit: int = 10) -> Dict[str, Any]:
        """Run custom GA4 report using HTTP API"""
        try:
            access_token, property_id = await get_user_ga4_credentials(self.user_id)
            if not access_token or not property_id:
                return {"error": "GA4 credentials not available"}
            
            # Build request payload
            request_data = {
                "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                "dimensions": [{"name": dim} for dim in dimensions],
                "metrics": [{"name": metric} for metric in metrics],
                "limit": limit
            }
            
            # Add dimension filter if provided
            if dimension_filter:
                request_data["dimensionFilter"] = {
                    "filter": {
                        "fieldName": dimension_filter['dimension'],
                        "stringFilter": {
                            "matchType": dimension_filter.get('operator', 'EXACT'),
                            "value": dimension_filter['value']
                        }
                    }
                }
            
            # Add ordering if provided
            if order_by:
                if order_by in metrics:
                    request_data["orderBys"] = [{"metric": {"metricName": order_by}, "desc": True}]
                else:
                    request_data["orderBys"] = [{"dimension": {"dimensionName": order_by}}]
            
            # Make HTTP request to GA4 API
            url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=request_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Process response
                        rows = []
                        for row in result.get('rows', []):
                            row_data = {
                                'dimensions': [
                                    {'name': dimensions[i], 'value': dim_value.get('value', '')}
                                    for i, dim_value in enumerate(row.get('dimensionValues', []))
                                ],
                                'metrics': [
                                    {'name': metrics[i], 'value': metric_value.get('value', '0')}
                                    for i, metric_value in enumerate(row.get('metricValues', []))
                                ]
                            }
                            rows.append(row_data)
                        
                        return {
                            'success': True,
                            'rows': rows,
                            'row_count': len(rows),
                            'date_range': f"{start_date} to {end_date}",
                            'dimensions': dimensions,
                            'metrics': metrics
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"GA4 API error {response.status}: {error_text}")
                        return {'error': f"GA4 API error: {response.status}"}
                        
        except Exception as e:
            logger.error(f"GA4 run report error: {e}")
            return {'error': f"GA4 report failed: {str(e)}"}


class GA4RealtimeTool(BaseTool):
    """Tool for getting real-time visitor data from GA4 using HTTP API"""
    name: str = "ga4_get_realtime"
    description: str = "Get real-time visitor data from GA4 including current active users and their activities."
    user_id: int
    
    class ArgsSchema(BaseModel):
        dimensions: List[str] = Field(default=['unifiedScreenName'], description="Dimensions for real-time data")
        metrics: List[str] = Field(default=['activeUsers'], description="Metrics for real-time data")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, dimensions: List[str] = None, metrics: List[str] = None) -> Dict[str, Any]:
        """Get real-time GA4 data using HTTP API"""
        try:
            dimensions = dimensions or ['unifiedScreenName']
            metrics = metrics or ['activeUsers']
            
            access_token, property_id = await get_user_ga4_credentials(self.user_id)
            if not access_token or not property_id:
                return {"error": "GA4 credentials not available"}
            
            # Build request payload
            request_data = {
                "dimensions": [{"name": dim} for dim in dimensions],
                "metrics": [{"name": metric} for metric in metrics]
            }
            
            # Make HTTP request to GA4 realtime API
            url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runRealtimeReport"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=request_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Calculate total active users
                        total_active_users = sum(
                            int(row.get('metricValues', [{}])[0].get('value', '0')) 
                            for row in result.get('rows', [])
                        )
                        
                        # Process by page/screen
                        by_page = []
                        for row in result.get('rows', []):
                            dimension_values = row.get('dimensionValues', [])
                            metric_values = row.get('metricValues', [])
                            
                            by_page.append({
                                'page': dimension_values[0].get('value', 'Unknown') if dimension_values else 'Unknown',
                                'active_users': int(metric_values[0].get('value', '0')) if metric_values else 0
                            })
                        
                        return {
                            'success': True,
                            'total_active_users': total_active_users,
                            'by_page': by_page,
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"GA4 realtime API error {response.status}: {error_text}")
                        return {'error': f"GA4 realtime API error: {response.status}"}
                        
        except Exception as e:
            logger.error(f"GA4 realtime error: {e}")
            return {'error': f"GA4 realtime data failed: {str(e)}"}


class GA4AdvertisingTool(BaseTool):
    """Tool for getting Google Ads performance metrics via GA4 using HTTP API"""
    name: str = "ga4_get_ads_performance"
    description: str = "Get Google Ads performance metrics including spend, clicks, and traffic from GA4."
    user_id: int
    
    class ArgsSchema(BaseModel):
        start_date: str = Field(description="Start date (YYYY-MM-DD or relative like 'today')")
        end_date: str = Field(description="End date (YYYY-MM-DD or relative like 'today')")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get Google Ads performance metrics using HTTP API"""
        try:
            access_token, property_id = await get_user_ga4_credentials(self.user_id)
            if not access_token or not property_id:
                return {"error": "GA4 credentials not available"}
            
            # Build request payload for advertising metrics - using sessionDefaultChannelGroup
            # to make the advertising metrics compatible (following GA4 API requirements)
            request_data = {
                "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                "dimensions": [{"name": "sessionDefaultChannelGroup"}],
                "metrics": [
                    {"name": "advertiserAdClicks"},
                    {"name": "advertiserAdCost"},
                    {"name": "advertiserAdCostPerClick"},
                    {"name": "returnOnAdSpend"},
                    {"name": "sessions"},
                    {"name": "totalRevenue"},
                    {"name": "conversions"}
                ]
            }
            
            # Make HTTP request to GA4 API
            url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=request_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Process summary data - aggregate across all channel groups
                        rows = result.get('rows', [])
                        if rows:
                            # Sum metrics across all channel groups to get total advertising performance
                            total_clicks = 0
                            total_cost = 0.0
                            total_sessions = 0
                            total_revenue = 0.0
                            total_conversions = 0
                            
                            for row in rows:
                                metrics = row.get('metricValues', [])
                                total_clicks += int(metrics[0].get('value', '0')) if len(metrics) > 0 else 0
                                total_cost += float(metrics[1].get('value', '0')) if len(metrics) > 1 else 0.0
                                total_sessions += int(metrics[4].get('value', '0')) if len(metrics) > 4 else 0
                                total_revenue += float(metrics[5].get('value', '0')) if len(metrics) > 5 else 0.0
                                total_conversions += int(metrics[6].get('value', '0')) if len(metrics) > 6 else 0
                            
                            # Calculate average CPC and ROAS
                            avg_cpc = total_cost / total_clicks if total_clicks > 0 else 0.0
                            roas = total_revenue / total_cost if total_cost > 0 else 0.0
                            
                            return {
                                'success': True,
                                'date_range': f"{start_date} to {end_date}",
                                'summary': {
                                    'clicks': total_clicks,
                                    'cost': total_cost,
                                    'cpc': avg_cpc,
                                    'roas': roas,
                                    'sessions': total_sessions,
                                    'revenue': total_revenue,
                                    'conversions': total_conversions
                                }
                            }
                        else:
                            return {
                                'success': True,
                                'date_range': f"{start_date} to {end_date}",
                                'summary': {
                                    'clicks': 0,
                                    'cost': 0.0,
                                    'cpc': 0.0,
                                    'roas': 0.0,
                                    'sessions': 0,
                                    'revenue': 0.0,
                                    'conversions': 0
                                },
                                'message': 'No Google Ads data available for the specified date range'
                            }
                    else:
                        error_text = await response.text()
                        logger.error(f"GA4 ads API error {response.status}: {error_text}")
                        return {'error': f"GA4 ads API error: {response.status}"}
                        
        except Exception as e:
            logger.error(f"GA4 ads performance error: {e}")
            return {'error': f"GA4 ads performance failed: {str(e)}"}


class GA4EcommerceTool(BaseTool):
    """Tool for getting ecommerce metrics including revenue, transactions, and conversion rate"""
    name: str = "ga4_get_ecommerce"
    description: str = "Get ecommerce performance metrics including revenue, transactions, AOV, and conversion rates."
    user_id: int
    
    class ArgsSchema(BaseModel):
        start_date: str = Field(description="Start date (YYYY-MM-DD or relative)")
        end_date: str = Field(description="End date (YYYY-MM-DD or relative)")
        group_by: Optional[str] = Field(default=None, description="Group results by dimension (date, deviceCategory, country)")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, start_date: str, end_date: str, group_by: Optional[str] = None) -> Dict[str, Any]:
        """Get ecommerce metrics from GA4"""
        try:
            client, property_id = await self._get_ga4_client()
            if not client:
                return {"error": "GA4 client not available"}
            
            dimensions = [Dimension(name=group_by)] if group_by else []
            
            request = RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimensions=dimensions,
                metrics=[
                    Metric(name='totalRevenue'),
                    Metric(name='transactions'),
                    Metric(name='ecommercePurchases'),
                    Metric(name='averagePurchaseRevenue'),
                    Metric(name='purchaseToViewRate'),
                    Metric(name='cartToViewRate')
                ]
            )
            
            response = client.run_report(request=request)
            
            # Process summary (first row or aggregate)
            summary_row = response.rows[0] if response.rows else None
            summary = {
                'revenue': float(summary_row.metric_values[0].value) if summary_row else 0.0,
                'transactions': int(summary_row.metric_values[1].value) if summary_row else 0,
                'purchases': int(summary_row.metric_values[2].value) if summary_row else 0,
                'average_order_value': float(summary_row.metric_values[3].value) if summary_row else 0.0,
                'purchase_to_view_rate': float(summary_row.metric_values[4].value) if summary_row else 0.0,
                'cart_to_view_rate': float(summary_row.metric_values[5].value) if summary_row else 0.0
            }
            
            # Process breakdown if groupBy specified
            breakdown = None
            if group_by and response.rows:
                breakdown = [
                    {
                        group_by: row.dimension_values[0].value,
                        'revenue': float(row.metric_values[0].value),
                        'transactions': int(row.metric_values[1].value)
                    }
                    for row in response.rows
                ]
            
            return {
                'success': True,
                'summary': summary,
                'breakdown': breakdown,
                'date_range': f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            logger.error(f"GA4 ecommerce error: {e}")
            return {'error': f"GA4 ecommerce data failed: {str(e)}"}
    
    async def _get_ga4_client(self):
        """Get authenticated GA4 client and property ID"""
        creds, property_id = await self._get_ga4_credentials()
        if not creds or not property_id:
            return None, None
        
        client = BetaAnalyticsDataClient(credentials=creds)
        return client, property_id
    
    async def _get_ga4_credentials(self) -> tuple[Optional['Credentials'], Optional[str]]:
        """Get Google credentials and GA4 property ID for the user from database"""
        return await get_user_ga4_credentials(self.user_id)


class GA4TrafficSourcesTool(BaseTool):
    """Tool for analyzing traffic sources and channels"""
    name: str = "ga4_get_traffic_sources"
    description: str = "Analyze traffic sources and channels to understand where visitors are coming from."
    user_id: int
    
    class ArgsSchema(BaseModel):
        start_date: str = Field(description="Start date")
        end_date: str = Field(description="End date")
        include_organic_vs_paid: bool = Field(default=True, description="Include organic vs paid breakdown")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, start_date: str, end_date: str, include_organic_vs_paid: bool = True) -> Dict[str, Any]:
        """Analyze traffic sources and channels"""
        try:
            client, property_id = await self._get_ga4_client()
            if not client:
                return {"error": "GA4 client not available"}
            
            request = RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimensions=[
                    Dimension(name='sessionDefaultChannelGroup'),
                    Dimension(name='sessionSource')
                ],
                metrics=[
                    Metric(name='sessions'),
                    Metric(name='activeUsers'),
                    Metric(name='totalRevenue'),
                    Metric(name='conversions')
                ],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name='sessions'), desc=True)],
                limit=20
            )
            
            response = client.run_report(request=request)
            
            # Process channels
            channels = {}
            for row in response.rows:
                channel = row.dimension_values[0].value
                source = row.dimension_values[1].value
                
                if channel not in channels:
                    channels[channel] = {
                        'sessions': 0,
                        'users': 0,
                        'revenue': 0.0,
                        'conversions': 0,
                        'sources': set()
                    }
                
                channels[channel]['sessions'] += int(row.metric_values[0].value)
                channels[channel]['users'] += int(row.metric_values[1].value)
                channels[channel]['revenue'] += float(row.metric_values[2].value)
                channels[channel]['conversions'] += int(row.metric_values[3].value)
                channels[channel]['sources'].add(source)
            
            # Format response
            channel_list = [
                {
                    'name': name,
                    'sessions': data['sessions'],
                    'users': data['users'],
                    'revenue': data['revenue'],
                    'conversions': data['conversions'],
                    'top_sources': list(data['sources'])[:5]
                }
                for name, data in channels.items()
            ]
            
            # Calculate organic vs paid if requested
            organic_vs_paid = None
            if include_organic_vs_paid:
                organic_channels = ['Organic Search', 'Direct', 'Organic Social']
                paid_channels = ['Paid Search', 'Paid Social', 'Display']
                
                organic_sessions = sum(
                    data['sessions'] for name, data in channels.items() 
                    if name in organic_channels
                )
                paid_sessions = sum(
                    data['sessions'] for name, data in channels.items() 
                    if name in paid_channels
                )
                
                organic_vs_paid = {
                    'organic': organic_sessions,
                    'paid': paid_sessions
                }
            
            return {
                'success': True,
                'channels': channel_list,
                'organic_vs_paid': organic_vs_paid,
                'date_range': f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            logger.error(f"GA4 traffic sources error: {e}")
            return {'error': f"GA4 traffic sources failed: {str(e)}"}
    
    async def _get_ga4_client(self):
        """Get authenticated GA4 client and property ID"""
        creds, property_id = await self._get_ga4_credentials()
        if not creds or not property_id:
            return None, None
        
        client = BetaAnalyticsDataClient(credentials=creds)
        return client, property_id
    
    async def _get_ga4_credentials(self) -> tuple[Optional['Credentials'], Optional[str]]:
        """Get Google credentials and GA4 property ID for the user from database"""
        return await get_user_ga4_credentials(self.user_id)


class GA4ProductPerformanceTool(BaseTool):
    """Tool for getting product-level analytics data"""
    name: str = "ga4_get_product_performance"
    description: str = "Get product-level analytics including best sellers, revenue by product, and conversion rates."
    user_id: int
    
    class ArgsSchema(BaseModel):
        start_date: str = Field(description="Start date")
        end_date: str = Field(description="End date")
        limit: int = Field(default=20, description="Number of products to return")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, start_date: str, end_date: str, limit: int = 20) -> Dict[str, Any]:
        """Get product performance metrics"""
        try:
            client, property_id = await self._get_ga4_client()
            if not client:
                return {"error": "GA4 client not available"}
            
            request = RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimensions=[
                    Dimension(name='itemName'),
                    Dimension(name='itemId')
                ],
                metrics=[
                    Metric(name='itemRevenue'),
                    Metric(name='itemsPurchased'),
                    Metric(name='itemsViewed'),
                    Metric(name='itemsAddedToCart'),
                    Metric(name='cartToViewRate'),
                    Metric(name='purchaseToViewRate')
                ],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name='itemRevenue'), desc=True)],
                limit=limit
            )
            
            response = client.run_report(request=request)
            
            products = [
                {
                    'name': row.dimension_values[0].value,
                    'id': row.dimension_values[1].value if len(row.dimension_values) > 1 else 'N/A',
                    'revenue': float(row.metric_values[0].value),
                    'quantity_sold': int(row.metric_values[1].value),
                    'views': int(row.metric_values[2].value),
                    'added_to_cart': int(row.metric_values[3].value),
                    'cart_to_view_rate': float(row.metric_values[4].value) if len(row.metric_values) > 4 else 0.0,
                    'purchase_to_view_rate': float(row.metric_values[5].value) if len(row.metric_values) > 5 else 0.0
                }
                for row in response.rows
            ]
            
            return {
                'success': True,
                'products': products,
                'total_products': len(products),
                'date_range': f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            logger.error(f"GA4 product performance error: {e}")
            return {'error': f"GA4 product performance failed: {str(e)}"}
    
    async def _get_ga4_client(self):
        """Get authenticated GA4 client and property ID"""
        creds, property_id = await self._get_ga4_credentials()
        if not creds or not property_id:
            return None, None
        
        client = BetaAnalyticsDataClient(credentials=creds)
        return client, property_id
    
    async def _get_ga4_credentials(self) -> tuple[Optional['Credentials'], Optional[str]]:
        """Get Google credentials and GA4 property ID for the user from database"""
        return await get_user_ga4_credentials(self.user_id)


class GA4AnalyticsAgentNativeMCP(ContextAwareMixin):
    """GA4 Analytics agent using direct Google Analytics Data API integration with stored OAuth tokens"""
    
    def __init__(self):
        self.name = "ga4_analytics"
        self.description = "Handles Google Analytics 4 data retrieval and analysis for website traffic, user behavior, conversions, and performance metrics"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")
        self.tools = None  # Will be created when user_id is available
        self.agent = None
        self.system_prompt = self._get_system_prompt()
        
    def _create_tools(self, user_id: int) -> List[BaseTool]:
        """Create GA4 tools for specific user"""
        return [
            GA4RunReportTool(user_id=user_id),
            GA4RealtimeTool(user_id=user_id),
            GA4AdvertisingTool(user_id=user_id)
        ]
        
    async def _ensure_agent_ready(self, user_id: int):
        """Ensure agent is initialized for specific user"""
        if not self.agent or not self.tools:
            try:
                # Check if user has Google credentials and GA4 property ID
                access_token, property_id = await get_user_ga4_credentials(user_id)
                if not access_token:
                    raise GA4Error("User has not authorized Google Analytics access")
                
                if not property_id:
                    raise GA4Error("GA4 property ID not configured. Please set user-specific GA4 property ID or GA4_PROPERTY_ID environment variable.")
                
                # Create tools for this user if not exists
                self.tools = self._create_tools(user_id)
                
                # Create react agent with tools
                self.agent = create_react_agent(
                    self.model,
                    self.tools,
                    prompt=self.system_prompt
                )
                
                logger.info(f"Initialized GA4 Analytics agent with {len(self.tools)} tools for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to initialize GA4 Analytics agent: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the agent"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        return f"""You are a Google Analytics 4 specialist agent with expertise in website analytics, user behavior analysis, and ecommerce performance tracking.

Today's date: {today}

You have access to the following GA4 tools using the user's authenticated Google account:

## Core GA4 Tools:
- **ga4_run_report**: Run custom reports with any combination of dimensions and metrics
  - Common dimensions: date, country, deviceCategory, city, pagePath, sessionDefaultChannelGroup
  - Common metrics: activeUsers, sessions, bounceRate, engagementRate, totalRevenue
  - Use for flexible analytics queries and custom analysis
  
- **ga4_get_realtime**: Get real-time visitor data
  - Shows current active users and their locations/activities
  - Use for immediate website activity monitoring
  
- **ga4_get_ads_performance**: Get Google Ads performance metrics
  - Advertising spend (adCost), clicks, traffic data
  - Sessions, active users, revenue from ads
  - Use for Google Ads ROI analysis

## Date Formatting Guidelines:
- Use relative dates: "today", "yesterday", "7daysAgo", "30daysAgo"
- Or specific dates: "2025-01-07", "2025-01-01"
- For ranges: start_date="30daysAgo", end_date="today"
- Be aware that today is {today}

## Common Analytics Queries:
- "What's today's traffic?" → Use ga4_get_realtime
- "Show Google Ads spend today/this week" → Use ga4_get_ads_performance
- "What's the advertising performance?" → Use ga4_get_ads_performance
- "Custom report on mobile vs desktop performance" → Use ga4_run_report with deviceCategory dimension
- "Get traffic by source" → Use ga4_run_report with sessionDefaultChannelGroup dimension

## Key Metrics Explained:
- **Active Users**: Unique users who had an engaged session
- **Sessions**: Number of sessions that began on your site or app
- **Bounce Rate**: Percentage of sessions that were not engaged
- **Engagement Rate**: Percentage of engaged sessions
- **Total Revenue**: Total purchase revenue
- **Conversions**: Total number of conversion events
- **Average Order Value**: Revenue per transaction

## Business Context:
- These analytics help iDrinkCoffee.com understand customer behavior and optimize performance
- Focus on ecommerce metrics like revenue, conversion rates, and product performance
- Traffic analysis helps with marketing attribution and channel optimization
- Real-time data is useful for monitoring campaigns and website issues

## Best Practices:
- Always specify meaningful date ranges for analysis
- Use appropriate dimensions and metrics combinations
- Format numbers clearly (e.g., revenue with currency, percentages with %)
- Provide context and insights, not just raw numbers
- Suggest actionable recommendations when possible
- Handle missing or zero data gracefully
- Explain what metrics mean in business terms

## Response Guidelines:
- Always include the date range in your response
- Format large numbers with commas (e.g., 1,234)
- Show percentages with one decimal place (e.g., 12.3%)
- Highlight key insights and trends
- Compare periods when relevant (e.g., vs. last week/month)
- Provide context for unusual patterns or anomalies

## Error Handling:
- If GA4 property ID is not configured, explain the setup requirement
- If no data is available, explain possible reasons (tracking issues, date range, etc.)
- If authentication fails, guide user to re-authorize Google access
- Always provide helpful troubleshooting information

Always provide clear, formatted responses with relevant analytics insights and actionable business recommendations."""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        logger.info(f"📊 GA4 AGENT CALLED with state keys: {state.keys()}")
        logger.info(f"📊 GA4 AGENT: last_agent={state.get('last_agent')}, current_agent={state.get('current_agent')}")
        try:
            # Extract user_id from state
            user_id = state.get("user_id")
            if not user_id:
                state["messages"].append(AIMessage(
                    content="GA4 Analytics agent requires user authentication. Please provide user context.",
                    metadata={"agent": self.name, "intermediate": True, "error": True}
                ))
                return state
            
            # Convert user_id to int if it's a string
            if isinstance(user_id, str):
                user_id = int(user_id)
            
            await self._ensure_agent_ready(user_id)
            
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            # Get last user message
            last_message = messages[-1]
            if not isinstance(last_message, HumanMessage):
                return state
            
            # Use context-aware messages from the mixin
            context_aware_messages = self.build_context_aware_messages(state, self.system_prompt)
            
            # Use the agent to process the request with context
            agent_state = {"messages": context_aware_messages}
            
            # Run the agent
            logger.info(f"🚀 Running GA4 Analytics agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ GA4 Analytics agent completed")
            
            # Extract the response
            if result.get("messages"):
                # Get the last AI message from the agent's response
                agent_messages = result["messages"]
                for msg in reversed(agent_messages):
                    if hasattr(msg, 'content') and msg.content:
                        state["messages"].append(AIMessage(
                            content=msg.content,
                            metadata={"agent": self.name, "intermediate": True}
                        ))
                        break
            else:
                state["messages"].append(AIMessage(
                    content="I processed your request but couldn't generate a response.",
                    metadata={"agent": self.name, "intermediate": True}
                ))
            
            state["last_agent"] = self.name
            return state
            
        except GA4Error as e:
            logger.error(f"GA4 Analytics authentication error: {e}")
            state["messages"].append(AIMessage(
                content=f"GA4 Analytics access error: {str(e)}. Please ensure you have authorized Google Analytics access and configured your GA4 property ID.",
                metadata={"agent": self.name, "intermediate": True, "error": True}
            ))
            return state
        except Exception as e:
            logger.error(f"Error in GA4AnalyticsAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in GA4 Analytics agent: {str(e)}",
                metadata={"agent": self.name, "intermediate": True, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        # Keywords related to GA4 and analytics
        keywords = [
            "analytics", "ga4", "google analytics", "traffic", "visitors", "users",
            "pageviews", "sessions", "bounce rate", "conversion", "revenue",
            "ecommerce", "sales performance", "website performance", "realtime",
            "real-time", "active users", "channel", "source", "campaign",
            "product performance", "best sellers", "top pages", "engagement",
            "demographics", "devices", "mobile", "desktop", "location", "country"
        ]
        
        message_content = last_message.content.lower()
        return any(keyword in message_content for keyword in keywords)
    
    async def cleanup(self):
        """Clean up resources"""
        # No persistent connections to clean up for direct API calls
        pass