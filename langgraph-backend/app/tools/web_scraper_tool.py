"""
Web scraping tool using BeautifulSoup and LLM for structured data extraction.
"""

import asyncio
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
import logging
import os
import json
from urllib.parse import urljoin, urlparse
import textwrap
from langchain_core.messages import SystemMessage, HumanMessage
from app.config.llm_factory import llm_factory, Provider

logger = logging.getLogger(__name__)

class WebScraperTool:
    """Web scraping tool with LLM for structured data extraction"""
    
    def __init__(self):
        self.name = "web_scraper"
        self.description = "Extract structured data from any website using LLM and BeautifulSoup"
        
        # Set up LLM using our existing factory with OpenRouter
        try:
            self.llm = llm_factory.create_llm(
                model_name="anthropic/claude-3-5-sonnet-20241022",
                preferred_provider=Provider.OPENROUTER,
                temperature=0.0,
                max_tokens=2048
            )
            logger.info("Web scraper initialized with anthropic/claude-3-5-sonnet-20241022 via OpenRouter")
        except Exception as e:
            logger.error(f"Failed to initialize LLM for web scraper: {e}")
            self.llm = None
    
    async def scrape_and_extract(
        self, 
        url: str, 
        extraction_prompt: str, 
        extraction_examples: Optional[List[Dict]] = None,
        max_text_length: int = 10000,
        model_id: str = "anthropic/claude-3-5-sonnet-20241022"
    ) -> Dict[str, Any]:
        """
        Scrape a website and extract structured data using LangExtract.
        
        Args:
            url: The URL to scrape
            extraction_prompt: Description of what to extract
            extraction_examples: Optional examples to guide extraction
            max_text_length: Maximum text length to process
            model_id: LLM model to use for extraction
            
        Returns:
            Dictionary containing extracted data and metadata
        """
        try:
            # Step 1: Fetch and parse the webpage
            logger.info(f"Fetching content from: {url}")
            content_result = await self._fetch_web_content(url, max_text_length)
            
            if not content_result["success"]:
                return content_result
            
            # Step 2: Extract structured data using LLM
            if self.llm:
                logger.info("Extracting structured data using LLM")
                extraction_result = await self._extract_with_llm(
                    content_result["text"], 
                    extraction_prompt, 
                    extraction_examples,
                    model_id
                )
            else:
                logger.warning("No LLM available, returning raw content only")
                extraction_result = {
                    "success": True,
                    "extractions": [],
                    "warning": "No LLM available for extraction. Returning raw content only."
                }
            
            # Combine results
            return {
                "success": True,
                "url": url,
                "title": content_result.get("title", ""),
                "text": content_result["text"][:1000] + "..." if len(content_result["text"]) > 1000 else content_result["text"],
                "extracted_data": extraction_result.get("extractions", []),
                "extraction_count": len(extraction_result.get("extractions", [])),
                "metadata": {
                    "content_length": len(content_result["text"]),
                    "extraction_prompt": extraction_prompt,
                    "model_used": model_id,
                    "has_llm": bool(self.llm)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in scrape_and_extract: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def _fetch_web_content(self, url: str, max_length: int) -> Dict[str, Any]:
        """Fetch and parse web content using BeautifulSoup"""
        try:
            # Make HTTP request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title"
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Truncate if needed
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            return {
                "success": True,
                "title": title_text,
                "text": text,
                "url": url,
                "content_length": len(text)
            }
            
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to fetch URL: {str(e)}",
                "url": url
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse content: {str(e)}",
                "url": url
            }
    
    async def _extract_with_llm(
        self, 
        text: str, 
        prompt: str, 
        examples: Optional[List[Dict]], 
        model_id: str
    ) -> Dict[str, Any]:
        """Extract structured data using LLM"""
        try:
            # Build system prompt with examples
            system_prompt = f"""You are an expert data extraction system. Extract structured information from text based on the given instructions.

EXTRACTION TASK: {prompt}

OUTPUT FORMAT:
Return a JSON object with an "extractions" array. Each extraction should have:
- "class": The category/type of the extracted entity
- "text": The exact text extracted from the source
- "attributes": Dictionary of additional context/attributes
- "position": Character position (if determinable)

EXAMPLE OUTPUT FORMAT:
{{
    "extractions": [
        {{
            "class": "company",
            "text": "Apple Inc.",
            "attributes": {{"type": "technology", "industry": "consumer electronics"}},
            "position": {{"start": 0, "end": 10}}
        }}
    ]
}}

RULES:
1. Extract exact text - do not paraphrase
2. Use meaningful class names
3. Add relevant attributes for context
4. Be precise and avoid overlapping extractions
5. Return ONLY valid JSON
"""

            # Add examples to system prompt if provided
            if examples:
                system_prompt += "\n\nEXAMPLES:\n"
                for i, example in enumerate(examples[:3], 1):  # Limit to 3 examples
                    if "text" in example and "extractions" in example:
                        system_prompt += f"\nExample {i}:\nText: {example['text']}\n"
                        system_prompt += f"Output: {json.dumps({'extractions': example['extractions']}, indent=2)}\n"
            
            # Truncate text if too long
            max_text_length = 8000  # Leave room for prompt and response
            if len(text) > max_text_length:
                text = text[:max_text_length] + "..."
                logger.info(f"Truncated text to {max_text_length} characters for extraction")
            
            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Extract structured data from this text:\n\n{text}")
            ]
            
            # Get LLM response
            response = await self.llm.ainvoke(messages)
            response_text = response.content.strip()
            
            # Parse JSON response
            try:
                # Try to find JSON in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    result = json.loads(json_text)
                    extractions = result.get("extractions", [])
                else:
                    # Fallback: try to parse entire response as JSON
                    result = json.loads(response_text)
                    extractions = result.get("extractions", [])
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"LLM response: {response_text[:500]}...")
                
                # Fallback: extract simple patterns
                extractions = self._fallback_extraction(text, prompt)
            
            return {
                "success": True,
                "extractions": extractions,
                "total_extractions": len(extractions)
            }
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {
                "success": False,
                "error": f"LLM extraction failed: {str(e)}",
                "extractions": []
            }
    
    def _fallback_extraction(self, text: str, prompt: str) -> List[Dict]:
        """Fallback extraction method using simple pattern matching"""
        extractions = []
        
        # Simple patterns based on common extraction types
        if "product" in prompt.lower() or "price" in prompt.lower():
            # Extract potential prices
            import re
            price_pattern = r'\$[\d,]+\.?\d*'
            prices = re.findall(price_pattern, text)
            for price in prices[:5]:  # Limit to 5
                extractions.append({
                    "class": "price",
                    "text": price,
                    "attributes": {"currency": "USD"},
                    "position": {"start": text.find(price), "end": text.find(price) + len(price)}
                })
        
        if "company" in prompt.lower() or "organization" in prompt.lower():
            # Extract potential company names (simple heuristic)
            import re
            company_pattern = r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]*)*(?:\s+(?:Inc|Corp|LLC|Ltd|Co)\b\.?)?'
            companies = re.findall(company_pattern, text)
            for company in companies[:5]:  # Limit to 5
                extractions.append({
                    "class": "company",
                    "text": company,
                    "attributes": {"type": "organization"},
                    "position": {"start": text.find(company), "end": text.find(company) + len(company)}
                })
        
        return extractions
    
    def get_example_prompts(self) -> Dict[str, Dict]:
        """Get example extraction prompts for common use cases"""
        return {
            "product_info": {
                "prompt": "Extract product information including name, price, features, and specifications.",
                "examples": [
                    {
                        "text": "iPhone 15 Pro - $999. Features: A17 Pro chip, titanium design, 48MP camera system.",
                        "extractions": [
                            {"class": "product", "text": "iPhone 15 Pro", "attributes": {"type": "smartphone"}},
                            {"class": "price", "text": "$999", "attributes": {"currency": "USD"}},
                            {"class": "feature", "text": "A17 Pro chip", "attributes": {"type": "processor"}},
                            {"class": "feature", "text": "48MP camera system", "attributes": {"type": "camera"}}
                        ]
                    }
                ]
            },
            "company_info": {
                "prompt": "Extract company information including name, industry, financial data, and key executives.",
                "examples": [
                    {
                        "text": "Tesla Inc., led by CEO Elon Musk, reported $96.8 billion in revenue for 2023 in the automotive industry.",
                        "extractions": [
                            {"class": "company", "text": "Tesla Inc.", "attributes": {"industry": "automotive"}},
                            {"class": "executive", "text": "Elon Musk", "attributes": {"role": "CEO"}},
                            {"class": "financial", "text": "$96.8 billion in revenue", "attributes": {"year": "2023", "metric": "revenue"}}
                        ]
                    }
                ]
            },
            "news_analysis": {
                "prompt": "Extract key entities from news articles including people, organizations, locations, and events.",
                "examples": [
                    {
                        "text": "President Biden announced new climate policies at the White House yesterday, affecting renewable energy companies.",
                        "extractions": [
                            {"class": "person", "text": "President Biden", "attributes": {"role": "president"}},
                            {"class": "location", "text": "White House", "attributes": {"type": "government_building"}},
                            {"class": "topic", "text": "climate policies", "attributes": {"domain": "environment"}},
                            {"class": "industry", "text": "renewable energy companies", "attributes": {"sector": "energy"}}
                        ]
                    }
                ]
            }
        }

# Global instance
web_scraper_tool = WebScraperTool()