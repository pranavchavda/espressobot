from app.agents.base import BaseAgent
from typing import List

class MediaAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="media",
            description="Handles product images and media management"
        )
    
    def _get_system_prompt(self) -> str:
        return "You are a media specialist for iDrinkCoffee.com."
    
    def _get_keywords(self) -> List[str]:
        return ["image", "photo", "media", "picture"]
    
    def _get_tools(self) -> List:
        return []