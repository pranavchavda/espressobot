"""
Module for handling MCP server connections for Shopify Dev MCP
"""
import os
import asyncio
import json
import httpx
import subprocess
from typing import Dict, Any, List, Optional

class ShopifyMCPServer:
    """
    A class to handle communication with a local Shopify Dev MCP server instance.
    This spawns an npx process running @shopify/dev-mcp to provide schema information
    and documentation search capabilities.
    """
    def __init__(self):
        self.process = None
        self.server_url = None
        self.running = False
    
    async def start(self):
        """Start the Shopify Dev MCP server process"""
        if self.running and self.process and self.process.poll() is None:
            print("MCP server is already running")
            return True
        
        # If we get here, either server isn't running or the process died
        if self.process and self.process.poll() is not None:
            print("MCP server process terminated unexpectedly, restarting...")
            self.process = None
            self.running = False
        
        try:
            # Check if npx is installed
            try:
                subprocess.run(["npx", "--version"], check=True, capture_output=True)
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                print(f"ERROR: npx is not installed. Install Node.js and npm first. {str(e)}")
                self.running = False
                return False
            
            # For debug purposes, check if npm is installed properly
            try:
                npm_version = subprocess.run(["npm", "--version"], check=True, capture_output=True, text=True)
                print(f"npm version: {npm_version.stdout.strip()}")
                node_version = subprocess.run(["node", "--version"], check=True, capture_output=True, text=True)
                print(f"node version: {node_version.stdout.strip()}")
            except Exception as e:
                print(f"Warning: Could not determine npm/node version: {str(e)}")
            
            # Try a simpler command first to see if npx works properly
            try:
                print("Testing npx functionality...")
                test_result = subprocess.run(["npx", "--no-install", "--yes", "--quiet", "cowsay", "Hello"], 
                                          check=False, capture_output=True, text=True, timeout=10)
                print(f"Test npx result code: {test_result.returncode}")
            except Exception as e:
                print(f"Warning: Test npx command failed: {str(e)}")
            
            # Start the server process with more verbose output
            print("Starting Shopify Dev MCP server...")
            # Use shell=True on Windows to ensure proper path resolution
            use_shell = os.name == 'nt'
            
            self.process = subprocess.Popen(
                ["npx", "--yes", "@shopify/dev-mcp@latest"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                shell=use_shell
            )
            
            # Wait for server to initialize
            self.running = True
            print("Waiting for Shopify Dev MCP server to initialize...")
            
            # Give the server time to start, check if it's still running
            await asyncio.sleep(2)
            if self.process.poll() is not None:
                stderr_output = self.process.stderr.read() if self.process.stderr else "No stderr output"
                stdout_output = self.process.stdout.read() if self.process.stdout else "No stdout output"
                print(f"ERROR: MCP server process exited unexpectedly with code {self.process.returncode}")
                print(f"STDERR: {stderr_output}")
                print(f"STDOUT: {stdout_output}")
                self.running = False
                return False
            
            # Wait more time for the server to fully initialize
            await asyncio.sleep(3)
            
            # For now, assume server is running on default port
            self.server_url = "http://localhost:3000"
            print(f"Shopify Dev MCP server is running at {self.server_url}")
            
            # Check if server is actually responding
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    print(f"Testing connection to MCP server at {self.server_url}...")
                    response = await client.get(f"{self.server_url}/health")
                    if response.status_code == 200:
                        print("Successfully connected to MCP server!")
                        return True
                    else:
                        print(f"Warning: MCP server health check returned status {response.status_code}")
                        # Continue anyway, maybe endpoint doesn't exist
                        return True
            except Exception as e:
                print(f"Warning: Could not verify MCP server is responding: {str(e)}")
                # Continue anyway, let the actual requests fail if needed
                return True
        except Exception as e:
            print(f"Error starting Shopify Dev MCP server: {str(e)}")
            self.stop()
            return False
    
    async def introspect_admin_schema(self, query, filter_types=None):
        """Query the Shopify Admin API schema using the MCP server"""
        if not self.running:
            server_started = await self.start()
            if not server_started:
                print("Failed to start MCP server for schema introspection")
                return {
                    "errors": [{"message": "Failed to start MCP server"}],
                    "mock_data": {
                        "schema": f"Schema information for '{query}' would appear here if MCP server was running",
                        "note": "This is mock data since the MCP server couldn't be started."
                    }
                }
        
        if filter_types is None:
            filter_types = ["all"]
        
        # Since we don't have direct access to the real Shopify Dev MCP, we'll return mocked data
        # In a real implementation, this would make an API call to the MCP server
        print(f"Using mock schema introspection for {query} due to API limitations")
        
        # Create a mock response with relevant fields for common types
        mock_data = {}
        
        if query.lower() == "product":
            mock_data = {
                "type": "Product",
                "fields": [
                    {"name": "id", "type": "ID!", "description": "The unique ID of the product"},
                    {"name": "title", "type": "String!", "description": "The title of the product"},
                    {"name": "description", "type": "String", "description": "The description of the product"},
                    {"name": "handle", "type": "String!", "description": "The handle of the product"},
                    {"name": "variants", "type": "[ProductVariant!]!", "description": "List of product variants"},
                    {"name": "images", "type": "[Image!]!", "description": "List of product images"},
                    {"name": "collections", "type": "[Collection!]!", "description": "The collections this product belongs to"},
                    {"name": "options", "type": "[ProductOption!]!", "description": "The product options"}
                ]
            }
        elif query.lower() == "order":
            mock_data = {
                "type": "Order",
                "fields": [
                    {"name": "id", "type": "ID!", "description": "The unique ID of the order"},
                    {"name": "name", "type": "String!", "description": "The name of the order, usually a number"},
                    {"name": "customer", "type": "Customer", "description": "The customer who placed the order"},
                    {"name": "lineItems", "type": "[LineItem!]!", "description": "The line items in the order"},
                    {"name": "totalPrice", "type": "Money!", "description": "The total price of the order"},
                    {"name": "processedAt", "type": "DateTime", "description": "The date and time when the order was processed"}
                ]
            }
        else:
            # For other types, return a generic message
            mock_data = {
                "type": query,
                "note": f"This is mock schema data for {query}. In a real implementation, this would come from the Shopify API.",
                "availableTypes": ["Product", "Order", "Customer", "Collection", "Metafield"]
            }
        
        return {
            "schema": mock_data,
            "note": "This is mock data. In a real implementation with proper API access, this would return the actual schema from Shopify."
        }
    
    async def search_dev_docs(self, prompt):
        """Search Shopify developer documentation using the MCP server"""
        if not self.running:
            server_started = await self.start()
            if not server_started:
                print("Failed to start MCP server for documentation search")
                return {
                    "errors": [{"message": "Failed to start MCP server"}],
                    "mock_data": {
                        "docs": f"Documentation search results for '{prompt}' would appear here if MCP server was running",
                        "note": "This is mock data since the MCP server couldn't be started."
                    }
                }
        
        # Since we don't have direct access to the real Shopify Dev MCP, we'll return mocked data
        # In a real implementation, this would make an API call to the MCP server
        print(f"Using mock documentation search for '{prompt}' due to API limitations")
        
        # Create mock documentation based on common Shopify topics
        mock_docs = []
        
        # Check for common topics and provide relevant mock documentation
        prompt_lower = prompt.lower()
        
        if "product" in prompt_lower:
            mock_docs.append({
                "title": "Shopify Product API",
                "url": "https://shopify.dev/api/admin-graphql/current/objects/Product",
                "excerpt": "Products are at the core of Shopify. Learn how to manage products using the Admin API.",
                "content": "The Product object represents a product in a shop's catalog. Products can have multiple options and variants. Products have many fields including: id, title, description, handle, productType, vendor, and more."
            })
        
        if "order" in prompt_lower:
            mock_docs.append({
                "title": "Shopify Order API",
                "url": "https://shopify.dev/api/admin-graphql/current/objects/Order",
                "excerpt": "Orders represent a customer's purchase of goods or services from a shop.",
                "content": "The Order object contains information about a customer's order, including line items, fulfillments, shipping address, and more. You can use the Order API to retrieve, create, and modify orders."
            })
        
        if "metafield" in prompt_lower:
            mock_docs.append({
                "title": "Working with Metafields",
                "url": "https://shopify.dev/api/admin-graphql/current/objects/Metafield",
                "excerpt": "Metafields let you store additional information about Shopify resources.",
                "content": "Metafields are extra pieces of data that apps can attach to Shopify resources, such as products, customers, and orders. They allow you to customize Shopify by storing information that wouldn't otherwise exist in the platform."
            })
        
        if "discount" in prompt_lower or "coupon" in prompt_lower:
            mock_docs.append({
                "title": "Shopify Discounts API",
                "url": "https://shopify.dev/api/admin-graphql/current/objects/DiscountCodeNode",
                "excerpt": "Learn how to create and manage discounts and price rules.",
                "content": "Discounts in Shopify can be automatically applied or require a code that customers enter at checkout. You can create percentage-based, fixed amount, or free shipping discounts."
            })
        
        # If no specific topics matched, provide generic information
        if not mock_docs:
            mock_docs.append({
                "title": "Shopify Admin API Documentation",
                "url": "https://shopify.dev/api/admin-graphql",
                "excerpt": "Learn about the Shopify Admin API and how to use it to build apps.",
                "content": f"This is a generic response for '{prompt}'. The Shopify Admin API allows you to build apps that integrate with Shopify. You can manage products, orders, customers, inventory, and more."
            })
        
        return {
            "docs": mock_docs,
            "note": "This is mock data. In a real implementation with proper API access, this would return actual documentation from Shopify Dev."
        }
    
    def stop(self):
        """Stop the Shopify Dev MCP server process"""
        if self.process:
            print("Stopping Shopify Dev MCP server...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
        
        self.running = False
        self.server_url = None

# Create a singleton instance
mcp_server = ShopifyMCPServer()
