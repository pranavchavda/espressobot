#!/usr/bin/env python3
"""Analyze which LLM model each agent uses"""
import os
import re
from pathlib import Path

def analyze_agents():
    agents_dir = Path("app/agents")
    
    # Get active agents from orchestrator
    active_agents = [
        ("ProductsAgentNativeMCPFinal", "products_native_mcp_final.py"),
        ("PricingAgentNativeMCP", "pricing_native_mcp.py"),
        ("InventoryAgentNativeMCP", "inventory_native_mcp.py"),
        ("SalesAgentNativeMCP", "sales_native_mcp.py"),
        ("FeaturesAgentNativeMCP", "features_native_mcp.py"),
        ("MediaAgentNativeMCP", "media_native_mcp.py"),
        ("IntegrationsAgentNativeMCP", "integrations_native_mcp.py"),
        ("ProductManagementAgentNativeMCP", "product_mgmt_native_mcp.py"),
        ("UtilityAgentNativeMCP", "utility_native_mcp.py"),
        ("GraphQLAgentNativeMCP", "graphql_native_mcp.py"),
        ("OrdersAgentNativeMCP", "orders_native_mcp.py"),
        ("GoogleWorkspaceAgentNativeMCP", "google_workspace_native_mcp.py"),
        ("GA4AnalyticsAgentNativeMCP", "ga4_analytics_native_mcp.py"),
    ]
    
    print("=" * 80)
    print("AGENT LLM MODEL ANALYSIS")
    print("=" * 80)
    
    # Check orchestrator
    print("\n📋 ORCHESTRATOR:")
    print("-" * 40)
    orchestrator_file = Path("app/orchestrator_direct.py")
    if orchestrator_file.exists():
        content = orchestrator_file.read_text()
        if "gpt-5-chat" in content:
            print("   Model: GPT-5-chat (via OpenRouter)")
        elif "gpt-5" in content:
            print("   Model: GPT-5 (via OpenRouter)")
    
    print("\n🤖 SPECIALIST AGENTS:")
    print("-" * 40)
    
    for class_name, filename in active_agents:
        filepath = agents_dir / filename
        if filepath.exists():
            content = filepath.read_text()
            
            # Extract model information
            model_info = "Unknown"
            
            # Check for ChatAnthropic
            if "ChatAnthropic" in content:
                match = re.search(r'model="([^"]+)"', content)
                if match:
                    model_info = f"Claude ({match.group(1)})"
            
            # Check for llm_factory
            elif "llm_factory.create_llm" in content:
                match = re.search(r'model_name="([^"]+)"', content)
                if match:
                    model_info = f"{match.group(1)} (via llm_factory)"
            
            # Check for model_config
            elif "model_config.get_langchain_llm" in content:
                model_info = "Dynamic (via model_config)"
            
            # Extract agent name
            agent_name = "unknown"
            name_match = re.search(r'self\.name = "([^"]+)"', content)
            if name_match:
                agent_name = name_match.group(1)
            
            print(f"   {agent_name:25} → {model_info}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    analyze_agents()