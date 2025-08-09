"""
Conversation title generator using OpenRouter
Generates concise titles with emoji prefixes for conversations
"""
from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

class TitleGenerator:
    """Generate conversation titles with emojis using OpenRouter"""
    
    def __init__(self):
        import os
        from langchain_openai import ChatOpenAI
        
        # Use OpenRouter API instead of OpenAI directly
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            # Fallback to OpenAI if OpenRouter not configured
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY or OPENAI_API_KEY environment variable is required")
            # Use OpenAI directly as fallback
            self.model = ChatOpenAI(
                model="gpt-4.1-nano",
                max_completion_tokens=100,
                api_key=api_key,
                timeout=30,
                max_retries=1
            )
            logger.info("TitleGenerator initialized with OpenAI GPT-4o-mini (fallback)")
        else:
            # Use OpenRouter
            self.model = ChatOpenAI(
                model="openai/gpt-4o-mini",  # OpenRouter format
                max_completion_tokens=100,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=30,
                max_retries=1,
                default_headers={
                    "HTTP-Referer": "https://idrinkcoffee.com",
                    "X-Title": "EspressoBot"
                }
            )
            logger.info("TitleGenerator initialized with OpenRouter GPT-4o-mini")
    
    async def generate_title(self, first_message: str) -> str:
        """Generate a title with emoji prefix from the first message"""
        
        prompt = f"""Generate a title for this conversation:
"{first_message[:300]}"

Requirements:
- Maximum 30 characters total (including emoji)
- Start with ONE emoji
- Follow with 2-5 words
- Be specific and descriptive

Examples:
📊 Sales Analysis
💰 Pricing Updates
📦 Inventory Check
☕ Coffee Machines
🔧 Login Fix
📈 Revenue Report

Output only the title, nothing else:"""
        
        try:
            # Generate title with timeout
            from langchain_core.messages import SystemMessage, HumanMessage
            
            messages = [
                SystemMessage(content="You are a helpful assistant that generates concise, descriptive titles with emoji prefixes."),
                HumanMessage(content=prompt)
            ]
            
            response = await asyncio.wait_for(
                self.model.ainvoke(messages),
                timeout=10.0
            )
            
            # Extract and clean the title
            title = response.content.strip()
            
            # Ensure it starts with an emoji (fallback if not)
            import re
            emoji_pattern = re.compile(r'^[\U0001F300-\U0001F9FF\U00002700-\U000027BF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF]')
            
            if not emoji_pattern.match(title):
                # Add a default emoji if missing
                title = "💬 " + title
            
            # Limit length
            if len(title) > 50:
                title = title[:47] + "..."
            
            logger.info(f"Generated title: {title}")
            return title
            
        except asyncio.TimeoutError:
            logger.error("Title generation timed out")
            return "💬 New Conversation"
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return "💬 New Conversation"
    
    def generate_title_sync(self, first_message: str) -> str:
        """Synchronous wrapper for title generation"""
        try:
            return asyncio.run(self.generate_title(first_message))
        except:
            return "💬 New Conversation"

# Global instance
_title_generator: Optional[TitleGenerator] = None

def get_title_generator() -> TitleGenerator:
    """Get or create the global title generator instance"""
    global _title_generator
    if _title_generator is None:
        _title_generator = TitleGenerator()
    return _title_generator