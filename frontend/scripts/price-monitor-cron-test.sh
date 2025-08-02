#!/bin/bash

# Price Monitor Cron Script - TEST VERSION (runs faster)
# This version runs with smaller datasets for quick testing

# Configuration
API_BASE="http://localhost:5173/api/price-monitor"
LOG_FILE="/tmp/price-monitor-test.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to make API calls
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local description="$4"
    
    log_message "Calling $description: $method $endpoint"
    
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
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        log_message "✅ $description completed successfully"
        echo "$body"
        return 0
    else
        log_message "❌ $description failed with HTTP $http_code"
        return 1
    fi
}

# Main execution
log_message "========================================="
log_message "Starting Price Monitor TEST Cron Job"
log_message "========================================="

# 1. Safe Sync Shopify Products (limited to one brand)
log_message "📦 Step 1: Syncing Shopify products (LIMITED TEST MODE)"
sync_result=$(api_call "POST" "/shopify-sync-safe/sync-idc-products-safe" '{"force": true, "brands": ["Eureka"], "limit": 10}' "Shopify sync test")
if [ $? -eq 0 ]; then
    log_message "Sync completed"
fi

# 2. Scrape Competitor Prices (starts background jobs)
log_message "🔍 Step 2: Starting competitor price scraping"
scrape_result=$(api_call "POST" "/scraping/scrape-all" '{}' "Competitor scraping")
if [ $? -eq 0 ]; then
    job_count=$(echo "$scrape_result" | grep -o '"job_id"' | wc -l)
    log_message "Started $job_count scraping jobs"
    log_message "Waiting 15 seconds for scraping to start..."
    sleep 15
fi

# 3. Scan for MAP Violations (dry run mode for speed)
log_message "⚠️  Step 3: Scanning for MAP violations (DRY RUN)"
violation_result=$(api_call "POST" "/violation-history/scan-and-record" '{"record_history": false, "dry_run": true}' "MAP violation scan")
if [ $? -eq 0 ]; then
    violations_found=$(echo "$violation_result" | grep -o '"violations_found":[0-9]*' | cut -d: -f2)
    log_message "Found $violations_found violations in dry run"
fi

# 4. Check Statistics
log_message "📊 Step 4: Checking violation statistics"
stats_result=$(api_call "GET" "/violation-history/statistics?group_by=day" "" "Violation statistics")
if [ $? -eq 0 ]; then
    active=$(echo "$stats_result" | grep -o '"active_violations":[0-9]*' | cut -d: -f2)
    total=$(echo "$stats_result" | grep -o '"total_violations":[0-9]*' | cut -d: -f2)
    log_message "Stats: $total total violations, $active currently active"
fi

# 5. Health Check
log_message "🏥 Step 5: Health check"
health_result=$(api_call "GET" "/health" "" "Health check")

# Summary
log_message "========================================="
log_message "✅ Test cron job completed!"
log_message "========================================="
echo ""
echo "Full log saved to: $LOG_FILE"
echo ""
echo "To run the full production cron job:"
echo "  ./scripts/price-monitor-cron.sh"