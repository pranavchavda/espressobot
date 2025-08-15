#!/usr/bin/env python3
"""
Direct test of MCP server with proper protocol
"""
import subprocess
import json
import sys

def send_request(request):
    """Send a request to the MCP server and get response"""
    proc = subprocess.Popen(
        ["python3", "mcp-server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send request
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline()
    if response_line:
        return json.loads(response_line)
    return None

# Test sequence
print("1. Initializing MCP server...")
init_response = send_request({
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {"roots": {"listChanged": True}}
    },
    "id": 1
})
print(f"Init response: {init_response}")

# Send initialized notification
print("\n2. Sending initialized notification...")
proc2 = subprocess.Popen(
    ["python3", "mcp-server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Initialize first
proc2.stdin.write(json.dumps({
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {"roots": {"listChanged": True}}
    },
    "id": 1
}) + "\n")
proc2.stdin.flush()
init_resp = proc2.stdout.readline()

# Send initialized notification
proc2.stdin.write(json.dumps({
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
}) + "\n")
proc2.stdin.flush()

# Now call the tool
print("\n3. Calling search_products tool...")
proc2.stdin.write(json.dumps({
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "search_products",
        "arguments": {
            "query": "Mexican Altura"
        }
    },
    "id": 2
}) + "\n")
proc2.stdin.flush()

# Read response
tool_response = proc2.stdout.readline()
if tool_response:
    result = json.loads(tool_response)
    print(f"\nTool response: {json.dumps(result, indent=2)}")
    
    # Extract and display products
    if "result" in result and "result" in result["result"]:
        products = result["result"]["result"]
        print(f"\nFound {len(products)} products:")
        for p in products:
            print(f"- {p['title']} ({p['handle']}) - ${p['price']} - SKU: {p['sku']}")

proc2.terminate()