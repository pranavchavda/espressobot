from app.agents.base import BaseAgent
from typing import List

class IntegrationsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="integrations",
            description="Manages external integrations and APIs"
        )
    
    def _get_system_prompt(self) -> str:
        return "You are an integrations specialist for iDrinkCoffee.com."
    
    def _get_keywords(self) -> List[str]:
        return ["integration", "api", "external", "sync"]
    
    def _get_tools(self) -> List:
        return []