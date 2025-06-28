#!/bin/bash

echo "🔍 Verifying EspressoBot Server Configuration"
echo "============================================"
echo ""

# Check if USE_MULTI_AGENT is set
if grep -q "USE_MULTI_AGENT=true" .env; then
    echo "✅ USE_MULTI_AGENT=true is set in .env"
else
    echo "❌ USE_MULTI_AGENT is not set to true in .env"
fi

echo ""
echo "📝 To start the server, run:"
echo "   pnpm dev"
echo ""
echo "The server should now start without errors and use the"
echo "Enhanced Multi-Agent Orchestrator with all 10 specialized agents!"
echo ""
echo "Once running, you can test with:"
echo "   node test-orchestrator-quick.js"
echo "   node test-tools-via-api.js"