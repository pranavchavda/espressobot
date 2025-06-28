# Yotpo Review Request CLI Tool

This tool allows you to send Yotpo review request emails directly from the command line without logging into the Yotpo dashboard. It uses the same API endpoints that Yotpo's UI uses internally.

## Setup

### 1. Get Your Yotpo API Credentials

1. Log into your Yotpo dashboard
2. Go to Settings > General Settings
3. Find your App Key (e.g., "6DQ85qiKjzh6yzsbQ0x58s7cVhN1IySPK6UPhfxt")
4. Go to Settings > API
5. Find your API Secret

### 2. Set Environment Variables

Add these to your `.bashrc`, `.zshrc`, or set them in your terminal:

```bash
export YOTPO_APP_KEY="your_app_key_here"
export YOTPO_API_SECRET="your_api_secret_here"
export YOTPO_ACCOUNT_EMAIL_ID="140510"  # Optional, defaults to 140510
```

### 3. Find Your Product IDs

Product IDs in Yotpo are numeric (e.g., "5431060993"). You can find them by:
- Checking the Yotpo dashboard when viewing a product
- Looking at the network requests when sending a manual review request
- Using the Yotpo API to list products

### 4. Test the Connection

```bash
python tools/send_review_request.py --recipient "test@example.com" --product "5431060993" --dry-run
```

## Usage

### Single Recipient

```bash
# Basic usage with email only
python tools/send_review_request.py --recipient "customer@example.com" --product "5431060993"

# With full name
python tools/send_review_request.py --recipient "John Doe <john@example.com>" --product "5431060993"

# With spam filter enabled
python tools/send_review_request.py --recipient "jane@example.com" --product "5431060993" --spam-filter
```

### Multiple Recipients (CSV)

Create a CSV file with recipients:

```csv
name,email
John Doe,john@example.com
Jane Smith,jane@example.com
Coffee Lover,coffee@example.com
```

Then run:

```bash
python tools/send_review_request.py --csv recipients.csv --product "5431060993"
```

### Options

- `--recipient, -r`: Single recipient (format: "Name <email>" or just "email")
- `--csv, -c`: CSV file with multiple recipients
- `--product, -p`: Yotpo Product ID (numeric ID, required)
- `--spam-filter, -s`: Apply spam limitations (max 5 emails per 30 days, etc.)
- `--dry-run`: Preview what would be sent without actually sending

### How It Works

The tool uses the same API endpoints as Yotpo's web interface:

1. **Authentication**: Generates a utoken using your API credentials
2. **Upload Mailing List**: Uploads recipient data as CSV to Yotpo
3. **Send Burst Email**: Triggers the email send for all recipients
4. **Direct Delivery**: Emails are sent immediately (no order creation needed)

### Important Notes

1. **Product IDs**: Must use Yotpo's numeric product IDs (e.g., "5431060993"), not Shopify handles or SKUs

2. **Email Limits**: Yotpo enforces these limits:
   - Max 5 emails to same person within 30 days (when spam filter is ON)
   - Only 1 review request per product per person every 12 months
   - Max 2,500 emails per batch

3. **Email Settings**: Configure your email templates and settings in the Yotpo dashboard under Settings > Email Settings

4. **Spam Filter**: The `--spam-filter` flag activates Yotpo's spam limitations. Without it, emails bypass the usual frequency limits.

### Examples

```bash
# Send to single customer for specific product
python tools/send_review_request.py -r "pranav@idrinkcoffee.com" -p "5431060993"

# Send to multiple customers from CSV
python tools/send_review_request.py -c customers.csv -p "5431060993"

# Test without sending (dry run)
python tools/send_review_request.py -r "test@example.com" -p "5431060993" --dry-run

# Send with spam filter activated
python tools/send_review_request.py -r "customer@example.com" -p "5431060993" --spam-filter
```

### Troubleshooting

1. **Authentication Errors**: Check your environment variables are set correctly
2. **Invalid Product ID**: Ensure you're using Yotpo's numeric product ID
3. **No Email Received**: Check Yotpo dashboard email settings and recipient's spam folder
4. **API Errors**: The utoken expires after 14 days - the tool will regenerate it automatically

### Finding Product IDs

To find Yotpo product IDs:
1. Go to Yotpo dashboard > Reviews > Moderate Reviews
2. Filter by product
3. Check the URL or network requests for the product ID
4. Or use Yotpo's API to list products programmatically