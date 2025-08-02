#!/usr/bin/env python3
"""Custom DNS resolver for bypassing Cloudflare issues."""

import socket
import requests.adapters
from urllib3.util.connection import create_connection

class DNSResolverAdapter(requests.adapters.HTTPAdapter):
    """HTTP adapter that uses custom DNS servers."""
    
    def __init__(self, dns_servers=None, *args, **kwargs):
        self.dns_servers = dns_servers or ['8.8.8.8', '8.8.4.4']  # Google DNS by default
        super().__init__(*args, **kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        """Initialize pool manager with custom DNS resolution."""
        # Store original getaddrinfo
        self._original_getaddrinfo = socket.getaddrinfo
        
        def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            """Custom DNS resolution using specified DNS servers."""
            # For Shopify domains, use custom DNS
            if 'shopify' in host.lower() or 'myshopify' in host.lower():
                try:
                    # Use system DNS tools to resolve with custom DNS
                    import subprocess
                    for dns_server in self.dns_servers:
                        try:
                            # Use dig or nslookup to resolve
                            result = subprocess.run(
                                ['dig', f'@{dns_server}', '+short', host, 'A'],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.returncode == 0 and result.stdout.strip():
                                ip = result.stdout.strip().split('\n')[0]
                                # Return in getaddrinfo format
                                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]
                        except:
                            continue
                except:
                    pass
            
            # Fall back to original resolution
            return self._original_getaddrinfo(host, port, family, type, proto, flags)
        
        # Monkey patch socket.getaddrinfo
        socket.getaddrinfo = custom_getaddrinfo
        
        return super().init_poolmanager(*args, **kwargs)
    
    def close(self):
        """Restore original DNS resolution on close."""
        if hasattr(self, '_original_getaddrinfo'):
            socket.getaddrinfo = self._original_getaddrinfo
        super().close()


def get_dns_resolver_session(dns_servers=None):
    """Get a requests session with custom DNS resolution."""
    session = requests.Session()
    adapter = DNSResolverAdapter(dns_servers=dns_servers)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session