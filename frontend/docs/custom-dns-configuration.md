# Custom DNS Configuration for Shopify API Requests

This guide explains how to configure custom DNS servers for Shopify API requests to bypass Cloudflare issues.

## Overview

When Cloudflare has regional issues, you can configure the application to use alternative DNS servers (like Google DNS, Cloudflare DNS, or OpenDNS) instead of your system's default DNS.

## Configuration

Add the following environment variable to your `.env` file:

```bash
# Use Google DNS servers (recommended)
CUSTOM_DNS_SERVERS=8.8.8.8,8.8.4.4

# Or use Cloudflare DNS (if their DNS is working but CDN isn't)
CUSTOM_DNS_SERVERS=1.1.1.1,1.0.0.1

# Or use OpenDNS
CUSTOM_DNS_SERVERS=208.67.222.222,208.67.220.220

# Or use Quad9
CUSTOM_DNS_SERVERS=9.9.9.9,149.112.112.112
```

## How It Works

### Python (MCP Tools)
- The Python tools use a custom `requests` adapter that intercepts DNS resolution
- For Shopify domains, it uses the `dig` command to resolve IPs using the specified DNS servers
- Falls back to system DNS if custom resolution fails

### Node.js (Server-side)
- Uses Node.js `dns` module with custom lookup function
- Creates custom HTTP/HTTPS agents with the modified DNS resolution
- Only applies custom DNS to Shopify-related domains

## Benefits

1. **Bypass Regional Issues**: If Cloudflare has issues in your region, using different DNS servers can route traffic through working regions
2. **Failover**: If custom DNS fails, the system falls back to default DNS
3. **Selective Application**: Only Shopify domains use custom DNS, other requests use normal DNS

## Testing

To test if custom DNS is working:

```bash
# Set custom DNS and run a test
CUSTOM_DNS_SERVERS=8.8.8.8,8.8.4.4 npm run dev

# You should see in the logs:
# "Using custom DNS servers: 8.8.8.8, 8.8.4.4"
```

## Troubleshooting

1. **"dig command not found"**: Install dig with `sudo apt-get install dnsutils` (Ubuntu/Debian) or `brew install bind` (macOS)
2. **Still getting Cloudflare errors**: Try different DNS servers or check if the issue is with Cloudflare's edge servers rather than DNS
3. **Performance**: Custom DNS resolution adds slight overhead, only use when necessary

## Alternative Solutions

If DNS changes don't help, the issue might be with Cloudflare's edge servers. In that case:

1. **Use VPN**: Connect through a VPN to access Cloudflare from a different region
2. **Proxy**: Configure HTTP proxy to route requests through a different location
3. **Direct IP**: If you know Shopify's direct IPs (not recommended as they can change)

## Security Note

Using custom DNS servers means trusting those servers with your DNS queries. Only use reputable DNS providers.