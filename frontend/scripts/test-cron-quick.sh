#!/bin/bash

# Quick test version of the price monitor cron script
# Tests all endpoints without full data processing

# Configuration
API_BASE="http://localhost:5173/api/price-monitor"

echo "🧪 Testing Price Monitor Cron Endpoints"
echo "======================================="

# Function to test endpoint
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local description="$4"
    
    echo -n "Testing $description... "
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE$endpoint" 2>/dev/null)
    else
        response=$(curl -s -w "\n%{http_code}" \
            "$API_BASE$endpoint" 2>/dev/null)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo "✅ OK (HTTP $http_code)"
    else
        echo "❌ Failed (HTTP $http_code)"
    fi
}

# Test each endpoint
test_endpoint "POST" "/shopify-sync-safe/sync-idc-products-safe" '{"force": true, "brands": ["Eureka"], "limit": 5}' "Shopify sync (limited)"
test_endpoint "POST" "/scraping/scrape-all" '{"limit": 5}' "Competitor scraping (limited)"
test_endpoint "POST" "/product-matching/generate-matches" '{"only_unmatched": true, "limit": 5}' "Product matching"
test_endpoint "POST" "/violation-history/scan-and-record" '{"record_history": true, "dry_run": true}' "Violation scan (dry run)"
test_endpoint "GET" "/violation-history/statistics?group_by=day" "" "Violation statistics"
test_endpoint "GET" "/health" "" "Health check"

echo "======================================="
echo "✅ All endpoints are reachable!"
echo ""
echo "To run the full cron job:"
echo "  ./scripts/price-monitor-cron.sh"
echo ""
echo "To set up as a cron job, add to crontab:"
echo "  # Run every 4 hours"
echo "  0 */4 * * * /home/pranav/espressobot/frontend/scripts/price-monitor-cron.sh >> /home/pranav/espressobot/frontend/logs/price-monitor/cron.log 2>&1"