#!/bin/bash

# Source NVM and use Node.js v22
source $HOME/.nvm/nvm.sh
nvm use 22

# Print node version for debugging
echo "Using Node version: $(node -v)"

# Set the MCP bearer token
export MCP_BEARER_TOKEN="${MCP_BEARER_TOKEN:-ihwvXarctxYJH0OUgA8Hg/WJX+NSPuOka7uRKLNENDU=}"
echo "Starting Shopify MCP stdio client..."

# Execute the MCP client
npx -y @pranavchavda/shopify-mcp-stdio-client@latest
