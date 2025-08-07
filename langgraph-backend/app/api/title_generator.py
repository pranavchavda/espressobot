"""
Conversation title generator using GPT-5-nano
Generates concise titles with emoji prefixes for conversations
"""
from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

class TitleGenerator:
    """Generate conversation titles with emojis using GPT-5-nano"""
    
    def __init__(self):
        from app.config.llm_factory import llm_factory
        self.model = llm_factory.create_llm(
            model_name="gpt-5-nano",
            temperature=0.7,
            max_tokens=50
        )
        logger.info("TitleGenerator initialized with GPT-5-nano")
    
    async def generate_title(self, first_message: str) -> str:
        """Generate a title with emoji prefix from the first message"""
        
        prompt = f"""Generate a concise title (3-7 words) for a conversation that starts with:
"{first_message[:500]}"

Rules:
1. Start with ONE relevant emoji that represents the topic
2. Follow with 2-6 words that capture the essence
3. Be specific and descriptive
4. No quotes or extra punctuation
5. Format: 🎯 Topic Summary

Examples:
- 📊 Sales Data Analysis Request
- 🛍️ Product Pricing Update
- 📦 Inventory Check Yesterday
- ☕ Coffee Machine Recommendations
- 🔧 Fix Login Authentication Issue
- 📈 Revenue Report Generation
- 🤖 GPT-5 Model Testing
- 🎨 Image Upload Feature
- 💾 Database Migration Help

Title:"""
        
        try:
            # Generate title with timeout
            response = await asyncio.wait_for(
                self.model.ainvoke([
                    {"role": "system", "content": "You are a helpful assistant that generates concise, descriptive titles with emoji prefixes."},
                    {"role": "user", "content": prompt}
                ]),
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