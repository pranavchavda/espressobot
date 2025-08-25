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
    
    # Chronological conversation record - preserves exchange sequence in compressed format
    # Format: {"message_1": {"human": "compressed_msg", "assistant": "compressed_response"}, "message_2": {...}}
    conversation_chain: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
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
            # Show recent exchanges in chronological order
            recent_exchanges = sorted(self.conversation_chain.items(), key=lambda x: int(x[0].split('_')[1]))[-10:]
            
            for message_key, exchange in recent_exchanges:
                message_num = message_key.split('_')[1]
                
                # Show human message if present
                if 'human' in exchange:
                    human_msg = exchange['human'][:200]  # Limit but keep more than before
                    parts.append(f"  {message_num}. 👤 User: {human_msg}")
                
                # Show assistant message if present
                if 'assistant' in exchange:
                    assistant_msg = exchange['assistant'][:200]
                    parts.append(f"  {message_num}. 🤖 Assistant: {assistant_msg}")
                    
                    # Add agent information if available
                    if exchange.get('agents_called'):
                        parts.append(f"      → Agents: {', '.join(exchange['agents_called'])}")
                    
                    # Add extracted data summary if available
                    if exchange.get('agent_data'):
                        for agent, data in exchange['agent_data'].items():
                            if data.get('product_ids'):
                                parts.append(f"      → {agent} found: {len(data['product_ids'])} products")
                            if data.get('variant_ids'):
                                parts.append(f"      → {agent} found: {len(data['variant_ids'])} variants")
                            if data.get('skus'):
                                parts.append(f"      → {agent} found: {', '.join(data['skus'][:2])}")
            
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
        
        # Initialize compression LLM for message compression
        from app.config.llm_factory import LLMFactory
        llm_factory = LLMFactory()
        self.compress_llm = llm_factory.create_llm("openai/gpt-4o-mini")  # Fast compression
        
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
    
    async def _compress_message(self, role: str, content: str) -> str:
        """Compress a message to its essential information while preserving ALL data"""
        
        # Skip compression for very short messages
        if len(content) < 100:
            return content
        
        try:
            compression_prompt = f"""Compress this {role} message to its essential information.
KEEP ALL: IDs, SKUs, prices, numbers, names, errors, decisions, specific data
REMOVE: Pleasantries, repetition, filler words, excessive politeness

Original: {content}

Compressed (preserve ALL data, remove fluff):"""
            
            compressed_response = await self.compress_llm.ainvoke(compression_prompt)
            compressed = compressed_response.content.strip()
            
            # Ensure compression actually saved space, otherwise keep original
            if len(compressed) < len(content) * 0.8:  # At least 20% reduction
                return compressed
            else:
                return content[:300] + "..." if len(content) > 300 else content
                
        except Exception as e:
            logger.warning(f"Message compression failed: {e}")
            # Fallback to simple truncation
            return content[:300] + "..." if len(content) > 300 else content
    
    def _extract_key_data(self, agent_result: str) -> Dict[str, Any]:
        """Extract structured data from agent response"""
        extracted = {
            "product_ids": [],
            "variant_ids": [],
            "skus": [],
            "prices": [],
            "errors": [],
            "actions": []
        }
        
        import re
        
        # Extract product IDs
        product_ids = re.findall(r'gid://shopify/Product/\d+', agent_result)
        extracted["product_ids"] = list(set(product_ids))  # Remove duplicates
        
        # Extract variant IDs
        variant_ids = re.findall(r'gid://shopify/ProductVariant/\d+', agent_result)
        extracted["variant_ids"] = list(set(variant_ids))
        
        # Extract SKUs (patterns like OB-2507-K58-MIL-CM7750)
        sku_patterns = [
            r'[A-Z]{2,3}-\d{4}-[A-Z0-9-]{5,20}',  # OB-XXXX pattern
            r'[A-Z]{3,}-[A-Z0-9-]{5,15}',         # General SKU pattern
        ]
        for pattern in sku_patterns:
            skus = re.findall(pattern, agent_result)
            extracted["skus"].extend(skus)
        extracted["skus"] = list(set(extracted["skus"]))  # Remove duplicates
        
        # Extract prices ($4499.00, 4450, etc.)
        price_patterns = [
            r'\$[\d,]+\.?\d*',  # $4499.00
            r'\b\d{3,6}\.?\d{0,2}\b(?=\s*(?:USD|dollars?|price|cost))',  # 4450 when followed by currency/price words
        ]
        for pattern in price_patterns:
            prices = re.findall(pattern, agent_result)
            extracted["prices"].extend(prices)
        extracted["prices"] = list(set(extracted["prices"][:5]))  # Keep first 5 unique prices
        
        # Extract error messages
        error_patterns = [
            r'Error: [^.!?\n]+[.!?]?',
            r'Failed [^.!?\n]+[.!?]?',
            r'Cannot [^.!?\n]+[.!?]?',
        ]
        for pattern in error_patterns:
            errors = re.findall(pattern, agent_result, re.IGNORECASE)
            extracted["errors"].extend(errors)
        
        # Extract actions/verbs
        action_words = ['found', 'created', 'updated', 'deleted', 'searched', 'retrieved', 'processed']
        for word in action_words:
            if word in agent_result.lower():
                extracted["actions"].append(word)
        
        return extracted
    
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
        await self._record_conversation_chain(context, messages, agent_results)
        
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
    
    async def _record_conversation_chain(self, context: ExtractedContext, messages: List[Any], agent_results: Optional[Dict[str, str]] = None):
        """Record compressed chronological conversation exchanges"""
        from datetime import datetime
        
        # Track human and assistant messages separately to pair them
        human_msg = None
        assistant_msg = None
        
        # Process messages to find human-assistant pairs
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
                role = msg.__class__.__name__.replace("Message", "").lower()
                content = msg.content
                
                # Skip system messages
                if role == "system":
                    continue
                
                if role in ['human', 'user']:
                    human_msg = content
                elif role in ['ai', 'assistant']:
                    assistant_msg = content
                    
            elif isinstance(msg, dict):
                role = msg.get("type", "unknown").lower()
                content = msg.get('content', '')
                
                if role in ['human', 'user']:
                    human_msg = content
                elif role in ['ai', 'assistant']:
                    assistant_msg = content
        
        # If we have a human-assistant exchange, record it
        if human_msg or assistant_msg:
            # Find the next message number
            existing_keys = [k for k in context.conversation_chain.keys() if k.startswith('message_')]
            if existing_keys:
                max_num = max([int(k.split('_')[1]) for k in existing_keys])
                next_num = max_num + 1
            else:
                next_num = 1
            
            message_key = f"message_{next_num}"
            exchange = {}
            
            # Compress and store human message
            if human_msg:
                compressed_human = await self._compress_message("human", human_msg)
                exchange["human"] = compressed_human
            
            # Compress and store assistant message with agent data
            if assistant_msg:
                compressed_assistant = await self._compress_message("assistant", assistant_msg)
                exchange["assistant"] = compressed_assistant
                
                # Add agent information if available
                if agent_results:
                    exchange["agents_called"] = list(agent_results.keys())
                    exchange["agent_data"] = {}
                    
                    # Extract structured data from each agent result
                    for agent, result in agent_results.items():
                        exchange["agent_data"][agent] = self._extract_key_data(result)
            
            exchange["timestamp"] = datetime.utcnow().isoformat()
            context.conversation_chain[message_key] = exchange
        
        # Trim conversation chain to prevent unbounded growth (keep last 25 message pairs)
        if len(context.conversation_chain) > 25:
            # Sort by message number and keep only the most recent
            sorted_messages = sorted(context.conversation_chain.items(), 
                                   key=lambda x: int(x[0].split('_')[1]))
            recent_messages = dict(sorted_messages[-25:])
            context.conversation_chain = recent_messages
        
        logger.debug(f"Recorded conversation in compressed chain (total: {len(context.conversation_chain)} exchanges)")
    
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
        if not context:
            logger.info(f"No context found for thread {thread_id}")
            return 0
        
        # Even if no structured extractions, try conversation chain for memories
        if context.extraction_count == 0 and not context.conversation_chain:
            logger.info(f"No context or conversation chain found for thread {thread_id}")
            return 0
        
        memories_saved = 0
        
        # Process all extractions and save MEMORY_WORTHY ones
        for ext_class in context.extraction_classes:
            items = context.extractions.get(ext_class, [])
            
            for item in items:
                ext_text = item.get('text', '')
                attrs = item.get('attributes', {})
                
                if self._should_save_as_memory(ext_class, ext_text, attrs):
                    memory_saved = await self._save_memory_direct(ext_class, ext_text, attrs, user_id, thread_id)
                    if memory_saved:
                        memories_saved += 1
        
        # If no structured extractions but we have conversation chain, try to extract memories from raw conversation
        if context.extraction_count == 0 and context.conversation_chain:
            logger.info(f"No structured extractions, trying conversation chain memory extraction for {thread_id}")
            memories_from_conversation = await self._extract_memories_from_conversation_chain(context, user_id, thread_id)
            memories_saved += memories_from_conversation
        
        logger.info(f"💾 Extracted {memories_saved} memories from context for thread {thread_id}")
        return memories_saved
    
    async def _extract_memories_from_conversation_chain(self, context: ExtractedContext, user_id: str, thread_id: str) -> int:
        """Extract memories from conversation chain using direct LLM processing"""
        if not context.conversation_chain:
            return 0
        
        # Convert conversation chain to text
        conversation_text = ""
        for message_key in sorted(context.conversation_chain.keys(), key=lambda x: int(x.split('_')[1])):
            exchange = context.conversation_chain[message_key]
            if 'human' in exchange:
                conversation_text += f"Human: {exchange['human']}\n"
            if 'assistant' in exchange:
                conversation_text += f"Assistant: {exchange['assistant']}\n"
        
        logger.info(f"Processing conversation chain: {conversation_text[:200]}...")
        
        # Use memory persistence to extract memories from the conversation text
        try:
            from app.memory.memory_persistence import MemoryExtractionService
            extraction_service = MemoryExtractionService()
            # Convert conversation text to fake messages for the extraction service
            from langchain_core.messages import HumanMessage, AIMessage
            fake_messages = []
            lines = conversation_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Human: '):
                    fake_messages.append(HumanMessage(content=line[7:]))
                elif line.startswith('Assistant: '):
                    fake_messages.append(AIMessage(content=line[11:]))
            memories = await extraction_service.extract_memories_from_conversation(fake_messages, user_id)
            
            # Save each memory
            memories_saved = 0
            for memory in memories:
                # Add thread context
                memory.metadata = memory.metadata or {}
                memory.metadata['thread_id'] = thread_id
                memory.metadata['extraction_source'] = 'conversation_chain'
                
                success = await self._save_memory_via_manager(memory, user_id)
                if success:
                    memories_saved += 1
            
            logger.info(f"Extracted {memories_saved} memories from conversation chain")
            return memories_saved
            
        except Exception as e:
            logger.error(f"Error extracting memories from conversation chain: {e}")
            return 0
    
    async def _save_memory_via_manager(self, memory, user_id: str) -> bool:
        """Save memory using the memory manager"""
        try:
            from app.memory.postgres_memory_manager_v2 import SimpleMemoryManager
            memory_manager = SimpleMemoryManager()
            await memory_manager.store_memory(memory)
            return True
        except Exception as e:
            logger.error(f"Error saving memory via manager: {e}")
            return False
    
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
    
    async def _save_memory_direct(self, ext_class: str, ext_text: str, attrs: dict, user_id: str, thread_id: str) -> bool:
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
                    "reason": self._generate_memory_reason(ext_class, ext_text, attrs),
                    "attributes": attrs,
                    "model": self.model_id,
                    "confidence": confidence_score,
                    "thread_id": thread_id  # Include thread_id to enable filtering
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
    
    def _generate_memory_reason(self, ext_class: str, ext_text: str, attrs: dict) -> str:
        """Generate human-readable reason why this memory is worth saving"""
        
        # Generate contextual reasons based on extraction class and content
        if ext_class in ["user_identity", "user_profile", "user_role"]:
            return "Core user identity information that helps personalize future interactions"
        
        elif "preference" in ext_class.lower():
            if "always" in ext_text.lower():
                return "Strong user preference that consistently influences their decisions"
            elif "prefer" in ext_text.lower():
                return "User preference that guides their choices and workflow"
            else:
                return "User preference that affects their work style and decisions"
        
        elif ext_class in ["user_expertise", "user_specialization", "technical_expertise"]:
            return "User's professional expertise that determines appropriate conversation depth and context"
        
        elif ext_class in ["user_experience", "professional_background"]:
            years = attrs.get("years_experience") or attrs.get("duration_years")
            if years:
                return f"Professional experience level ({years} years) helps tailor recommendations and complexity"
            else:
                return "Professional experience level helps determine appropriate conversation depth"
        
        elif ext_class in ["business_context", "company_info", "business_details"]:
            return "Business context that influences recommendations and understanding of user's environment"
        
        elif ext_class in ["policy", "standard", "rule"]:
            return "User's policy or standard that must be considered in future recommendations"
        
        elif "tool" in ext_class.lower() or "technology" in ext_class.lower():
            return "User's tool or technology preference that affects solution recommendations"
        
        elif ext_class in ["user_constraint", "user_limitation"]:
            return "User constraint that must be considered when providing solutions or recommendations"
        
        elif ext_class in ["user_goal", "user_objective"]:
            return "User's stated goal that provides direction for future assistance"
        
        # Fallback for any other extraction class
        else:
            return f"Durable user information ({ext_class}) with long-term relevance for personalized assistance"
    
    def clear_old_context(self, thread_id: str):
        """Clear old context to prevent unbounded growth"""
        if thread_id in self.contexts:
            context = self.contexts[thread_id]
            # Keep only recent extractions per class
            for ext_class in context.extractions:
                if len(context.extractions[ext_class]) > 20:
                    context.extractions[ext_class] = context.extractions[ext_class][-20:]