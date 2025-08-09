#!/usr/bin/env python3
"""
Script to update all agents to use context-aware mixin
"""
import os
import re

AGENTS_TO_UPDATE = [
    "pricing_native_mcp.py",
    "inventory_native_mcp.py", 
    "sales_native_mcp.py",
    "orders_native_mcp.py",
    "media_native_mcp.py",
    "features_native_mcp.py",
    "product_mgmt_native_mcp.py",
    "utility_native_mcp.py",
    "integrations_native_mcp.py",
    "graphql_native_mcp.py",
    "ga4_analytics_native_mcp.py"
]

def update_agent_file(filepath):
    """Update an agent file to use the context mixin"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Skip if already updated
    if 'ContextAwareMixin' in content:
        print(f"  ✓ {filepath} already updated")
        return
    
    # Add SystemMessage import if not present
    if 'SystemMessage' not in content:
        content = re.sub(
            r'from langchain_core\.messages import (.*)',
            r'from langchain_core.messages import \1, SystemMessage',
            content
        )
    
    # Add the import for ContextAwareMixin after agent_model_manager import
    if 'from app.agents.base_context_mixin import ContextAwareMixin' not in content:
        content = re.sub(
            r'(from app\.config\.agent_model_manager import agent_model_manager)',
            r'\1\n\n# Import context mixin for A2A context handling\nfrom app.agents.base_context_mixin import ContextAwareMixin',
            content
        )
    
    # Add mixin to class definition
    # Match various class definition patterns
    patterns = [
        (r'class (\w+Agent\w*)\:', r'class \1(ContextAwareMixin):'),
        (r'class (\w+Agent\w*)\(.*\):', r'class \1(ContextAwareMixin):')
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            break
    
    # Update the agent invocation to use context
    # Look for agent.ainvoke patterns
    if 'agent_state = {"messages": messages}' in content:
        content = content.replace(
            '            # Use the agent to process the request with full conversation history\n'
            '            agent_state = {"messages": messages}',
            '            # Use context-aware messages from the mixin\n'
            '            context_aware_messages = self.build_context_aware_messages(state, self.system_prompt)\n'
            '            \n'
            '            # Use the agent to process the request with context\n'
            '            agent_state = {"messages": context_aware_messages}'
        )
        
        # Also update the logging
        content = re.sub(
            r'(logger\.info\(f"🚀 Running .* agent)',
            r'\1 with context-aware prompt',
            content
        )
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  ✅ Updated {filepath}")

def main():
    agents_dir = "app/agents"
    
    print("Updating agents to use context-aware mixin...")
    
    for agent_file in AGENTS_TO_UPDATE:
        filepath = os.path.join(agents_dir, agent_file)
        if os.path.exists(filepath):
            try:
                update_agent_file(filepath)
            except Exception as e:
                print(f"  ❌ Error updating {filepath}: {e}")
        else:
            print(f"  ⚠️  {filepath} not found")
    
    print("\nDone! All agents now support A2A context passing from orchestrator.")

if __name__ == "__main__":
    main()