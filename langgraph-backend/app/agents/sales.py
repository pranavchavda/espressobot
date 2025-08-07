from app.agents.base import BaseAgent
from typing import List

class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="sales",
            description="Manages sales campaigns and promotions"
        )
    
    def _get_system_prompt(self) -> str:
        return "You are a sales specialist for iDrinkCoffee.com."
    
    def _get_keywords(self) -> List[str]:
        return ["sale", "campaign", "promotion", "map"]
    
    def _get_tools(self) -> List:
        return []