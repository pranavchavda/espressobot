#!/usr/bin/env python3
"""
Script to add scratchpad functionality to all MCP servers
Modifies each server to include scratchpad tools
"""

import os
import re
from pathlib import Path

# List of MCP server files to modify
MCP_SERVERS = [
    'mcp-products-server.py',
    'mcp-pricing-server.py', 
    'mcp-inventory-server.py',
    'mcp-sales-server.py',
    'mcp-features-server.py',
    'mcp-media-server.py',
    'mcp-integrations-server.py',
    'mcp-product-management-server.py',
    'mcp-utility-server.py',
    'mcp-orders-server.py'
]

SCRATCHPAD_IMPORT = """
# Scratchpad functionality
from mcp_scratchpad_tool import SCRATCHPAD_TOOLS"""

SCRATCHPAD_ADDITION = """
        
        # Add scratchpad tools
        for tool_def in SCRATCHPAD_TOOLS:
            self.add_tool_from_def(tool_def)"""

def add_tool_from_def_method():
    """Method to add to base server for tool definition support"""
    return '''
    def add_tool_from_def(self, tool_def):
        """Add a tool from a tool definition dictionary"""
        class DynamicTool:
            def __init__(self, name, description, input_schema, handler):
                self.name = name
                self.description = description
                self.input_schema = input_schema
                self._handler = handler
            
            async def run(self, **kwargs):
                if asyncio.iscoroutinefunction(self._handler):
                    return await self._handler(**kwargs)
                else:
                    return self._handler(**kwargs)
        
        tool = DynamicTool(
            tool_def['name'],
            tool_def['description'], 
            tool_def['inputSchema'],
            tool_def['handler']
        )
        self.add_tool(tool)'''

def modify_server_file(filepath):
    """Modify a single server file to include scratchpad functionality"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Skip if already modified
        if 'mcp_scratchpad_tool' in content:
            print(f"✓ {filepath.name} already has scratchpad tools, skipping")
            return True
            
        # Add import after the existing imports
        import_pattern = r'(from mcp_tools\..*?import.*?\n)'
        if re.search(import_pattern, content):
            content = re.sub(
                r'(from mcp_tools\..*?import.*?\n)(?=\n|\nclass)', 
                r'\1' + SCRATCHPAD_IMPORT + '\n',
                content,
                count=1
            )
        else:
            # Fallback: add after sys.path.insert line
            content = re.sub(
                r'(sys\.path\.insert\(.*?\n)',
                r'\1' + SCRATCHPAD_IMPORT + '\n',
                content,
                count=1
            )
        
        # Add scratchpad tools to _load_tools method
        load_tools_pattern = r'(def _load_tools\(self\):.*?)((?=\n    def|\n\nclass|\Z))'
        match = re.search(load_tools_pattern, content, re.DOTALL)
        
        if match:
            # Insert before the end of the method
            method_content = match.group(1)
            rest = match.group(2)
            
            # Add scratchpad tools at the end of the method
            if 'Add scratchpad tools' not in method_content:
                method_content += SCRATCHPAD_ADDITION
            
            content = content.replace(match.group(0), method_content + rest)
        
        # Write the modified content back
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"✓ Added scratchpad tools to {filepath.name}")
        return True
        
    except Exception as e:
        print(f"✗ Error modifying {filepath.name}: {e}")
        return False

def add_method_to_base_server():
    """Add the add_tool_from_def method to the base server"""
    base_server_path = Path(__file__).parent / 'mcp_base_server.py'
    
    try:
        with open(base_server_path, 'r') as f:
            content = f.read()
        
        # Skip if already has the method
        if 'add_tool_from_def' in content:
            print("✓ Base server already has add_tool_from_def method")
            return True
        
        # Add the method before the last class or at the end of EnhancedMCPServer class
        class_pattern = r'(class EnhancedMCPServer.*?)((?=\nclass|\Z))'
        match = re.search(class_pattern, content, re.DOTALL)
        
        if match:
            class_content = match.group(1)
            rest = match.group(2)
            
            # Add the method at the end of the class (before the last method ends)
            method_to_add = add_tool_from_def_method()
            class_content = class_content.rstrip() + method_to_add + '\n'
            
            content = content.replace(match.group(0), class_content + rest)
            
            with open(base_server_path, 'w') as f:
                f.write(content)
            
            print("✓ Added add_tool_from_def method to base server")
            return True
        else:
            print("✗ Could not find EnhancedMCPServer class in base server")
            return False
            
    except Exception as e:
        print(f"✗ Error modifying base server: {e}")
        return False

def main():
    """Main function to add scratchpad to all servers"""
    script_dir = Path(__file__).parent
    
    print("Adding scratchpad functionality to MCP servers...")
    print("=" * 50)
    
    # First, add the helper method to base server
    if not add_method_to_base_server():
        print("Failed to modify base server, aborting")
        return
    
    # Then modify each server
    success_count = 0
    for server_file in MCP_SERVERS:
        server_path = script_dir / server_file
        if server_path.exists():
            if modify_server_file(server_path):
                success_count += 1
        else:
            print(f"⚠ {server_file} not found, skipping")
    
    print("=" * 50)
    print(f"Successfully modified {success_count}/{len(MCP_SERVERS)} servers")
    print("Scratchpad tools added: scratchpad_read, scratchpad_write, scratchpad_append, scratchpad_add_entry, scratchpad_clear")

if __name__ == "__main__":
    main()