#!/bin/bash
# Run the MCP server with proper environment

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Ensure we have the required environment variables
if [ -z "$SHOPIFY_SHOP_URL" ] || [ -z "$SHOPIFY_ACCESS_TOKEN" ]; then
    echo "Error: SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN must be set"
    exit 1
fi

# Run the MCP server
cd "$DIR"
exec python3 mcp-server.py