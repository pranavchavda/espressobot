#!/usr/bin/env python3
"""Update all agents to mark their responses as intermediate"""

import os
import re
from pathlib import Path

agents_dir = Path("/home/pranav/espressobot/langgraph-backend/app/agents")

# List of agent files to update
agent_files = [
    "features_native_mcp.py",
    "inventory_native_mcp.py",
    "orders_native_mcp.py",
    "pricing_native_mcp.py",
    "product_mgmt_native_mcp.py",
    "sales_native_mcp.py",
    "utility_native_mcp.py",
    "ga4_analytics_native_mcp.py",
    "google_workspace_native_mcp.py",
    "graphql_native_mcp.py"
]

def update_agent_file(filepath):
    """Update an agent file to mark responses as intermediate"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern 1: AIMessage with agent metadata
    pattern1 = r'(state\["messages"\]\.append\(AIMessage\(\s*content=.*?,\s*metadata=\{"agent": self\.name)'
    replacement1 = r'\1, "intermediate": True'
    
    # Apply the replacement
    updated = re.sub(pattern1, replacement1, content)
    
    # Check if changes were made
    if updated != content:
        with open(filepath, 'w') as f:
            f.write(updated)
        print(f"✅ Updated {filepath.name}")
        return True
    else:
        print(f"⏭️  No changes needed for {filepath.name}")
        return False

# Update all agent files
updated_count = 0
for agent_file in agent_files:
    filepath = agents_dir / agent_file
    if filepath.exists():
        if update_agent_file(filepath):
            updated_count += 1
    else:
        print(f"❌ File not found: {agent_file}")

print(f"\n📊 Updated {updated_count} agent files")