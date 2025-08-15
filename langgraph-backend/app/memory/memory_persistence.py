"""Memory Persistence Node for LangGraph Integration"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import langextract as lx

from ..state.graph_state import GraphState
from .postgres_memory_manager_v2 import SimpleMemoryManager, Memory
from .prompt_assembler import PromptAssembler, ContextTier
from .embedding_service import get_embedding_service
from .memory_decay_service import get_decay_service

logger = logging.getLogger(__name__)

# Memory extraction schema for langextract
class MemoryCategory(str, Enum):
    PREFERENCES = "preferences"
    FACTS = "facts"
    PROBLEMS = "problems"
    SOLUTIONS = "solutions"
    RELATIONSHIPS = "relationships"
    EXPERTISE = "expertise"
    GENERAL = "general"

@dataclass
class ExtractedMemory:
    """Structured memory extraction using langextract"""
    content: str  # The specific memory content
    category: MemoryCategory  # Category of memory
    importance: float  # Importance score 0.1-1.0
    confidence: float  # Extraction confidence 0.1-1.0
    reasoning: str  # Why this memory has long-term value
    is_ephemeral: bool = False  # Whether this is temporary/task-specific

class MemoryExtractionService:
    """Service for extracting memories from conversations"""
    
    def __init__(self):
        self.openai_client = None
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client lazily"""
        try:
            import openai
            import os
            self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    
    async def extract_memories_from_conversation(self, messages: List[BaseMessage], 
                                               user_id: str) -> List[Memory]:
        """Extract meaningful memories from conversation messages"""
        
        # Get recent messages for extraction
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        
        # Format messages for analysis
        conversation_text = self._format_messages_for_extraction(recent_messages)
        
        if not conversation_text.strip():
            return []
        
        # Try langextract first, fall back to GPT if it fails
        try:
            logger.info("Attempting memory extraction with langextract...")
            memories = await self._extract_memories_langextract(conversation_text, user_id)
            if memories:
                logger.info(f"Successfully extracted {len(memories)} memories with langextract")
                return memories
            else:
                logger.warning("Langextract returned no memories, falling back to GPT")
        except Exception as e:
            logger.warning(f"Langextract extraction failed: {e}, falling back to GPT")
        
        # Fallback to direct GPT extraction
        return await self._extract_memories_gpt(conversation_text, user_id)
    
    async def _extract_memories_langextract(self, conversation_text: str, user_id: str) -> List[Memory]:
        """Experimental langextract-based extraction (kept for future improvement)"""
        # Use langextract for structured extraction
        try:
            # Define extraction examples using lx.data.Extraction format
            examples = [
                lx.data.ExampleData(
                    text="User: My name is John and I love Italian coffee\nAssistant: Nice to meet you John! Italian coffee is excellent.",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="user_fact",
                            extraction_text="My name is John",
                            attributes={
                                "content": "User's name is John",
                                "category": "facts",
                                "importance": 0.8,
                                "confidence": 1.0,
                                "reasoning": "Core identity information needed for personalization",
                                "is_ephemeral": False
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="user_preference",
                            extraction_text="I love Italian coffee",
                            attributes={
                                "content": "User loves Italian coffee",
                                "category": "preferences",
                                "importance": 0.9,
                                "confidence": 1.0,
                                "reasoning": "Specific preference that guides recommendations",
                                "is_ephemeral": False
                            }
                        )
                    ]
                ),
                lx.data.ExampleData(
                    text="User: Can you check today's sales report?\nAssistant: I'll check today's sales for you.",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="ephemeral_task",
                            extraction_text="check today's sales report",
                            attributes={
                                "content": "User requested today's sales report",
                                "category": "general",
                                "importance": 0.2,
                                "confidence": 0.8,
                                "reasoning": "One-time task request",
                                "is_ephemeral": True
                            }
                        )
                    ]
                ),
                lx.data.ExampleData(
                    text="User: I work at Google as a senior backend engineer. We use Python and Go exclusively.\nAssistant: That's great experience!",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="user_fact",
                            extraction_text="I work at Google as a senior backend engineer",
                            attributes={
                                "content": "User is a senior backend engineer at Google",
                                "category": "facts",
                                "importance": 0.95,
                                "confidence": 0.95,
                                "reasoning": "Professional identity affects all technical discussions",
                                "is_ephemeral": False
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="user_expertise",
                            extraction_text="We use Python and Go exclusively",
                            attributes={
                                "content": "User's team uses Python and Go exclusively",
                                "category": "expertise",
                                "importance": 0.85,
                                "confidence": 0.9,
                                "reasoning": "Technology stack preference for solutions",
                                "is_ephemeral": False
                            }
                        )
                    ]
                )
            ]
            
            # Extract memories using langextract with proper parameters
            prompt_description = """Extract ONLY high-value, long-term memories that will be useful in future interactions.
                
                Focus on:
                - Personal preferences that persist
                - Important facts about the user
                - Recurring problems or pain points  
                - Business relationships and context
                - User's expertise areas
                
                Skip ephemeral items like:
                - One-time tasks or requests
                - Temporary states
                - Time-specific data
                - Conversation mechanics
                
                Mark is_ephemeral=True for temporary items (they will be filtered out).
                Each memory should be self-contained and specific."""
            
            # Call langextract with OpenAI model
            import os
            from langextract.inference import OpenAILanguageModel
            
            result = lx.extract(
                text_or_documents=conversation_text,
                prompt_description=prompt_description,
                examples=examples,
                model_id="gpt-4.1-mini",  # Use gpt-4.1-mini which works in context compression
                api_key=os.getenv("OPENAI_API_KEY"),
                language_model_type=OpenAILanguageModel,
                use_schema_constraints=True,
                temperature=0.3,  # Lower temperature for more consistent extraction
                debug=False  # Disable debug for cleaner logs
            )
            
            # Handle case where result might be wrapped in markdown code blocks
            if isinstance(result, str):
                # Strip markdown code blocks if present
                import re
                import json
                
                # Remove markdown code block wrapper
                clean_json = re.sub(r'^```json\s*', '', result, flags=re.MULTILINE)
                clean_json = re.sub(r'\s*```$', '', clean_json, flags=re.MULTILINE)
                
                try:
                    result_data = json.loads(clean_json)
                    # Create a mock result object with extractions
                    class MockResult:
                        def __init__(self, data):
                            self.extractions = []
                            if 'extractions' in data:
                                for ext in data['extractions']:
                                    extraction = lx.data.Extraction(
                                        extraction_class=list(ext.keys())[0] if ext else "unknown",
                                        extraction_text=ext.get(list(ext.keys())[0], "") if ext else "",
                                        attributes=ext.get(f"{list(ext.keys())[0]}_attributes", {}) if ext else {}
                                    )
                                    self.extractions.append(extraction)
                    
                    result = MockResult(result_data)
                    logger.debug(f"Parsed markdown-wrapped JSON result with {len(result.extractions)} extractions")
                except Exception as e:
                    logger.warning(f"Failed to parse markdown-wrapped result: {e}")
                    # Continue with original result
            
            # Convert to Memory objects with quality filtering
            memories = []
            filtered_count = 0
            
            # Result is an AnnotatedDocument with extractions
            if result and hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    attrs = extraction.attributes or {}
                    
                    # Skip ephemeral memories
                    if attrs.get("is_ephemeral", False):
                        filtered_count += 1
                        logger.debug(f"Filtered ephemeral memory: {attrs.get('content', '')[:50]}...")
                        continue
                    
                    # Skip low confidence memories
                    confidence = float(attrs.get("confidence", 0.5))
                    if confidence < 0.3:
                        filtered_count += 1
                        logger.debug(f"Filtered low confidence ({confidence}) memory: {attrs.get('content', '')[:50]}...")
                        continue
                    
                    # Build metadata
                    metadata = {
                        "confidence": confidence,
                        "reasoning": attrs.get("reasoning", ""),
                        "extraction_version": "v3_langextract",
                        "extraction_method": "langextract",
                        "extraction_class": extraction.extraction_class,
                        "source_text": extraction.extraction_text[:100] if extraction.extraction_text else ""
                    }
                    
                    memory = Memory(
                        user_id=user_id,
                        content=attrs.get("content", ""),
                        category=attrs.get("category", "general"),
                        importance_score=float(attrs.get("importance", 0.5)),
                        metadata=metadata
                    )
                    memories.append(memory)
                    logger.info(f"📝 Extracted memory: '{memory.content}' (category: {memory.category}, importance: {memory.importance_score}, confidence: {confidence})")
            
            logger.info(f"Extracted {len(memories)} high-quality memories from conversation (filtered {filtered_count} ephemeral/low-confidence)")
            if filtered_count > 0:
                logger.info(f"Memory quality filter: {len(memories)} kept, {filtered_count} filtered ({filtered_count/(len(memories)+filtered_count)*100:.1f}% filtered)")
            
            return memories
            
        except Exception as e:
            logger.error(f"Langextract memory extraction failed: {e}, falling back to GPT-4.1-nano")
            # Fall back to original extraction method
            return await self._extract_memories_gpt(conversation_text, user_id)
    
    async def _extract_memories_gpt(self, conversation_text: str, user_id: str) -> List[Memory]:
        """GPT-4.1-nano extraction method (primary method)"""
        
        if not self.openai_client:
            return []
        
        # ORIGINAL EXTRACTION CODE - KEPT AS FALLBACK
        extraction_prompt = f"""
Analyze this conversation and extract ONLY high-value, long-term memories that will be useful in future interactions.

EXTRACT memories that are:
✓ Personal preferences that will persist (e.g., "I prefer dark roast coffee", "I like detailed explanations")
✓ Important facts about the user (e.g., "I work at Google", "I have two kids", "I'm based in Toronto")
✓ Recurring problems or pain points (e.g., "I always struggle with Python async", "My team needs better documentation")
✓ Learned solutions that could apply again (e.g., "Using Redis solved our caching issues")
✓ Business relationships and context (e.g., "I manage the DevOps team", "We use AWS exclusively")
✓ User's expertise or knowledge areas (e.g., "I'm experienced with React", "I'm new to machine learning")

DO NOT EXTRACT ephemeral memories like:
✗ One-time tasks or requests (e.g., "check today's sales", "run this command")
✗ Temporary states (e.g., "currently looking at...", "just finished...")  
✗ Action descriptions (e.g., "user reviewed emails", "user requested analysis")
✗ Time-specific data (e.g., "today's performance", "this week's metrics")
✗ Conversation mechanics (e.g., "user thanked assistant", "user asked for help")

Conversation:
{conversation_text}

Return a JSON object with a "memories" array. For each memory provide:
- "content": The specific memory (be precise and complete, e.g., "User prefers Python over JavaScript for backend development")
- "category": One of: "preferences", "facts", "problems", "solutions", "relationships", "expertise", "general"
- "importance": 0.1-1.0 based on long-term value (preferences/facts: 0.7-1.0, problems: 0.5-0.8, general: 0.3-0.6)
- "is_ephemeral": true if this is task/time-specific (these will be filtered out)
- "confidence": 0.1-1.0 indicating extraction confidence
- "reasoning": Brief explanation of why this memory has long-term value
- "metadata": Additional context (optional)

Quality Guidelines:
- Each memory should be self-contained and understandable without conversation context
- Prefer specific over generic (e.g., "Uses VS Code with Python extension" not "Uses an IDE")
- Combine related facts into single memories when appropriate
- Focus on information that would change how the assistant interacts with the user

Example:
{{
    "memories": [
        {{
            "content": "User is a senior backend engineer at Google working primarily with Python and Go",
            "category": "facts",
            "importance": 0.9,
            "is_ephemeral": false,
            "confidence": 0.95,
            "reasoning": "Core professional identity that affects technical discussions",
            "metadata": {{"topics": ["career", "expertise"]}}
        }},
        {{
            "content": "User prefers concise, code-focused explanations over lengthy theoretical discussions",
            "category": "preferences",
            "importance": 0.8,
            "is_ephemeral": false,
            "confidence": 0.85,
            "reasoning": "Communication style preference that should guide all responses",
            "metadata": {{"topics": ["communication"]}}
        }}
    ]
}}

Return {{"memories": []}} if no high-value, long-term memories are found.
"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1-nano",  # Use gpt-4o-mini instead of gpt-5-mini
                messages=[{"role": "user", "content": extraction_prompt}],
                max_completion_tokens=1500,
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            import json
            response_content = response.choices[0].message.content
            logger.debug(f"Raw extraction response: {response_content[:200]}...")
            
            # Handle case where model returns array directly or wrapped in object
            extracted_data = json.loads(response_content)
            
            # If response is wrapped in an object like {"memories": [...]}
            if isinstance(extracted_data, dict):
                extracted_data = extracted_data.get("memories", extracted_data.get("items", []))
            
            # Ensure we have a list
            if not isinstance(extracted_data, list):
                logger.warning(f"Unexpected extraction format: {type(extracted_data)}")
                extracted_data = []
            
            # Convert to Memory objects with quality filtering
            memories = []
            filtered_count = 0
            for item in extracted_data:
                if not isinstance(item, dict):
                    continue
                
                # Skip ephemeral memories
                if item.get("is_ephemeral", False):
                    filtered_count += 1
                    logger.debug(f"Filtered ephemeral memory: {item.get('content', '')[:50]}...")
                    continue
                
                # Skip low confidence memories
                confidence = item.get("confidence", 0.5)
                if confidence < 0.3:
                    filtered_count += 1
                    logger.debug(f"Filtered low confidence ({confidence}) memory: {item.get('content', '')[:50]}...")
                    continue
                
                # Build metadata including new fields
                metadata = item.get("metadata", {})
                metadata["confidence"] = confidence
                metadata["reasoning"] = item.get("reasoning", "")
                metadata["extraction_version"] = "v2_quality_focused"
                
                memory = Memory(
                    user_id=user_id,
                    content=item.get("content", ""),
                    category=item.get("category", "general"),
                    importance_score=item.get("importance", 0.5),
                    metadata=metadata
                )
                memories.append(memory)
                # Log each extracted memory for visibility
                logger.info(f"📝 Extracted memory: '{memory.content}' (category: {memory.category}, importance: {memory.importance_score}, confidence: {confidence})")
            
            logger.info(f"Extracted {len(memories)} high-quality memories from conversation (filtered {filtered_count} ephemeral/low-confidence)")
            if filtered_count > 0:
                logger.info(f"Memory quality filter: {len(memories)} kept, {filtered_count} filtered ({filtered_count/(len(memories)+filtered_count)*100:.1f}% filtered)")
            return memories
            
        except json.JSONDecodeError as e:
            logger.error(f"Memory extraction JSON parsing failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []
    
    def _format_messages_for_extraction(self, messages: List[BaseMessage]) -> str:
        """Format messages for memory extraction"""
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Extract main content, skip tool calls
                content = msg.content
                if content and content.strip():
                    formatted.append(f"Assistant: {content}")
        
        return "\n".join(formatted)

class MemoryPersistenceNode:
    """Memory persistence node for LangGraph workflow"""
    
    def __init__(self, database_url: Optional[str] = None):
        from .shared_manager import get_shared_memory_manager
        self.memory_manager = None  # Will be set in initialize
        self.prompt_assembler = None  # Will be set in initialize
        self.extraction_service = MemoryExtractionService()
        self.embedding_service = get_embedding_service()
        self.decay_service = None  # Will be set in initialize
        self._initialized = False
        self._conversation_memories = {}  # Track memories used per conversation
        self._get_shared_manager = get_shared_memory_manager
    
    async def initialize(self):
        """Initialize the memory system"""
        if not self._initialized:
            self.memory_manager = await self._get_shared_manager()
            self.prompt_assembler = PromptAssembler(self.memory_manager)
            self.decay_service = get_decay_service(self.memory_manager)
            self._initialized = True
            logger.info("Memory persistence node initialized with shared manager")
    
    async def close(self):
        """Close resources"""
        if self._initialized:
            # Don't close the shared manager, just mark as uninitialized
            self._initialized = False
    
    async def load_memory_context(self, state: GraphState) -> GraphState:
        """Load relevant memory context for the conversation"""
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get current message to search for relevant memories
            current_message = state["messages"][-1] if state["messages"] else None
            if not current_message or not isinstance(current_message, HumanMessage):
                return state
            
            user_id = state.get("user_id")
            if not user_id:
                logger.warning("No user_id provided for memory context loading")
                return state
            
            query = current_message.content
            current_agent = state.get("current_agent", "general")
            
            # Determine context tier based on query complexity
            context_tier = self._determine_context_tier(query, state)
            
            # Assemble intelligent prompt with memory context
            assembled_prompt = await self.prompt_assembler.assemble_prompt(
                user_query=query,
                user_id=user_id,
                agent_type=current_agent,
                context_tier=context_tier,
                conversation_context=self._extract_conversation_context(state)
            )
            
            # Update state with memory context
            state["memory_context"] = [
                {
                    "id": mem.id,
                    "content": mem.content,
                    "category": mem.category,
                    "importance": mem.importance_score,
                    "similarity": getattr(mem, 'similarity_score', None)
                }
                for mem in assembled_prompt.relevant_memories
            ]
            
            state["prompt_fragments"] = [
                {
                    "category": frag.category,
                    "content": frag.content,
                    "priority": frag.priority,
                    "agent_type": frag.agent_type
                }
                for frag in assembled_prompt.prompt_fragments
            ]
            
            state["context_tier"] = context_tier.value
            state["memory_search_query"] = query
            state["consolidated_context"] = assembled_prompt.consolidation_applied
            
            # Update system context with assembled prompt
            if "context" not in state:
                state["context"] = {}
            
            state["context"]["memory_summary"] = assembled_prompt.context_summary
            state["context"]["system_prompt_enhancement"] = assembled_prompt.system_prompt
            state["context"]["memory_count"] = len(assembled_prompt.relevant_memories)
            state["context"]["fragment_count"] = len(assembled_prompt.prompt_fragments)
            
            # Store memories for later tracking
            conversation_id = state.get("conversation_id", str(datetime.utcnow()))
            self._conversation_memories[conversation_id] = assembled_prompt.relevant_memories
            
            logger.info(f"Loaded memory context: {len(assembled_prompt.relevant_memories)} memories, "
                       f"{len(assembled_prompt.prompt_fragments)} fragments, tier: {context_tier.value}")
            
        except Exception as e:
            logger.error(f"Failed to load memory context: {e}")
            # Continue without memory context rather than fail
        
        return state
    
    async def persist_conversation_memories(self, state: GraphState) -> GraphState:
        """Extract and persist memories from the conversation"""
        
        if not self._initialized:
            await self.initialize()
        
        try:
            user_id = state.get("user_id")
            if not user_id:
                return state
            
            messages = state.get("messages", [])
            if len(messages) < 2:  # Need at least user message and response
                return state
            
            # Extract memories from conversation
            new_memories = await self.extraction_service.extract_memories_from_conversation(
                messages, user_id
            )
            
            # Store memories sequentially to avoid connection conflicts
            stored_count = 0
            for memory in new_memories:
                try:
                    memory_id = await self.memory_manager.store_memory(memory)
                    if memory_id:
                        stored_count += 1
                    # Small delay between stores to prevent connection issues
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"Failed to store memory: {e}")
            
            # Update metadata
            if "metadata" not in state:
                state["metadata"] = {}
            
            state["metadata"]["memories_extracted"] = len(new_memories)
            state["metadata"]["memories_stored"] = stored_count
            
            if stored_count > 0:
                logger.info(f"Persisted {stored_count} memories from conversation")
            
        except Exception as e:
            logger.error(f"Failed to persist conversation memories: {e}")
        
        return state
    
    def _determine_context_tier(self, query: str, state: GraphState) -> ContextTier:
        """Determine appropriate context tier based on query complexity"""
        
        query_lower = query.lower()
        
        # Complex queries that need full context
        complex_indicators = [
            "analyze", "compare", "detailed", "comprehensive", "explain why",
            "what are all", "give me everything", "full report", "in depth"
        ]
        
        # Simple queries that need minimal context
        simple_indicators = [
            "what is", "who is", "when", "where", "yes", "no", "thanks",
            "hello", "hi", "ok", "sure", "help"
        ]
        
        if any(indicator in query_lower for indicator in complex_indicators):
            return ContextTier.FULL
        elif any(indicator in query_lower for indicator in simple_indicators):
            return ContextTier.CORE
        elif len(query.split()) > 20:  # Long queries get more context
            return ContextTier.FULL
        else:
            return ContextTier.STANDARD
    
    def _extract_conversation_context(self, state: GraphState) -> List[Dict]:
        """Extract conversation context from state"""
        messages = state.get("messages", [])
        context = []
        
        for msg in messages[-5:]:  # Last 5 messages
            context.append({
                "role": msg.type,
                "content": msg.content[:200] if len(msg.content) > 200 else msg.content,
                "timestamp": getattr(msg, 'timestamp', None)
            })
        
        return context
    
    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for a user"""
        if not self._initialized:
            await self.initialize()
        
        try:
            stats = await self.memory_manager.get_user_memory_stats(user_id)
            performance = self.memory_manager.get_performance_stats()
            
            return {
                **stats,
                "performance": performance
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}
    
    async def track_memory_usage(self, state: GraphState) -> GraphState:
        """Track which memories were useful after agent response"""
        
        if not self._initialized:
            await self.initialize()
        
        try:
            conversation_id = state.get("conversation_id", str(datetime.utcnow()))
            
            # Get memories that were provided for this conversation
            provided_memories = self._conversation_memories.get(conversation_id, [])
            
            if not provided_memories:
                return state
            
            # Get the last AI message (agent response)
            messages = state.get("messages", [])
            agent_response = None
            user_message = None
            
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and not agent_response:
                    agent_response = msg.content
                elif isinstance(msg, HumanMessage) and not user_message:
                    user_message = msg.content
                
                if agent_response and user_message:
                    break
            
            if agent_response:
                # Track memory usage
                analytics = await self.decay_service.track_memory_usage(
                    conversation_id=conversation_id,
                    memories_provided=provided_memories,
                    agent_response=agent_response,
                    user_message=user_message
                )
                
                # Store analytics in state
                if "metadata" not in state:
                    state["metadata"] = {}
                
                state["metadata"]["memory_usage_analytics"] = analytics
                
                logger.info(f"📊 Memory usage: {analytics['memories_used']}/{analytics['total_memories_provided']} "
                          f"({analytics['usage_rate']*100:.1f}% usage rate)")
            
            # Clean up tracked memories
            if conversation_id in self._conversation_memories:
                del self._conversation_memories[conversation_id]
        
        except Exception as e:
            logger.error(f"Failed to track memory usage: {e}")
        
        return state
    
    async def search_user_memories(self, user_id: str, query: str, 
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """Search user memories"""
        if not self._initialized:
            await self.initialize()
        
        try:
            results = await self.memory_manager.search_memories(
                user_id=user_id,
                query=query,
                limit=limit
            )
            
            return [
                {
                    "content": result.memory.content,
                    "category": result.memory.category,
                    "similarity_score": result.similarity_score,
                    "importance": result.memory.importance_score,
                    "created_at": result.memory.created_at.isoformat() if result.memory.created_at else None
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

# Global instance for graph integration
_memory_node_instance: Optional[MemoryPersistenceNode] = None

def get_memory_node(database_url: Optional[str] = None) -> MemoryPersistenceNode:
    """Get singleton memory persistence node"""
    global _memory_node_instance
    if _memory_node_instance is None:
        _memory_node_instance = MemoryPersistenceNode(database_url)
    return _memory_node_instance