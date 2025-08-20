"""
Simplified Compressed Context Manager - Lets LangExtract decide what's important
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import langextract as lx
import logging
import textwrap
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

@dataclass
class ExtractedContext:
    """Holds ALL extracted context from conversations - dynamically structured by LangExtract"""
    
    # Dynamic extraction storage - let LangExtract decide what's important
    # Key is extraction_class, value is list of extractions with that class
    extractions: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    
    # Chronological conversation record - preserves full exchange sequence
    conversation_chain: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata about what was extracted
    extraction_classes: List[str] = field(default_factory=list)  # List of all extraction classes found
    extraction_count: int = 0  # Total number of extractions
    
    # Source grounding - maps extractions to original message positions
    source_map: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    
    def to_context_string(self, max_tokens: int = 2000) -> str:
        """Convert to a comprehensive context string for the orchestrator"""
        parts = []
        
        # Show extraction summary
        if self.extraction_count > 0:
            parts.append(f"📊 Context: {self.extraction_count} items in {len(self.extraction_classes)} categories\n")
        
        # Add chronological conversation record FIRST (most important for continuity)
        if self.conversation_chain:
            parts.append("🔗 Conversation Chain:")
            # Show recent exchanges (last 10 to keep it manageable)
            recent_exchanges = self.conversation_chain[-10:] if len(self.conversation_chain) > 10 else self.conversation_chain
            for i, exchange in enumerate(recent_exchanges, 1):
                role = exchange.get('role', 'unknown')
                content = exchange.get('content', '')[:150]  # Truncate long messages
                timestamp = exchange.get('timestamp', '')
                
                # Format exchange with clear role indicators
                if role.lower() in ['user', 'human']:
                    parts.append(f"  {i}. 👤 User: {content}")
                elif role.lower() in ['assistant', 'ai']:
                    parts.append(f"  {i}. 🤖 Assistant: {content}")
                else:
                    parts.append(f"  {i}. {role}: {content}")
                    
                # Add any agent actions if available
                if exchange.get('agent_actions'):
                    actions = exchange['agent_actions']
                    parts.append(f"      → Actions: {', '.join(actions)}")
            parts.append("")  # Empty line after conversation chain
        
        # Then show extracted entities and facts
        for extraction_class in self.extraction_classes:
            if extraction_class not in self.extractions:
                continue
                
            items = self.extractions[extraction_class]
            if not items:
                continue
                
            # Format the class name nicely
            class_title = extraction_class.replace('_', ' ').title()
            parts.append(f"【{class_title}】")
            
            # Show items with their key attributes
            for item in items[:8]:  # Reduced from 10 to make room for conversation chain
                if isinstance(item, dict):
                    text = item.get('text', '')[:150]  # Reduced from 200
                    attrs = item.get('attributes', {})
                    
                    # Build a comprehensive line with all important attributes
                    line = f"  • {text}"
                    if attrs:
                        # Show key attributes
                        attr_parts = []
                        for k, v in list(attrs.items())[:5]:  # Limit to 5 most important
                            if v and str(v).strip():
                                # Format the value nicely
                                if isinstance(v, list):
                                    v = f"[{len(v)} items]"
                                elif isinstance(v, dict):
                                    v = f"[{len(v)} fields]"
                                elif len(str(v)) > 30:
                                    v = str(v)[:30] + "..."
                                attr_parts.append(f"{k}={v}")
                        if attr_parts:
                            line += f"\n    → {', '.join(attr_parts)}"
                    parts.append(line)
            parts.append("")  # Empty line between categories
        
        context = "\n".join(parts)
        
        # Only truncate if really necessary
        if len(context) > max_tokens * 4:  # Rough estimate: 1 token ~= 4 chars
            context = context[:max_tokens * 4] + "\n... [truncated]"
        
        return context
    
    def get_by_class(self, extraction_class: str) -> List[Dict[str, Any]]:
        """Get all extractions of a specific class"""
        return self.extractions.get(extraction_class, [])
    
    def has_info(self, extraction_class: str, attribute: str = None) -> bool:
        """Check if we have information of a specific type"""
        items = self.get_by_class(extraction_class)
        if not items:
            return False
        if attribute:
            # Check if any item has this attribute
            return any(item.get('attributes', {}).get(attribute) for item in items)
        return True


class CompressedContextManager:
    """Manages compressed context extraction using LangExtract with dynamic extraction"""
    
    def __init__(self, model_id: str = "gpt-4.1-mini", api_key: Optional[str] = None):
        self.model_id = model_id
        self.api_key = api_key
        self.contexts: Dict[str, ExtractedContext] = {}  # thread_id -> context
        
        # Dual-extraction prompt that creates both context and memory items
        self.extraction_prompt = textwrap.dedent("""
            Extract ALL important information from this conversation for both CONTEXT and MEMORY purposes.
            
            You MUST classify each extraction as either:
            1. CONTEXT_ONLY - Ephemeral/transactional data (orders, searches, specific tasks, time-bound info)
            2. MEMORY_WORTHY - Lasting information about the user, preferences, business rules, or permanent facts
            
            BE CREATIVE with extraction classes. Create specific, descriptive classes for everything you find.
            
            CLASSIFICATION RULES:
            
            MEMORY_WORTHY (save to long-term memory):
            - User identity: "User is a developer", "User works at Google"
            - User preferences: "User prefers Python over Java", "User always uses Docker"
            - Business context: "Store uses Shopify Plus", "Company policy is X"
            - Expertise areas: "User specializes in machine learning"
            - Lasting facts: "User's store sells coffee equipment"
            - Standards/policies: "User requires all prices in USD"
            
            CONTEXT_ONLY (don't save as memory):
            - Specific orders: "1x Loveramics Egg Cafe Latte Cup", "Order #12345"
            - Search results: "Found 5 espresso machines under $500"
            - Time-bound tasks: "Check today's sales", "This week's performance"
            - Specific product details: "Breville Bambino Plus costs $399"
            - Error messages: "API returned 404", "Connection failed"
            - Agent actions: "Searched for products", "Updated pricing"
            
            MEMORY FORMAT RULES - For MEMORY_WORTHY items only:
            - Always use third person format starting with "User" 
            - Convert "I am a developer" → "User is a developer"
            - Convert "I love Python" → "User loves Python" 
            - Convert "I always prefer X" → "User always prefers X"
            - Convert "My company is Netflix" → "User's company is Netflix"
            - NEVER save assistant responses as user memories
            
            CRITICAL: Add a 'memory_classification' attribute to EVERY extraction with value:
            - "MEMORY_WORTHY" - Will be saved to long-term memory database
            - "CONTEXT_ONLY" - Will only be used for conversation context
            
            Extract EVERYTHING that could be useful for understanding the conversation context.
            The goal is comprehensive information preservation with proper classification.
        """)
        
        # Examples showing dual classification with memory_classification attribute
        self.extraction_examples = [
            lx.data.ExampleData(
                text="User: I am a senior data scientist at Google and I always prefer PyTorch over TensorFlow",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="user_profile",
                        extraction_text="User is a senior data scientist at Google",
                        attributes={
                            "role": "senior data scientist",
                            "company": "Google",
                            "memory_classification": "MEMORY_WORTHY"
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="user_preference", 
                        extraction_text="User always prefers PyTorch over TensorFlow",
                        attributes={
                            "preferred": "PyTorch",
                            "not_preferred": "TensorFlow",
                            "domain": "machine learning frameworks",
                            "memory_classification": "MEMORY_WORTHY"
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="User: Show me espresso machines under $500\nAgent: Found 3 products: Breville Bambino Plus ($399), De'Longhi EC155 ($99.95), Gaggia Classic Pro ($449)\nUser: I'll take the Breville Bambino Plus",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="product_search_request",
                        extraction_text="Show me espresso machines under $500",
                        attributes={
                            "product_type": "espresso machines", 
                            "price_constraint": "under $500",
                            "action": "show",
                            "memory_classification": "CONTEXT_ONLY"
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="product_search_results",
                        extraction_text="Found 3 products: Breville Bambino Plus ($399), De'Longhi EC155 ($99.95), Gaggia Classic Pro ($449)",
                        attributes={
                            "count": "3",
                            "products": ["Breville Bambino Plus", "De'Longhi EC155", "Gaggia Classic Pro"],
                            "prices": ["$399", "$99.95", "$449"],
                            "memory_classification": "CONTEXT_ONLY"
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="product_purchase_decision",
                        extraction_text="I'll take the Breville Bambino Plus",
                        attributes={
                            "selected_product": "Breville Bambino Plus",
                            "price": "$399",
                            "decision": "purchase",
                            "memory_classification": "CONTEXT_ONLY"
                        }
                    )
                ]
            )
        ]
    
    def get_context(self, thread_id: str) -> ExtractedContext:
        """Get or create context for a thread"""
        if thread_id not in self.contexts:
            self.contexts[thread_id] = ExtractedContext()
        return self.contexts[thread_id]
    
    async def compress_turn(self, 
                           thread_id: str, 
                           messages: List[Any],
                           agent_results: Optional[Dict[str, str]] = None,
                           user_id: str = "1") -> ExtractedContext:
        """Compress a conversation turn into structured extractions AND record conversation chain"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting compression for thread {thread_id} with {len(messages)} messages")
        
        # Store user_id for memory saving
        self._current_user_id = user_id
        
        context = self.get_context(thread_id)
        
        # Record chronological conversation exchanges
        self._record_conversation_chain(context, messages, agent_results)
        
        # Convert messages to text for entity extraction
        text_parts = []
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                role = msg.__class__.__name__.replace("Message", "")
                text_parts.append(f"{role}: {msg.content}")
            elif isinstance(msg, dict):
                role = msg.get("type", "unknown")
                text_parts.append(f"{role}: {msg.get('content', '')}")
        
        # Add agent results if provided
        if agent_results:
            text_parts.append("\nAgent Results:")
            for agent, result in agent_results.items():
                text_parts.append(f"{agent}: {result[:1000]}")  # Include more of the result
        
        conversation_text = "\n".join(text_parts)
        
        try:
            # Extract using LangExtract
            logger.info(f"Extracting from {len(conversation_text)} chars of conversation")
            
            # Set up API key if needed
            if self.model_id.startswith("gpt") and not self.api_key:
                import os
                self.api_key = os.getenv("OPENAI_API_KEY")
            
            # Configure based on model type
            # OpenAI models need fence_output=True and use_schema_constraints=False
            is_openai = self.model_id.startswith("gpt") or "gpt-" in self.model_id
            
            try:
                result = lx.extract(
                    text_or_documents=conversation_text,
                    prompt_description=self.extraction_prompt,
                    examples=self.extraction_examples,
                    model_id=self.model_id,
                    api_key=self.api_key if is_openai else None,
                    fence_output=True,  # Always True for proper parsing
                    use_schema_constraints=False,  # Always False for OpenAI compatibility
                    temperature=0.1  # Low temperature for consistent output
                )
            except Exception as lx_error:
                logger.error(f"LangExtract extraction failed: {lx_error}")
                # Return empty context on failure rather than crashing
                return context
            
            logger.info(f"LangExtract found {len(result.extractions)} extractions")
            
            # Process each extraction
            for extraction in result.extractions:
                self._store_extraction(context, extraction)
            
            logger.info(f"Stored {context.extraction_count} total extractions in {len(context.extraction_classes)} classes")
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            # Continue with just conversation chain recording if LangExtract fails
            logger.info("Context compression failed, but conversation chain was recorded")
        
        return context
    
    def _record_conversation_chain(self, context: ExtractedContext, messages: List[Any], agent_results: Optional[Dict[str, str]] = None):
        """Record chronological conversation exchanges for context continuity"""
        from datetime import datetime
        
        # Process each message in chronological order
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                role = msg.__class__.__name__.replace("Message", "").lower()
                content = msg.content
                
                # Skip system messages from conversation chain (they're not exchanges)
                if role == "system":
                    continue
                
                # Create exchange record
                exchange = {
                    'role': role,
                    'content': content,
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'message'
                }
                
                # Add agent actions if this is an assistant message and we have agent results
                if role == 'ai' and agent_results:
                    exchange['agent_actions'] = list(agent_results.keys())
                
                context.conversation_chain.append(exchange)
                
            elif isinstance(msg, dict):
                role = msg.get("type", "unknown").lower()
                content = msg.get('content', '')
                
                if role != "system":  # Skip system messages
                    exchange = {
                        'role': role,
                        'content': content,
                        'timestamp': datetime.utcnow().isoformat(),
                        'type': 'message'
                    }
                    context.conversation_chain.append(exchange)
        
        # Trim conversation chain to prevent unbounded growth (keep last 50 exchanges)
        if len(context.conversation_chain) > 50:
            context.conversation_chain = context.conversation_chain[-50:]
        
        logger.debug(f"Recorded {len(messages)} messages in conversation chain (total: {len(context.conversation_chain)} exchanges)")
    
    def _store_extraction(self, context: ExtractedContext, extraction: lx.data.Extraction):
        """Store an extraction in the context and save as memory if relevant"""
        ext_class = extraction.extraction_class
        ext_text = extraction.extraction_text
        
        # Safely handle attributes - ensure it's a dict or None
        attrs = extraction.attributes
        if attrs is not None and not isinstance(attrs, dict):
            logger.warning(f"Invalid attributes type {type(attrs)} for extraction, converting to dict")
            try:
                # Try to convert to dict if it's a string (might be JSON)
                if isinstance(attrs, str):
                    import json
                    attrs = json.loads(attrs)
                else:
                    # Convert other types to string representation
                    attrs = {"value": str(attrs)}
            except:
                # Fallback to empty dict
                attrs = {}
        attrs = attrs or {}
        
        # Track extraction class
        if ext_class not in context.extraction_classes:
            context.extraction_classes.append(ext_class)
        
        # Initialize storage for this class if needed
        if ext_class not in context.extractions:
            context.extractions[ext_class] = []
        
        # Store the extraction with all its data
        extraction_data = {
            'text': ext_text,
            'attributes': attrs,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store source grounding if available
        if extraction.char_interval:
            source_key = f"{ext_class}:{len(context.extractions[ext_class])}"
            context.source_map[source_key] = (
                extraction.char_interval.start_pos,
                extraction.char_interval.end_pos
            )
        
        context.extractions[ext_class].append(extraction_data)
        context.extraction_count += 1
        
        # Note: Memory extraction happens separately via extract_memories_from_context()
        # This keeps context compression fast and memory saving as a separate process
        
        logger.debug(f"Stored: {ext_class} -> {ext_text[:50]}... with {len(attrs)} attributes")
    
    async def extract_memories_from_context(self, thread_id: str, user_id: str = "1") -> int:
        """Extract and save memories from compressed context as a separate process"""
        context = self.get_context(thread_id)
        if not context or context.extraction_count == 0:
            logger.info(f"No context found for thread {thread_id}")
            return 0
        
        memories_saved = 0
        
        # Process all extractions and save MEMORY_WORTHY ones
        for ext_class in context.extraction_classes:
            items = context.extractions.get(ext_class, [])
            
            for item in items:
                ext_text = item.get('text', '')
                attrs = item.get('attributes', {})
                
                if self._should_save_as_memory(ext_class, ext_text, attrs):
                    memory_saved = await self._save_memory_direct(ext_class, ext_text, attrs, user_id)
                    if memory_saved:
                        memories_saved += 1
        
        logger.info(f"💾 Extracted {memories_saved} memories from context for thread {thread_id}")
        return memories_saved
    
    def _should_save_as_memory(self, ext_class: str, ext_text: str, attrs: dict) -> bool:
        """Determine if an extraction should be saved as memory"""
        
        # Check LangExtract classification first
        memory_classification = attrs.get('memory_classification', '').upper()
        
        if memory_classification == 'CONTEXT_ONLY':
            return False
        
        if memory_classification == 'MEMORY_WORTHY':
            # Additional quality checks for memory-worthy items
            
            # Skip if too short or not informative
            if len(ext_text.strip()) < 10:
                logger.debug(f"❌ Skipped memory (too short): {ext_text[:50]}...")
                return False
            
            # Skip if it's just a generic response
            if ext_text.lower().startswith(("yes", "no", "ok", "sure", "thanks")):
                logger.debug(f"❌ Skipped memory (generic): {ext_text[:50]}...")
                return False
            
            # Skip transactional content that slipped through
            if any(pattern in ext_text.lower() for pattern in [
                "1x ", "2x ", "order #", "found ", "results:", "search for",
                "today's ", "this week", "currently ", "right now"
            ]):
                logger.warning(f"⚠️ Transactional content marked as MEMORY_WORTHY: {ext_text[:50]}...")
                return False
            
            return True
        
        # Fallback: No classification provided, use heuristic logic
        logger.debug(f"⚠️ No memory_classification found for: {ext_text[:50]}..., using heuristics")
        
        memory_worthy_classes = {
            "user_profile", "user_role", "user_identity", "user_profession", "user_expertise",
            "user_preference", "tool_preference", "workflow_preference", "business_context",
            "industry_info", "platform_info", "technical_expertise", "skill_area", 
            "specialization", "policy", "standard", "guideline", "rule", "process"
        }
        
        lasting_indicators = [
            "always", "prefer", "usually", "typically", "standard",
            "policy", "rule", "never", "love", "hate", "specialize",
            "expert", "senior", "work with", "use for", "company"
        ]
        
        should_save = (ext_class in memory_worthy_classes or 
                      any(indicator in ext_text.lower() for indicator in lasting_indicators))
        
        return should_save and len(ext_text.strip()) >= 10
    
    async def _save_memory_direct(self, ext_class: str, ext_text: str, attrs: dict, user_id: str) -> bool:
        """Save extraction as memory directly (not async background task)"""
        try:
            from ..memory.postgres_memory_manager_v2 import SimpleMemoryManager, Memory
            
            # Extract confidence score from attributes or calculate default
            confidence_score = self._extract_confidence_score(attrs)
            
            # Create memory object
            memory = Memory(
                user_id=user_id,
                content=ext_text,
                category=self._map_extraction_to_memory_category(ext_class),
                importance_score=self._calculate_importance(ext_class, attrs, confidence_score),
                metadata={
                    "extraction_class": ext_class,
                    "extraction_method": "context_compression",
                    "reason": "dual_extraction_process",
                    "attributes": attrs,
                    "model": self.model_id,
                    "confidence": confidence_score
                }
            )
            
            # Save memory
            from ..memory.shared_manager import get_shared_memory_manager
            manager = await get_shared_memory_manager()
            memory_id = await manager.store_memory(memory)
            
            if memory_id:
                logger.info(f"💾 Saved memory {memory_id}: {ext_text[:60]}...")
                return True
            else:
                logger.error(f"Failed to save memory: {ext_text[:60]}...")
                return False
                
        except Exception as e:
            logger.error(f"Memory save error: {e}")
            return False
    
    # Removed _save_memory_async - now using direct memory extraction process
    
    def _map_extraction_to_memory_category(self, ext_class: str) -> str:
        """Map extraction class to memory category"""
        category_mapping = {
            "user_preference": "preferences",
            "user_profile": "facts",
            "user_role": "facts", 
            "user_identity": "facts",
            "business_context": "general",
            "technical_expertise": "expertise",
            "policy": "preferences",
            "standard": "preferences",
            "tool_preference": "preferences",
            "workflow_preference": "preferences"
        }
        
        # Default mapping based on keywords
        if "preference" in ext_class:
            return "preferences"
        elif "user" in ext_class or "profile" in ext_class:
            return "facts"
        elif "business" in ext_class or "company" in ext_class:
            return "general"
        elif "technical" in ext_class or "skill" in ext_class:
            return "expertise"
        else:
            return "general"
    
    def _calculate_importance(self, ext_class: str, attrs: dict, confidence_score: float = 0.5) -> float:
        """Calculate importance score for memory"""
        base_score = 0.5
        
        # Higher importance for certain classes
        if ext_class in ["user_profile", "user_role", "technical_expertise"]:
            base_score = 0.8
        elif "preference" in ext_class:
            base_score = 0.7
        elif ext_class in ["business_context", "policy"]:
            base_score = 0.6
        
        # Boost based on confidence score
        base_score = (base_score + confidence_score) / 2.0
        
        # Additional boost based on attributes
        if attrs.get("confidence"):
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _extract_confidence_score(self, attrs: dict) -> float:
        """Extract or calculate confidence score for memory"""
        
        # Check if LangExtract provided a confidence score
        if attrs.get("confidence"):
            try:
                return float(attrs["confidence"])
            except (ValueError, TypeError):
                pass
        
        # Calculate confidence based on extraction attributes and content quality
        base_confidence = 0.7  # Default confidence
        
        # Boost confidence for detailed extractions
        if len(attrs) > 3:  # Rich attributes suggest higher confidence
            base_confidence += 0.1
            
        # Boost for specific attribute types that indicate certainty
        if attrs.get("role") or attrs.get("company"):  # Professional info
            base_confidence += 0.1
        if attrs.get("preferred") and attrs.get("not_preferred"):  # Clear preferences
            base_confidence += 0.1
        if attrs.get("domain"):  # Specific domain knowledge
            base_confidence += 0.05
            
        # Reduce confidence for vague extractions
        if not attrs or len(attrs) <= 1:
            base_confidence -= 0.1
            
        return min(max(base_confidence, 0.1), 1.0)  # Keep between 0.1 and 1.0
    
    def clear_old_context(self, thread_id: str):
        """Clear old context to prevent unbounded growth"""
        if thread_id in self.contexts:
            context = self.contexts[thread_id]
            # Keep only recent extractions per class
            for ext_class in context.extractions:
                if len(context.extractions[ext_class]) > 20:
                    context.extractions[ext_class] = context.extractions[ext_class][-20:]