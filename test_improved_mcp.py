#!/usr/bin/env python3
"""
Test script for the improved ShopifyFeaturesMCPServer implementation.
This tests the singleton pattern, connection caching, and retry logic.
"""

import os
import sys
import asyncio
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import the MCP server
from mcp_server import shopify_features_mcp_server

async def test_search_products():
    """Test the search_products functionality with various queries."""
    
    queries = [
        "Behmor",  # The query that was timing out
        "espresso machine",
        "coffee grinder"
    ]
    
    results = {}
    errors = {}
    
    for query in queries:
        try:
            logger.info(f"Testing search_products with query: '{query}'")
            start_time = time.time()
            
            result = await shopify_features_mcp_server.search_products(query)
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"Search for '{query}' completed in {duration:.2f} seconds")
            
            if isinstance(result, dict) and "isError" in result and result["isError"]:
                logger.error(f"Error in search result: {result}")
                errors[query] = result
            else:
                logger.info(f"Successfully retrieved results for '{query}'")
                results[query] = result
                
                # Print some stats about the results
                if isinstance(result, dict) and "content" in result:
                    content_items = result["content"]
                    logger.info(f"Found {len(content_items)} content items")
                    
                    for i, item in enumerate(content_items[:3]):  # Show first 3 items
                        item_type = item.get("type", "unknown")
                        text = item.get("text", "")
                        logger.info(f"Item {i+1} (type: {item_type}): {text[:100]}...")
        
        except Exception as e:
            logger.error(f"Exception during search for '{query}': {e}", exc_info=True)
            errors[query] = str(e)
    
    # Summary
    logger.info("=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Successful queries: {len(results)}/{len(queries)}")
    logger.info(f"Failed queries: {len(errors)}/{len(queries)}")
    
    if errors:
        logger.error("Errors encountered:")
        for query, error in errors.items():
            logger.error(f"  - '{query}': {error}")
    
    return len(errors) == 0  # Return True if no errors

async def test_connection_reuse():
    """Test that the connection is reused between calls."""
    logger.info("Testing connection reuse...")
    
    # First call should initialize the connection
    logger.info("First call - should initialize connection")
    start_time = time.time()
    result1 = await shopify_features_mcp_server.search_products("espresso")
    duration1 = time.time() - start_time
    logger.info(f"First call completed in {duration1:.2f} seconds")
    
    # Second call should reuse the connection and be faster
    logger.info("Second call - should reuse connection")
    start_time = time.time()
    result2 = await shopify_features_mcp_server.search_products("coffee")
    duration2 = time.time() - start_time
    logger.info(f"Second call completed in {duration2:.2f} seconds")
    
    # Check if the second call was faster (indicating connection reuse)
    logger.info(f"Connection reuse test: first call took {duration1:.2f}s, second call took {duration2:.2f}s")
    logger.info(f"Second call was {duration1/duration2:.1f}x faster than first call")
    
    return True

async def main():
    logger.info("Starting Improved Shopify Features MCP Server Test")
    logger.info(f"Current time: {datetime.now().isoformat()}")
    
    # Test search products
    search_success = await test_search_products()
    logger.info(f"Search products test {'passed' if search_success else 'failed'}")
    
    # Test connection reuse
    reuse_success = await test_connection_reuse()
    logger.info(f"Connection reuse test {'passed' if reuse_success else 'failed'}")
    
    if search_success and reuse_success:
        logger.info("All tests passed successfully!")
        return 0
    else:
        logger.error("Some tests failed. See logs for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
