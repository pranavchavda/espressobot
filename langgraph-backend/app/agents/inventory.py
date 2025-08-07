from app.agents.base import BaseAgent
from typing import List

class InventoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="inventory",
            description="Manages inventory levels and stock tracking"
        )
    
    def _get_system_prompt(self) -> str:
        return "You are an inventory specialist for iDrinkCoffee.com."
    
    def _get_keywords(self) -> List[str]:
        return ["inventory", "stock", "quantity", "available"]
    
    def _get_tools(self) -> List:
        return []