"""
Native MCP implementation for Perplexity research
"""

import os
import requests
from typing import Dict, Any, Optional
from ..base import BaseMCPTool

class PerplexityResearchTool(BaseMCPTool):
    """Research using Perplexity AI for real-time information"""
    
    name = "perplexity_research"
    description = "Research products, competitors, and industry information using Perplexity AI"
    context = """
    Uses Perplexity AI to research real-time information about:
    - Product specifications and reviews
    - Competitor pricing and features
    - Industry trends and news
    - Technical specifications
    - Market analysis
    
    Models available:
    - sonar: Fast, efficient searches
    - sonar-pro: More detailed, comprehensive research
    
    Use cases:
    - Research competitor pricing before setting prices
    - Find product specifications for listings
    - Get industry news and trends
    - Research suppliers and manufacturers
    - Technical troubleshooting
    
    Note: Results include real-time web data with citations.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Research query"
            },
            "model": {
                "type": "string",
                "enum": ["sonar", "sonar-pro"],
                "description": "Perplexity model to use (default: sonar)",
                "default": "sonar"
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, model: str = "sonar") -> Dict[str, Any]:
        """Execute Perplexity research"""
        api_key = os.environ.get('PERPLEXITY_API_KEY')
        if not api_key:
            return {
                "success": False,
                "error": "PERPLEXITY_API_KEY environment variable not set"
            }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'You are a helpful research assistant for iDrinkCoffee.com e-commerce operations.\n'
                        'About iDrinkCoffee.com: Premium coffee equipment retailer on Shopify, located in Milton, Ontario.\n'
                        'Focus on providing accurate, relevant information for:\n'
                        '- Product research and specifications\n'
                        '- Competitor analysis and pricing\n'
                        '- Industry trends and news\n'
                        '- Supplier and manufacturer information\n'
                        'Format responses with clear sections and include sources.'
                    )
                },
                {
                    'role': 'user',
                    'content': query
                }
            ]
        }
        
        try:
            response = requests.post(
                'https://api.perplexity.ai/chat/completions',
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            return {
                "success": True,
                "result": content,
                "model": model,
                "usage": data.get('usage', {}),
                "query": query
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
                "query": query
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
            
    async def test(self) -> Dict[str, Any]:
        """Test Perplexity integration"""
        if not os.environ.get('PERPLEXITY_API_KEY'):
            return {
                "status": "failed",
                "error": "PERPLEXITY_API_KEY not configured"
            }
            
        try:
            result = await self.execute("What is the current price of coffee beans?", model="sonar")
            if result["success"]:
                return {
                    "status": "passed",
                    "message": "Perplexity API accessible"
                }
            else:
                return {
                    "status": "failed",
                    "error": result["error"]
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }