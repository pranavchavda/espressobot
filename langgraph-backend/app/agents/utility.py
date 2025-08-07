from app.agents.base import BaseAgent
from typing import List

class UtilityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="utility",
            description="Handles memory and utility operations"
        )
    
    def _get_system_prompt(self) -> str:
        return "You are a utility specialist for iDrinkCoffee.com."
    
    def _get_keywords(self) -> List[str]:
        return ["memory", "remember", "utility", "helper"]
    
    def _get_tools(self) -> List:
        return []