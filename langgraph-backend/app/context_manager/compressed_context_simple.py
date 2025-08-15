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
        
        # Dynamically show all extraction classes and their content
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
            for item in items[:10]:  # Show more items since we want comprehensive context
                if isinstance(item, dict):
                    text = item.get('text', '')[:200]
                    attrs = item.get('attributes', {})
                    
                    # Build a comprehensive line with all important attributes
                    line = f"  • {text}"
                    if attrs:
                        # Show ALL attributes, not just first 3
                        attr_parts = []
                        for k, v in attrs.items():
                            if v and str(v).strip():
                                # Format the value nicely
                                if isinstance(v, list):
                                    v = f"[{len(v)} items]"
                                elif isinstance(v, dict):
                                    v = f"[{len(v)} fields]"
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
        """Compress a conversation turn into structured extractions"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting compression for thread {thread_id} with {len(messages)} messages")
        
        context = self.get_context(thread_id)
        
        # Convert messages to text for extraction
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
            
            result = lx.extract(
                text_or_documents=conversation_text,
                prompt_description=self.extraction_prompt,
                examples=self.extraction_examples,
                model_id=self.model_id,
                api_key=self.api_key if is_openai else None,
                fence_output=is_openai,  # Must be True for OpenAI models
                use_schema_constraints=not is_openai  # Must be False for OpenAI models
            )
            
            logger.info(f"LangExtract found {len(result.extractions)} extractions")
            
            # Process each extraction
            for extraction in result.extractions:
                self._store_extraction(context, extraction)
            
            logger.info(f"Stored {context.extraction_count} total extractions in {len(context.extraction_classes)} classes")
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
        
        return context
    
    def _store_extraction(self, context: ExtractedContext, extraction: lx.data.Extraction):
        """Store an extraction in the context"""
        ext_class = extraction.extraction_class
        ext_text = extraction.extraction_text
        attrs = extraction.attributes or {}
        
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