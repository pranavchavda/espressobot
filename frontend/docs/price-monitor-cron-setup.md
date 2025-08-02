# Price Monitor Cron Setup Guide

## Overview

This guide explains how to set up automated price monitoring using cron jobs. The system will:
- Sync products from Shopify (safely, preserving manual matches)
- Scrape competitor prices
- Generate new product matches
- Scan for MAP violations
- Record violation history
- Generate reports

## Available Scripts

### 1. Bash Script: `price-monitor-cron.sh`
- Simple bash script using curl
- Minimal dependencies
- Good for basic setups

### 2. Node.js Script: `price-monitor-cron.js`
- More robust error handling
- Better JSON parsing
- Integrated with environment variables
- Recommended for production

## Installation

### Prerequisites
```bash
# For bash script
sudo apt-get install curl mailutils  # Debian/Ubuntu
sudo yum install curl mailx          # RHEL/CentOS

# For Node.js script
npm install node-fetch
```

### Environment Variables (for Node.js script)
Add to your `.env` file:
```env
# Optional notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PRICE_MONITOR_EMAIL=alerts@yourdomain.com

# API configuration (if not localhost)
API_BASE_URL=http://localhost:5173/api/price-monitor
```

## Cron Setup

### 1. Edit your crontab
```bash
crontab -e
```

### 2. Add cron entries

#### Option A: Run every 4 hours
```cron
# Price Monitor - Every 4 hours
0 */4 * * * /home/pranav/espressobot/frontend/scripts/price-monitor-cron.sh >> /home/pranav/espressobot/frontend/logs/price-monitor/cron.log 2>&1
```

#### Option B: Run at specific times (recommended)
```cron
# Price Monitor - Run at 6 AM, 12 PM, 6 PM, and 10 PM
0 6,12,18,22 * * * /home/pranav/espressobot/frontend/scripts/price-monitor-cron.sh >> /home/pranav/espressobot/frontend/logs/price-monitor/cron.log 2>&1
```

#### Option C: Different schedules for different tasks
```cron
# Shopify sync - Once daily at 3 AM
0 3 * * * /home/pranav/espressobot/frontend/scripts/price-monitor-cron.sh >> /home/pranav/espressobot/frontend/logs/price-monitor/cron.log 2>&1

# Competitor scraping - Every 6 hours
0 */6 * * * curl -X POST http://localhost:5173/api/price-monitor/scraping/scrape-all

# Violation scan - Every 2 hours during business hours
0 8-20/2 * * * curl -X POST http://localhost:5173/api/price-monitor/violation-history/scan-and-record -H "Content-Type: application/json" -d '{"record_history":true}'
```

#### Option D: Using Node.js script
```cron
# Price Monitor with Node.js - Every 4 hours
0 */4 * * * cd /home/pranav/espressobot/frontend && /usr/bin/node scripts/price-monitor-cron.js
```

## Testing

### Test the bash script manually
```bash
cd /home/pranav/espressobot/frontend
./scripts/price-monitor-cron.sh
```

### Test the Node.js script manually
```bash
cd /home/pranav/espressobot/frontend
node scripts/price-monitor-cron.js
```

### Check if cron is running
```bash
# View cron logs
tail -f /var/log/cron  # or /var/log/syslog on some systems

# Check your custom logs
tail -f /home/pranav/espressobot/frontend/logs/price-monitor/cron-*.log
```

## Log Management

Logs are stored in `/home/pranav/espressobot/frontend/logs/price-monitor/`:
- `cron-YYYY-MM-DD.log` - Daily execution logs
- `cron-errors-YYYY-MM-DD.log` - Error logs
- `last-run-summary.json` - Summary of last run (Node.js script only)

The scripts automatically clean up logs older than 30 days.

## Monitoring & Alerts

### Slack Notifications
Set `SLACK_WEBHOOK_URL` to receive alerts for:
- MAP violations found
- Errors during execution
- System health issues

### Email Notifications
Set `PRICE_MONITOR_EMAIL` for critical error alerts.

### Manual Check
```bash
# Check last run summary (Node.js script)
cat /home/pranav/espressobot/frontend/logs/price-monitor/last-run-summary.json

# Check today's logs
tail -100 /home/pranav/espressobot/frontend/logs/price-monitor/cron-$(date +%Y-%m-%d).log

# Check for errors
grep ERROR /home/pranav/espressobot/frontend/logs/price-monitor/cron-errors-$(date +%Y-%m-%d).log
```

## Troubleshooting

### Cron not running
1. Check cron service: `sudo systemctl status cron`
2. Check crontab: `crontab -l`
3. Check permissions: `ls -la scripts/price-monitor-cron.sh`
4. Check PATH in cron (may need full paths)

### API connection issues
1. Ensure the app is running on port 5173
2. Check firewall settings
3. Test endpoints manually with curl

### Permission issues
```bash
# Make scripts executable
chmod +x scripts/price-monitor-cron.sh
chmod +x scripts/price-monitor-cron.js

# Ensure log directory is writable
mkdir -p logs/price-monitor
chmod 755 logs/price-monitor
```

## Performance Considerations

### Recommended Schedule
- **Shopify Sync**: Once or twice daily (low frequency, preserves manual matches)
- **Competitor Scraping**: Every 4-6 hours (respects rate limits)
- **Violation Scanning**: Every 2-4 hours (catches violations quickly)
- **Match Generation**: Once daily (for new products only)

### Resource Usage
- Each full run takes 2-10 minutes depending on data volume
- Uses minimal CPU but may spike during embedding generation
- Network bandwidth varies with number of products

### Rate Limiting
The scripts respect:
- Shopify API rate limits (automatic pagination)
- Competitor site rate limits (configured per site)
- Database connection pooling

## Security Notes

1. **Never commit credentials** to the repository
2. **Use environment variables** for sensitive data
3. **Restrict cron log permissions**: `chmod 640 logs/price-monitor/*.log`
4. **Monitor for suspicious activity** in logs
5. **Rotate logs regularly** (handled automatically)

## Example Full Setup

```bash
# 1. Navigate to project
cd /home/pranav/espressobot/frontend

# 2. Make scripts executable
chmod +x scripts/price-monitor-cron.sh
chmod +x scripts/price-monitor-cron.js

# 3. Create log directory
mkdir -p logs/price-monitor

# 4. Test the script
./scripts/price-monitor-cron.sh

# 5. Add to crontab
crontab -e
# Add: 0 */4 * * * /home/pranav/espressobot/frontend/scripts/price-monitor-cron.sh

# 6. Monitor logs
tail -f logs/price-monitor/cron-*.log
```

---

**Created**: August 2, 2025  
**Scripts**: `price-monitor-cron.sh` (bash), `price-monitor-cron.js` (Node.js)  
**Safe for manual matches**: ✅ Yes - uses only safe sync endpoints