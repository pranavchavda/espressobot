from app.agents.base import BaseAgent
from typing import List

class ProductManagementAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="product_mgmt",
            description="Creates and manages product listings"
        )
    
    def _get_system_prompt(self) -> str:
        return "You are a product management specialist for iDrinkCoffee.com."
    
    def _get_keywords(self) -> List[str]:
        return ["create", "duplicate", "new product", "listing"]
    
    def _get_tools(self) -> List:
        return []