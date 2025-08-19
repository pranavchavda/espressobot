"""
Utility Agent with web scraping and research capabilities
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import logging
import json

logger = logging.getLogger(__name__)

# Import the model manager
from app.config.agent_model_manager import agent_model_manager

# Import context mixin for A2A context handling
from app.agents.base_context_mixin import ContextAwareMixin

# Import the web scraper tool
from app.tools.web_scraper_tool import web_scraper_tool

class UtilityAgentNativeMCP(ContextAwareMixin):
    """Utility agent with web scraping and research capabilities"""
    
    def __init__(self):
        self.name = "utility"
        self.description = "Handles web scraping, research, and utility functions"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        return """You are a Utility specialist agent with expertise in web scraping, research, and data extraction.

You have access to advanced web scraping capabilities using LLM and BeautifulSoup. 
Use these tools to extract structured data from any website.

## Your Capabilities:
- **Web Scraping**: Extract content from any publicly accessible website
- **Structured Data Extraction**: Use AI-powered extraction to identify specific information
- **Research**: Analyze websites for competitive intelligence and market research
- **Data Processing**: Clean and format extracted data for analysis

## Web Scraping Features:
- Fetch and parse HTML content using BeautifulSoup
- Extract structured data using OpenRouter with anthropic/claude-3-5-sonnet-20241022 model
- Support for custom extraction prompts and examples
- Clean text processing and data formatting
- Error handling and retry mechanisms

## Available Extraction Templates:
- **Product Information**: Names, prices, features, specifications
- **Company Information**: Industry, executives, financial data
- **News Analysis**: People, organizations, locations, events
- **Contact Information**: Addresses, phone numbers, emails
- **Custom Extraction**: User-defined prompts and examples

## Web Scraping Process:
1. Fetch webpage content with proper headers
2. Parse HTML and extract clean text
3. Apply AI-powered structured extraction
4. Return formatted, searchable data

## Best Practices:
- Always respect robots.txt and rate limits
- Use descriptive extraction prompts
- Provide examples when possible for better accuracy
- Handle errors gracefully
- Return structured, actionable data

## Example Usage:
- "Extract product pricing from [website]"
- "Scrape company information from [company website]"
- "Get contact details from [business directory]"
- "Extract news articles about [topic] from [news site]"

When users request web scraping or data extraction, use the web scraper tool with appropriate extraction prompts and examples. Always provide clear, structured results with source URLs and extraction metadata."""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        try:
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            # Get last user message
            last_message = messages[-1]
            if not isinstance(last_message, HumanMessage):
                return state
            
            user_query = last_message.content
            logger.info(f"🚀 Utility agent processing query: {user_query[:100]}...")
            
            # Check if this is a web scraping request
            scraping_keywords = ["scrape", "extract", "website", "web", "url", "http", "parse", "data from"]
            is_scraping_request = any(keyword in user_query.lower() for keyword in scraping_keywords)
            
            if is_scraping_request:
                # Handle web scraping request
                response = await self._handle_web_scraping(user_query)
            else:
                # Handle general utility request with LLM
                response = await self._handle_general_request(user_query)
            
            # Add response to state
            state["messages"].append(AIMessage(
                content=response,
                metadata={"agent": self.name}
            ))
            
            state["last_agent"] = self.name
            logger.info(f"✅ Utility agent completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in UtilityAgent: {e}")
            state["messages"].append(AIMessage(
                content=f"I encountered an error: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    async def _handle_web_scraping(self, query: str) -> str:
        """Handle web scraping requests"""
        try:
            # Extract URL from query
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, query)
            
            if not urls:
                return "I'd be happy to help with web scraping! Please provide a URL to scrape. For example: 'Scrape product information from https://example.com'"
            
            url = urls[0]  # Use first URL found
            
            # Determine extraction type based on query
            extraction_examples = web_scraper_tool.get_example_prompts()
            
            if any(word in query.lower() for word in ["product", "price", "feature", "specification"]):
                prompt_info = extraction_examples["product_info"]
            elif any(word in query.lower() for word in ["company", "business", "executive", "financial"]):
                prompt_info = extraction_examples["company_info"]
            elif any(word in query.lower() for word in ["news", "article", "event", "people"]):
                prompt_info = extraction_examples["news_analysis"]
            else:
                # Default: extract general entities
                prompt_info = {
                    "prompt": "Extract key information, names, numbers, and important details from the webpage.",
                    "examples": []
                }
            
            # Perform web scraping
            result = await web_scraper_tool.scrape_and_extract(
                url=url,
                extraction_prompt=prompt_info["prompt"],
                extraction_examples=prompt_info.get("examples", [])
            )
            
            if not result["success"]:
                return f"Failed to scrape {url}: {result.get('error', 'Unknown error')}"
            
            # Format response
            response_parts = [
                f"**Web Scraping Results for {url}**",
                f"**Title:** {result['title']}",
                f"**Extracted {result['extraction_count']} entities:**\n"
            ]
            
            if result["extracted_data"]:
                for i, item in enumerate(result["extracted_data"][:10], 1):  # Show first 10
                    attrs_str = ", ".join([f"{k}: {v}" for k, v in item["attributes"].items()]) if item["attributes"] else "No attributes"
                    response_parts.append(f"{i}. **{item['class'].title()}**: {item['text']}")
                    if attrs_str != "No attributes":
                        response_parts.append(f"   - {attrs_str}")
                
                if len(result["extracted_data"]) > 10:
                    response_parts.append(f"\n... and {len(result['extracted_data']) - 10} more entities")
            else:
                response_parts.append("No structured data could be extracted.")
            
            response_parts.extend([
                f"\n**Content Preview:**",
                result["text"][:500] + "..." if len(result["text"]) > 500 else result["text"],
                f"\n**Metadata:**",
                f"- Content length: {result['metadata']['content_length']} characters",
                f"- Model used: {result['metadata']['model_used']}",
                f"- LLM available: {result['metadata']['has_llm']}"
            ])
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Web scraping error: {e}")
            return f"Error during web scraping: {str(e)}"
    
    async def _handle_general_request(self, query: str) -> str:
        """Handle general utility requests using LLM"""
        try:
            # Use context-aware messages from the mixin  
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"""I need help with this utility request: {query}

I can help with:
- Web scraping and data extraction from websites
- Research and competitive analysis  
- General utility functions and calculations
- Data processing and formatting

Please let me know specifically what you'd like me to do. If you need web scraping, provide a URL to scrape.""")
            ]
            
            # Get LLM response
            response = await self.model.ainvoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"General request error: {e}")
            return f"I encountered an error processing your request: {str(e)}"
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["scrape", "extract", "website", "web", "url", "http", "https", 
                   "parse", "data from", "research", "competitor", "industry", 
                   "trend", "analysis", "competitive analysis", "utility", 
                   "crawl", "fetch", "download", "content from"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)
    
    async def process_async(self, message: str) -> Dict[str, Any]:
        """
        Process a message asynchronously for the async orchestrator
        """
        try:
            # Create a state dict with the message
            state = {
                "messages": [HumanMessage(content=message)]
            }
            
            # Call the agent
            result_state = await self(state)
            
            # Extract the response from the last AI message
            messages = result_state.get("messages", [])
            response_content = ""
            
            # Find the last AI message
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    response_content = msg.content
                    break
            
            return {
                "content": response_content,
                "agent": self.name,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__}.process_async: {e}")
            return {
                "content": f"Error in {self.name} agent: {str(e)}",
                "agent": self.name,
                "success": False,
                "error": str(e)
            }