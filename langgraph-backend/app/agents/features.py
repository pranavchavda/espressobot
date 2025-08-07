from app.agents.base import BaseAgent
from typing import List

class FeaturesAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="features",
            description="Manages product features and metafields"
        )
    
    def _get_system_prompt(self) -> str:
        return "You are a features specialist for iDrinkCoffee.com."
    
    def _get_keywords(self) -> List[str]:
        return ["feature", "metafield", "specification", "attribute"]
    
    def _get_tools(self) -> List:
        return []