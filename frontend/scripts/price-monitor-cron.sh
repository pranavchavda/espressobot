#!/bin/bash

# Price Monitor Cron Script
# Updates products, checks violations, and maintains the price monitoring system
# Safe for manual matches - uses only safe sync endpoints

# Configuration
API_BASE="https://node.idrinkcoffee.info/api/price-monitor"
LOG_DIR="/var/www/html/ebot/logs/price-monitor"
LOG_FILE="$LOG_DIR/cron-$(date +%Y%m%d).log"
ERROR_LOG="$LOG_DIR/cron-errors-$(date +%Y%m%d).log"
SLACK_WEBHOOK_URL="" # Optional: Add your Slack webhook for notifications
EMAIL_RECIPIENT="" # Optional: Add email for critical alerts

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to log errors
log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$ERROR_LOG" >&2
}

# Function to send notifications (optional)
send_notification() {
    local message="$1"
    local severity="$2" # info, warning, error
    
    # Slack notification
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Price Monitor Alert ($severity): $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null
    fi
    
    # Email notification for errors
    if [ "$severity" = "error" ] && [ -n "$EMAIL_RECIPIENT" ]; then
        echo "$message" | mail -s "Price Monitor Error Alert" "$EMAIL_RECIPIENT" 2>/dev/null
    fi
}

# Function to make API calls with error handling
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
        log_error "$description failed with HTTP $http_code: $body"
        send_notification "$description failed with HTTP $http_code" "error"
        return 1
    fi
}

# Main execution
log_message "========================================="
log_message "Starting Price Monitor Cron Job"
log_message "========================================="

# Record cron job start
record_job "cron_job" "running" "{\"started_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"

# Track overall success
overall_success=true

# Function to record job execution
record_job() {
    local job_type="$1"
    local status="$2"
    local details="$3"
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"job_type\":\"$job_type\",\"status\":\"$status\",\"details\":$details}" \
        "$API_BASE/job-status/record" > /dev/null 2>&1
}

# 1. Safe Sync Shopify Products
log_message "📦 Step 1: Syncing Shopify products (SAFE mode - preserves manual matches)"
sync_result=$(api_call "POST" "/shopify-sync-safe/sync-idc-products-safe" '{"force": true}' "Shopify product sync")
if [ $? -eq 0 ]; then
    created=$(echo "$sync_result" | grep -o '"total_products_created":[0-9]*' | cut -d: -f2)
    updated=$(echo "$sync_result" | grep -o '"total_products_updated":[0-9]*' | cut -d: -f2)
    preserved=$(echo "$sync_result" | grep -o '"manual_matches_preserved":[0-9]*' | cut -d: -f2)
    log_message "Sync results: $created created, $updated updated, $preserved manual matches preserved"
    record_job "shopify_sync" "completed" "{\"created\":$created,\"updated\":$updated,\"preserved\":$preserved}"
else
    overall_success=false
    record_job "shopify_sync" "failed" "{}"
fi

# 2. Scrape Competitor Prices
log_message "🔍 Step 2: Scraping competitor prices"
scrape_result=$(api_call "POST" "/scraping/scrape-all" '{}' "Competitor price scraping")
if [ $? -eq 0 ]; then
    job_count=$(echo "$scrape_result" | grep -o '"jobs":\[[^]]*\]' | grep -o '"job_id"' | wc -l)
    log_message "Started $job_count competitor scraping jobs (running in background)"
    record_job "competitor_scrape" "completed" "{\"jobs_started\":$job_count}"
    
    # Give scraping some time to complete
    log_message "Waiting 30 seconds for scraping to progress..."
    sleep 30
else
    overall_success=false
    record_job "competitor_scrape" "failed" "{}"
fi

# 3. Generate Product Matches (only for unmatched products)
# NOTE: This endpoint is currently not available - matching happens during scraping
# log_message "🔗 Step 3: Generating product matches for new products"
# match_result=$(api_call "POST" "/product-matching/generate-matches" '{"only_unmatched": true}' "Product matching")
# if [ $? -eq 0 ]; then
#     new_matches=$(echo "$match_result" | grep -o '"matches_created":[0-9]*' | cut -d: -f2)
#     log_message "Created $new_matches new product matches"
# else
#     overall_success=false
# fi
log_message "🔗 Step 3: Product matching happens automatically during scraping"

# 4. Scan for MAP Violations and Record History
log_message "⚠️  Step 4: Scanning for MAP violations"
violation_result=$(api_call "POST" "/violation-history/scan-and-record" '{"record_history": true, "dry_run": false}' "MAP violation scan")
if [ $? -eq 0 ]; then
    violations_found=$(echo "$violation_result" | grep -o '"violations_found":[0-9]*' | cut -d: -f2)
    history_recorded=$(echo "$violation_result" | grep -o '"history_recorded":[0-9]*' | cut -d: -f2)
    log_message "Found $violations_found violations, recorded $history_recorded in history"
    record_job "violation_scan" "completed" "{\"violations_found\":$violations_found,\"history_recorded\":$history_recorded}"
    
    # Send notification if violations found
    if [ "$violations_found" -gt 0 ]; then
        send_notification "Found $violations_found MAP violations" "warning"
    fi
else
    overall_success=false
    record_job "violation_scan" "failed" "{}"
fi

# 5. Generate Violation Statistics Report
log_message "📊 Step 5: Generating violation statistics"
stats_result=$(api_call "GET" "/violation-history/statistics?group_by=day" "" "Violation statistics")
if [ $? -eq 0 ]; then
    active_violations=$(echo "$stats_result" | grep -o '"active_violations":[0-9]*' | cut -d: -f2)
    log_message "Currently $active_violations active violations"
fi

# 6. Check System Health
log_message "🏥 Step 6: Checking system health"
health_result=$(api_call "GET" "/health" "" "System health check")
if [ $? -ne 0 ]; then
    overall_success=false
    send_notification "Price monitor health check failed!" "error"
fi

# 7. Clean up old logs (keep last 30 days)
log_message "🧹 Step 7: Cleaning up old logs"
find "$LOG_DIR" -name "cron-*.log" -mtime +30 -delete
find "$LOG_DIR" -name "cron-errors-*.log" -mtime +30 -delete
log_message "Cleaned up logs older than 30 days"

# Summary
log_message "========================================="
if [ "$overall_success" = true ]; then
    log_message "✅ Price Monitor Cron Job completed successfully"
    record_job "cron_job" "completed" "{\"completed_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"success\"}"
    exit 0
else
    log_message "⚠️  Price Monitor Cron Job completed with errors"
    record_job "cron_job" "failed" "{\"completed_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"error\"}"
    send_notification "Price monitor cron job completed with errors - check logs" "error"
    exit 1
fi