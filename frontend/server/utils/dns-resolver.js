import dns from 'dns';
import { promisify } from 'util';
import http from 'http';
import https from 'https';

const resolve4 = promisify(dns.resolve4);

/**
 * Create a custom HTTP/HTTPS agent that uses specific DNS servers
 * @param {string[]} dnsServers - Array of DNS server IPs
 * @returns {Object} Object with httpAgent and httpsAgent
 */
export function createCustomDNSAgents(dnsServers = ['8.8.8.8', '8.8.4.4']) {
  // Set custom DNS servers
  dns.setServers(dnsServers);
  
  // Custom lookup function
  const customLookup = async (hostname, options, callback) => {
    try {
      // Only use custom DNS for Shopify domains
      if (hostname.includes('shopify') || hostname.includes('myshopify')) {
        const addresses = await resolve4(hostname);
        if (addresses && addresses.length > 0) {
          callback(null, addresses[0], 4);
          return;
        }
      }
      
      // Fall back to default DNS
      dns.lookup(hostname, options, callback);
    } catch (error) {
      // Fall back to default DNS on error
      dns.lookup(hostname, options, callback);
    }
  };
  
  // Create custom agents
  const httpAgent = new http.Agent({
    lookup: customLookup,
    keepAlive: true,
    keepAliveMsecs: 1000,
  });
  
  const httpsAgent = new https.Agent({
    lookup: customLookup,
    keepAlive: true,
    keepAliveMsecs: 1000,
  });
  
  return { httpAgent, httpsAgent };
}

/**
 * Get DNS servers from environment or use defaults
 * @returns {string[]} Array of DNS server IPs
 */
export function getDNSServers() {
  const customDNS = process.env.CUSTOM_DNS_SERVERS;
  if (customDNS) {
    return customDNS.split(',').map(s => s.trim());
  }
  // Default to Google DNS
  return ['8.8.8.8', '8.8.4.4'];
}