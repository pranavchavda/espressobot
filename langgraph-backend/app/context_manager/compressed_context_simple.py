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
    
    def __init__(self, model_id: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model_id = model_id
        self.api_key = api_key
        self.contexts: Dict[str, ExtractedContext] = {}  # thread_id -> context
        
        # More open-ended extraction prompt
        self.extraction_prompt = textwrap.dedent("""
            Extract ALL important information from this conversation.
            
            BE CREATIVE with extraction classes. Create specific, descriptive classes for everything you find.
            
            Guidelines:
            - Create a new extraction_class for each TYPE of information
            - Use descriptive names like "product_listing", "price_comparison", "user_complaint", "api_error"
            - Extract the exact text that contains the information
            - Include ALL relevant attributes (IDs, names, numbers, statuses, dates, etc.)
            - Preserve exact values, especially for IDs, prices, quantities
            
            Examples of extraction classes (create your own as needed):
            - product_search_result, product_details, pricing_information
            - user_question, follow_up_request, clarification_needed
            - agent_action, api_response, error_message
            - inventory_status, shipping_info, order_details
            - comparison_request, feature_inquiry, availability_check
            
            Extract EVERYTHING that could be useful for understanding the conversation context.
            The goal is comprehensive information preservation.
        """)
        
        # Provide minimal examples to guide format but not restrict content
        self.extraction_examples = [
            lx.data.ExampleData(
                text="User: Show me espresso machines under $500",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="product_search_request",
                        extraction_text="Show me espresso machines under $500",
                        attributes={
                            "product_type": "espresso machines",
                            "price_constraint": "under $500",
                            "action": "show"
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="Agent: Found 3 products: Breville Bambino Plus ($399), De'Longhi EC155 ($99.95), Gaggia Classic Pro ($449)",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="search_results_summary",
                        extraction_text="Found 3 products",
                        attributes={"count": "3", "status": "success"}
                    ),
                    lx.data.Extraction(
                        extraction_class="product_with_price",
                        extraction_text="Breville Bambino Plus ($399)",
                        attributes={"name": "Breville Bambino Plus", "price": "$399"}
                    ),
                    lx.data.Extraction(
                        extraction_class="product_with_price",
                        extraction_text="De'Longhi EC155 ($99.95)",
                        attributes={"name": "De'Longhi EC155", "price": "$99.95"}
                    ),
                    lx.data.Extraction(
                        extraction_class="product_with_price",
                        extraction_text="Gaggia Classic Pro ($449)",
                        attributes={"name": "Gaggia Classic Pro", "price": "$449"}
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
                           agent_results: Optional[Dict[str, str]] = None) -> ExtractedContext:
        """Compress a conversation turn into structured extractions AND record conversation chain"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting compression for thread {thread_id} with {len(messages)} messages")
        
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
        """Store an extraction in the context"""
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
        
        logger.debug(f"Stored: {ext_class} -> {ext_text[:50]}... with {len(attrs)} attributes")
    
    def clear_old_context(self, thread_id: str):
        """Clear old context to prevent unbounded growth"""
        if thread_id in self.contexts:
            context = self.contexts[thread_id]
            # Keep only recent extractions per class
            for ext_class in context.extractions:
                if len(context.extractions[ext_class]) > 20:
                    context.extractions[ext_class] = context.extractions[ext_class][-20:]