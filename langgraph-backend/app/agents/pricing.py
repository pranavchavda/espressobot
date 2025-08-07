from app.agents.base import BaseAgent
from typing import List

class PricingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="pricing",
            description="Handles price updates, discounts, and pricing strategies"
        )
    
    def _get_system_prompt(self) -> str:
        return "You are a pricing specialist for iDrinkCoffee.com."
    
    def _get_keywords(self) -> List[str]:
        return ["price", "cost", "discount", "sale", "pricing"]
    
    def _get_tools(self) -> List:
        return []