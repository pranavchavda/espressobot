#!/usr/bin/env python3
"""
Script to update all agents to use dynamic model configuration
"""
import os
import re
from pathlib import Path

def update_agent_file(filepath: Path):
    """Update an agent file to use dynamic model configuration"""
    
    content = filepath.read_text()
    original_content = content
    
    # Check if already updated
    if "agent_model_manager" in content:
        print(f"  ✓ {filepath.name} already updated")
        return False
    
    # Pattern to find the model initialization
    patterns = [
        (r'self\.model = ChatAnthropic\([^)]+\)', 
         'self.model = agent_model_manager.get_model_for_agent(self.name)\n        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")'),
        (r'self\.model = ChatOpenAI\([^)]+\)',
         'self.model = agent_model_manager.get_model_for_agent(self.name)\n        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")'),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            break
    
    # Add import if model was changed
    if content != original_content:
        # Add import statement after other imports
        import_line = "from app.config.agent_model_manager import agent_model_manager"
        
        # Find where to add the import (after other app imports)
        if "from app." in content:
            # Add after last app import
            lines = content.split('\n')
            last_app_import = -1
            for i, line in enumerate(lines):
                if line.startswith('from app.'):
                    last_app_import = i
            
            if last_app_import >= 0:
                lines.insert(last_app_import + 1, import_line)
                content = '\n'.join(lines)
        else:
            # Add after logger import
            content = content.replace(
                'logger = logging.getLogger(__name__)',
                f'logger = logging.getLogger(__name__)\n\n# Import the model manager\n{import_line}'
            )
        
        # Write updated content
        filepath.write_text(content)
        print(f"  ✅ Updated {filepath.name}")
        return True
    
    print(f"  ⚠️  No model initialization found in {filepath.name}")
    return False

def main():
    """Update all agent files"""
    print("=" * 60)
    print("Updating Agents to Use Dynamic Model Configuration")
    print("=" * 60)
    
    agents_dir = Path("app/agents")
    
    # List of agent files to update
    agent_files = [
        "products_native_mcp_final.py",
        "pricing_native_mcp.py",
        "inventory_native_mcp.py",
        "sales_native_mcp.py",
        "features_native_mcp.py",
        "media_native_mcp.py",
        "integrations_native_mcp.py",
        "product_mgmt_native_mcp.py",
        "utility_native_mcp.py",
        "graphql_native_mcp.py",
        "orders_native_mcp.py",
        "google_workspace_native_mcp.py",
        "ga4_analytics_native_mcp.py",
    ]
    
    updated_count = 0
    
    print("\nProcessing agent files:")
    for filename in agent_files:
        filepath = agents_dir / filename
        if filepath.exists():
            if update_agent_file(filepath):
                updated_count += 1
        else:
            print(f"  ❌ {filename} not found")
    
    print("\n" + "=" * 60)
    print(f"Updated {updated_count} agent files")
    print("=" * 60)

if __name__ == "__main__":
    main()