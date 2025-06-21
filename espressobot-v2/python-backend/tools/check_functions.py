#!/usr/bin/env python3
"""Check all function names in the tools."""

import os
import re

tools_dir = os.path.dirname(os.path.abspath(__file__))

# Tools to check
tools_to_check = [
    'update_status.py',
    'manage_map_sales.py', 
    'manage_variant_links.py',
    'manage_inventory_policy.py',
    'upload_to_skuvault.py',
    'bulk_price_update.py',
    'graphql_query.py',
    'graphql_mutation.py',
    'pplx.py'
]

for tool_file in tools_to_check:
    tool_path = os.path.join(tools_dir, tool_file)
    if os.path.exists(tool_path):
        print(f"\n=== {tool_file} ===")
        with open(tool_path, 'r') as f:
            content = f.read()
            # Find all function definitions
            functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
            # Filter out main and helper functions
            main_funcs = [f for f in functions if not f.startswith('_') and f != 'main']
            print(f"Functions: {', '.join(main_funcs)}")