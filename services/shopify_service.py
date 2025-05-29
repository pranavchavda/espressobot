"""
Shopify service implementation for the Flask-ShopifyBot.

This service provides direct access to Shopify API functionality without
the overhead of separate MCP server processes.
"""
import os
import json
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ShopifyService:
    """
    Service for interacting with Shopify APIs.
    """
    def __init__(self):
        """Initialize the Shopify service with API credentials."""
        self.shop_url = os.getenv("SHOPIFY_SHOP_URL")
        self.admin_api_access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")  # Changed to match .env file
        self.storefront_access_token = os.getenv("SHOPIFY_STOREFRONT_ACCESS_TOKEN", "")
        self.api_version = os.getenv("SHOPIFY_API_VERSION", "2023-10")
        
        # Validate required environment variables
        if not self.shop_url or not self.admin_api_access_token:
            raise ValueError("Missing required Shopify environment variables")
        
        # Ensure shop URL is properly formatted
        if not self.shop_url.startswith(("http://", "https://")):
            self.shop_url = f"https://{self.shop_url}"
        
        # Remove trailing slash if present
        self.shop_url = self.shop_url.rstrip("/")
        
        # Admin API GraphQL endpoint
        self.admin_api_url = f"{self.shop_url}/admin/api/{self.api_version}/graphql.json"
        
        # Storefront API GraphQL endpoint
        self.storefront_api_url = f"{self.shop_url}/api/{self.api_version}/graphql.json"
    
    async def query_admin_api(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Shopify Admin API.
        
        Args:
            query: GraphQL query string
            variables: Variables for the GraphQL query
            
        Returns:
            API response data
        """
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.admin_api_access_token
        }
        
        payload = {
            "query": query
        }
        
        if variables:
            payload["variables"] = variables
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.admin_api_url,
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
    
    async def query_storefront_api(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Shopify Storefront API.
        
        Args:
            query: GraphQL query string
            variables: Variables for the GraphQL query
            
        Returns:
            API response data
        """
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Storefront-Access-Token": self.storefront_access_token
        }
        
        payload = {
            "query": query
        }
        
        if variables:
            payload["variables"] = variables
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.storefront_api_url,
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
    
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
    
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get a specific product by ID from the Shopify store.
        
        Args:
            product_id: The ID of the product to retrieve
            
        Returns:
            Product details
        """
        # Convert numeric ID to gid format if needed
        if product_id.isdigit():
            gid = f"gid://shopify/Product/{product_id}"
        else:
            gid = product_id
            
        # GraphQL query for a single product
        query = """
        query GetProduct($id: ID!) {
          product(id: $id) {
            id
            title
            handle
            description
            descriptionHtml
            productType
            vendor
            status
            totalInventory
            tags
            createdAt
            updatedAt
            publishedAt
            onlineStoreUrl
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
            images(first: 10) {
              edges {
                node {
                  id
                  url
                  altText
                  width
                  height
                }
              }
            }
            variants(first: 50) {
              edges {
                node {
                  id
                  title
                  price
                  compareAtPrice
                  sku
                  inventoryQuantity
                  selectedOptions {
                    name
                    value
                  }
                  image {
                    url
                  }
                }
              }
            }
            options {
              id
              name
              values
            }
            metafields(first: 20) {
              edges {
                node {
                  id
                  namespace
                  key
                  value
                  type
                }
              }
            }
          }
        }
        """
        
        # Variables for the query
        variables = {
            "id": gid
        }
        
        try:
            # Execute query
            result = await self.query_admin_api(query, variables)
            
            # Check for errors
            if "errors" in result:
                error_message = result["errors"][0]["message"]
                raise Exception(f"Shopify API error: {error_message}")
                
            # Return the product data
            return result["data"]["product"]
        except Exception as e:
            print(f"Error in get_product: {str(e)}")
            raise
    
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
