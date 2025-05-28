"""
Shopify service implementation for Shopify Admin API interactions.
Replaces the ShopifyMCPServer with a direct implementation.
"""
import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
import logging
import httpx

from services.base_service import BaseService, ServiceError
from services.config import service_config

class ShopifyServiceError(ServiceError):
    """Exception raised for Shopify service errors."""
    pass

class ShopifyService(BaseService):
    """
    Direct implementation of Shopify service functionality.
    Provides Shopify Admin API interactions without MCP overhead.
    """
    def __init__(self):
        """Initialize the Shopify service."""
        super().__init__("shopify")
        
        # Get API credentials from config
        self.api_key = service_config.get("shopify", "api_key", os.environ.get("SHOPIFY_API_KEY", ""))
        self.api_secret = service_config.get("shopify", "api_secret", os.environ.get("SHOPIFY_API_SECRET", ""))
        self.shop_url = service_config.get("shopify", "shop_url", os.environ.get("SHOPIFY_SHOP_URL", ""))
        self.access_token = service_config.get("shopify", "access_token", os.environ.get("SHOPIFY_ACCESS_TOKEN", ""))
        
        # API version
        self.api_version = service_config.get("shopify", "api_version", "2023-10")
        
        # Validate configuration
        if not self.shop_url or not self.access_token:
            self.logger.warning("Shopify service initialized without required credentials")
    
    def _get_api_url(self, endpoint: str) -> str:
        """
        Get the full API URL for a given endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Full API URL
        """
        # Ensure shop URL doesn't have protocol
        shop_domain = self.shop_url.replace("https://", "").replace("http://", "")
        
        # Construct API URL
        return f"https://{shop_domain}/admin/api/{self.api_version}/{endpoint}"
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get the headers for Shopify API requests.
        
        Returns:
            Headers dictionary
        """
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def query_admin_api(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Shopify Admin API.
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Query results
        """
        try:
            # Validate credentials
            if not self.shop_url or not self.access_token:
                raise ShopifyServiceError("Missing Shopify API credentials")
            
            # Prepare request
            url = self._get_api_url("graphql.json")
            headers = self._get_headers()
            payload = {
                "query": query,
                "variables": variables or {}
            }
            
            # Execute request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                # Raise for HTTP errors
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    error_messages = [error.get("message", "Unknown error") for error in data["errors"]]
                    raise ShopifyServiceError(f"GraphQL errors: {', '.join(error_messages)}")
                
                return {
                    "success": True,
                    "data": data.get("data", {})
                }
        except Exception as e:
            raise ShopifyServiceError(f"Failed to query Shopify Admin API: {str(e)}")
    
    async def get_products(self, limit: int = 10, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Get products from the Shopify store.
        
        Args:
            limit: Maximum number of products to return
            cursor: Pagination cursor
            
        Returns:
            List of products and pagination info
        """
        # GraphQL query for products
        query = """
        query GetProducts($limit: Int!, $cursor: String) {
          products(first: $limit, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                handle
                description
                descriptionHtml
                productType
                vendor
                status
                totalInventory
                priceRangeV2 {
                  minVariantPrice {
                    amount
                    currencyCode
                  }
                  maxVariantPrice {
                    amount
                    currencyCode
                  }
                }
                images(first: 1) {
                  edges {
                    node {
                      url
                      altText
                    }
                  }
                }
                variants(first: 5) {
                  edges {
                    node {
                      id
                      title
                      price
                      sku
                      inventoryQuantity
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        # Variables for the query
        variables = {
            "limit": limit
        }
        
        if cursor:
            variables["cursor"] = cursor
        
        # Execute query
        return await self.query_admin_api(query, variables)
    
    async def get_orders(self, limit: int = 10, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Get orders from the Shopify store.
        
        Args:
            limit: Maximum number of orders to return
            cursor: Pagination cursor
            
        Returns:
            List of orders and pagination info
        """
        # GraphQL query for orders
        query = """
        query GetOrders($limit: Int!, $cursor: String) {
          orders(first: $limit, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                name
                email
                phone
                totalPrice
                subtotalPrice
                totalTax
                processedAt
                fulfillmentStatus
                financialStatus
                customer {
                  id
                  email
                  firstName
                  lastName
                }
                lineItems(first: 10) {
                  edges {
                    node {
                      title
                      quantity
                      originalTotalPrice
                      variant {
                        id
                        title
                        sku
                        price
                      }
                    }
                  }
                }
                shippingAddress {
                  address1
                  address2
                  city
                  province
                  country
                  zip
                }
              }
            }
          }
        }
        """
        
        # Variables for the query
        variables = {
            "limit": limit
        }
        
        if cursor:
            variables["cursor"] = cursor
        
        # Execute query
        return await self.query_admin_api(query, variables)
    
    async def search_products(self, query_text: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for products in the Shopify store.
        
        Args:
            query_text: Search query
            limit: Maximum number of products to return
            
        Returns:
            List of matching products
        """
        # GraphQL query for product search
        query = """
        query SearchProducts($query: String!, $limit: Int!) {
          products(first: $limit, query: $query) {
            edges {
              node {
                id
                title
                handle
                description
                productType
                vendor
                totalInventory
                priceRangeV2 {
                  minVariantPrice {
                    amount
                    currencyCode
                  }
                }
                images(first: 1) {
                  edges {
                    node {
                      url
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        # Variables for the query
        variables = {
            "query": query_text,
            "limit": limit
        }
        
        # Execute query
        return await self.query_admin_api(query, variables)

# Create a singleton instance
shopify_service = ShopifyService()
