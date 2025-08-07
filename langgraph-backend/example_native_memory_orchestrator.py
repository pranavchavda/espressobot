#!/usr/bin/env python3
"""Example orchestrator using native LangChain/LangGraph memory integration

This demonstrates how to integrate the native memory system into your existing
LangGraph orchestrator, replacing custom memory implementations.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import Dict, Any, List, Optional
import logging
import os

from app.state.graph_state import GraphState
from app.agents.base import BaseAgent
from app.agents.router import RouterAgent
from app.memory.native_memory_integration import (
    NativeMemoryIntegration,
    MemoryType,
    ContextTier,
    create_native_memory_manager,
    create_memory_node
)
from langchain_core.messages import AIMessage, HumanMessage
import asyncio

logger = logging.getLogger(__name__)

class NativeMemoryOrchestrator:
    """Orchestrator using native LangChain/LangGraph memory features
    
    This replaces custom memory implementations with native components:
    - LangGraph PostgresSaver for checkpointing
    - LangChain memory classes for conversation history
    - Native pgvector for semantic search
    """
    
    def __init__(self, memory_type: MemoryType = MemoryType.COMBINED):
        self.agents: Dict[str, BaseAgent] = {}
        
        # Initialize native memory integration
        self.memory_integration = NativeMemoryIntegration(
            memory_type=memory_type,
            context_tier=ContextTier.STANDARD
        )
        
        # Create native memory components
        self.memory_manager = create_native_memory_manager()
        self.memory_node = create_memory_node(self.memory_manager)
        
        self.graph = None
        self.router = None
        self._initialize_agents()
        self._build_native_graph()
    
    def _initialize_agents(self):
        """Initialize all specialist agents (same as before)"""
        # Use existing agent initialization
        from app.agents.products_native_mcp_final import ProductsAgentNativeMCPFinal
        from app.agents.pricing_native_mcp import PricingAgentNativeMCP
        from app.agents.general import GeneralAgent
        
        try:
            self.agents["general"] = GeneralAgent()
            self.agents["products"] = ProductsAgentNativeMCPFinal()
            self.agents["pricing"] = PricingAgentNativeMCP()
            
            # Initialize router with native memory awareness
            self.router = RouterAgent()
            
            logger.info(f"Initialized {len(self.agents)} agents with native memory")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
    
    def _build_native_graph(self):
        """Build LangGraph workflow with native memory integration"""
        workflow = StateGraph(GraphState)
        
        # Add memory nodes using native components
        workflow.add_node("load_memory", self.memory_node.load_memory_context)
        workflow.add_node("route", self._route_with_memory)
        
        # Add agent nodes (enhanced with memory context)
        for agent_name in self.agents.keys():
            workflow.add_node(agent_name, self._create_memory_enhanced_agent_node(agent_name))
        
        workflow.add_node("persist_memory", self.memory_node.persist_conversation)
        
        # Build workflow edges
        workflow.add_edge(START, "load_memory")
        workflow.add_edge("load_memory", "route")
        
        # Router to agents
        for agent_name in self.agents.keys():
            workflow.add_conditional_edges(
                "route",
                self._should_route_to_agent,
                {agent_name: agent_name}
            )
        
        # All agents to memory persistence
        for agent_name in self.agents.keys():
            workflow.add_edge(agent_name, "persist_memory")
        
        workflow.add_edge("persist_memory", END)
        
        # Compile with native checkpointer
        self.graph = workflow.compile(checkpointer=self.memory_manager.checkpointer)
        
        logger.info("Built native memory-enhanced LangGraph workflow")
    
    def _create_memory_enhanced_agent_node(self, agent_name: str):
        """Create memory-enhanced agent node"""
        async def memory_enhanced_agent(state: GraphState) -> GraphState:
            agent = self.agents[agent_name]
            
            # Agent now has access to memory context in state
            memory_context = state.get("memory_context", {})
            
            # Log memory context usage
            if memory_context:
                logger.debug(f"Agent {agent_name} using memory context with keys: {list(memory_context.keys())}")
            
            # Process with agent (memory context available in state)
            try:
                result_state = await agent.process(state)
                logger.info(f"Agent {agent_name} processed successfully")
                return result_state
            except Exception as e:
                logger.error(f"Agent {agent_name} processing failed: {e}")
                state.messages.append(AIMessage(
                    content=f"I encountered an error while processing your request. Please try again."
                ))
                return state
        
        return memory_enhanced_agent
    
    async def _route_with_memory(self, state: GraphState) -> GraphState:
        """Route with memory context awareness"""
        try:
            # Router can use memory context for better routing decisions
            memory_context = state.get("memory_context", {})
            
            # Enhanced routing with conversation history
            chat_history = memory_context.get("chat_history", [])
            semantic_context = memory_context.get("semantic_context", [])
            
            # Add context to routing decision
            routing_context = {
                "recent_topics": self._extract_recent_topics(chat_history),
                "semantic_hints": self._extract_semantic_hints(semantic_context)
            }
            
            # Use router with enhanced context
            routed_state = await self.router.route(state, routing_context)
            
            return routed_state
            
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            state.next_agent = "general"  # Fallback to general agent
            return state
    
    def _extract_recent_topics(self, chat_history: List) -> List[str]:
        """Extract topics from recent conversation"""
        topics = []
        # Simple keyword extraction from recent messages
        for msg in chat_history[-5:]:  # Last 5 messages
            content = msg.content if hasattr(msg, 'content') else str(msg)
            # Extract potential topics (simplified)
            words = content.lower().split()
            topics.extend([w for w in words if len(w) > 5])  # Words longer than 5 chars
        return list(set(topics))[:10]  # Top 10 unique topics
    
    def _extract_semantic_hints(self, semantic_context: List) -> List[str]:
        """Extract hints from semantic search results"""
        hints = []
        for item in semantic_context[:3]:  # Top 3 semantic matches
            if hasattr(item, 'page_content'):
                hints.append(item.page_content[:100])  # First 100 chars
            elif isinstance(item, dict):
                hints.append(item.get('content', '')[:100])
        return hints
    
    def _should_route_to_agent(self, state: GraphState) -> str:
        """Determine which agent to route to"""
        return state.get("next_agent", "general")
    
    async def initialize(self):
        """Initialize the native memory orchestrator"""
        try:
            # Initialize native memory integration
            await self.memory_integration.initialize()
            
            # Initialize memory manager
            await self.memory_manager.initialize()
            
            logger.info("Native memory orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    async def process_message(self, 
                            user_message: str, 
                            user_id: str,
                            thread_id: Optional[str] = None) -> str:
        """Process user message with native memory integration"""
        thread_id = thread_id or f"{user_id}_default"
        
        # Create initial state
        initial_state = GraphState(
            user_id=user_id,
            thread_id=thread_id,
            messages=[HumanMessage(content=user_message)]
        )
        
        # Configuration for native checkpointing
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id
            }
        }
        
        try:
            # Process through native memory-enhanced graph
            result = await self.graph.ainvoke(initial_state, config=config)
            
            # Extract response
            if result.messages:
                latest_message = result.messages[-1]
                if hasattr(latest_message, 'content'):
                    return latest_message.content
            
            return "I apologize, but I couldn't generate a response. Please try again."
            
        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            return "I encountered an error processing your request. Please try again."
    
    async def get_conversation_history(self, user_id: str, thread_id: str) -> List[Dict[str, Any]]:
        """Get conversation history using native checkpointing"""
        try:
            checkpoint = await self.memory_manager.load_conversation_checkpoint(user_id, thread_id)
            if checkpoint:
                messages = checkpoint.get("messages", [])
                return [
                    {
                        "role": "human" if isinstance(msg, HumanMessage) else "ai",
                        "content": msg.content if hasattr(msg, 'content') else str(msg),
                        "timestamp": checkpoint.get("ts")
                    }
                    for msg in messages
                ]
            return []
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def search_user_memories(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """Search user memories using native vector search"""
        try:
            results = await self.memory_integration.search_user_memories(user_id, query)
            return [
                {
                    "content": result.content,
                    "metadata": result.metadata,
                    "similarity_score": result.similarity_score,
                    "timestamp": result.timestamp.isoformat() if result.timestamp else None
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get native memory system statistics"""
        return self.memory_integration.get_stats()

# Example usage
async def main():
    """Example usage of native memory orchestrator"""
    logging.basicConfig(level=logging.INFO)
    
    # Create orchestrator with combined memory (buffer + vector)
    orchestrator = NativeMemoryOrchestrator(MemoryType.COMBINED)
    
    try:
        await orchestrator.initialize()
        
        # Test conversation
        user_id = "demo_user"
        thread_id = "demo_thread"
        
        messages = [
            "Hello, I need help with my e-commerce store",
            "I want to add new products to my inventory", 
            "How do I set up automated pricing?",
            "Can you help me with API integration?"
        ]
        
        for message in messages:
            print(f"\nUser: {message}")
            response = await orchestrator.process_message(message, user_id, thread_id)
            print(f"Assistant: {response}")
        
        # Test memory search
        print("\n--- Memory Search Results ---")
        search_results = await orchestrator.search_user_memories(
            user_id, "product management"
        )
        for i, result in enumerate(search_results[:3]):
            print(f"{i+1}. {result['content'][:100]}... (Score: {result['similarity_score']:.3f})")
        
        # Get statistics
        print("\n--- Memory Statistics ---")
        stats = orchestrator.get_memory_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
