"""
Compressed Context Management using LangExtract
Enables token-efficient context maintenance across long conversations
"""
import langextract as lx
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
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
    
    # Legacy fields for backward compatibility (will be populated from extractions)
    products: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    operations: List[Dict[str, Any]] = field(default_factory=list)
    user_goals: List[str] = field(default_factory=list)
    agent_results: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    
    # Source grounding - maps extractions to original message positions
    source_map: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    
    # Metadata about what was extracted
    extraction_classes: List[str] = field(default_factory=list)  # List of all extraction classes found
    extraction_count: int = 0  # Total number of extractions
    
    def to_context_string(self, max_tokens: int = 1000) -> str:
        """Convert to a concise context string for the orchestrator - shows ALL extraction types dynamically"""
        parts = []
        
        # Show extraction summary
        if self.extraction_count > 0:
            parts.append(f"Context extracted: {self.extraction_count} items in {len(self.extraction_classes)} categories")
            parts.append("")
        
        # Dynamically show all extraction classes and their content
        for extraction_class in self.extraction_classes:
            if extraction_class in self.extractions:
                items = self.extractions[extraction_class]
                if not items:
                    continue
                    
                # Format the class name nicely
                class_title = extraction_class.replace('_', ' ').title()
                parts.append(f"{class_title}:")
                
                # Show items based on type
                for item in items[:5]:  # Limit to 5 per category
                    if isinstance(item, dict):
                        # Show the main text first
                        text = item.get('text', '')
                        if text:
                            line = f"  • {text[:100]}"
                            # Add key attributes inline
                            attrs = item.get('attributes', {})
                            key_attrs = []
                            for k, v in list(attrs.items())[:3]:  # Show first 3 attributes
                                if v and str(v).strip():
                                    key_attrs.append(f"{k}={v}")
                            if key_attrs:
                                line += f" ({', '.join(key_attrs)})"
                            parts.append(line)
                    else:
                        parts.append(f"  • {str(item)[:100]}")
                parts.append("")  # Empty line between categories
        
        context = "\n".join(parts)
        
        # Truncate if too long (rough token estimate: 1 token ~= 4 chars)
        max_chars = max_tokens * 4
        if len(context) > max_chars:
            context = context[:max_chars] + "... [truncated]"
        
        return context

class CompressedContextManager:
    """Manages context compression using LangExtract"""
    
    def __init__(self, model_id: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model_id = model_id
        self.api_key = api_key
        self.contexts: Dict[str, ExtractedContext] = {}  # thread_id -> context
        
        # Define extraction schema with prompt and examples
        self.extraction_prompt = textwrap.dedent("""
            Extract ALL important information from this conversation. 
            
            CREATE NEW EXTRACTION CLASSES for any type of information you find important.
            Don't limit yourself to predefined categories - be creative and comprehensive.
            
            For each piece of important information:
            1. Create a descriptive extraction_class name (e.g., "product_pricing", "user_question", "error_message")
            2. Extract the relevant text
            3. Add attributes that capture the key details
            
            Examples of extraction classes you might create (but not limited to):
            - product_details, pricing_info, inventory_status
            - user_request, follow_up_question, clarification
            - agent_response, search_results, api_response
            - error_message, warning, success_confirmation
            - date_reference, time_constraint, deadline
            - customer_info, account_details, order_reference
            - technical_spec, configuration, setting
            - comparison, alternative_option, recommendation
            - action_taken, action_needed, pending_task
            
            IMPORTANT: 
            - Extract EVERYTHING that could be useful for understanding context
            - Create specific, descriptive extraction classes
            - Include all relevant attributes (IDs, names, values, statuses, etc.)
            - Preserve exact values, especially numbers, prices, IDs
            - If something seems important but doesn't fit existing classes, CREATE A NEW CLASS
            
            The goal is to lose ZERO information from the conversation.
        """)
        
        self.extraction_examples = [
            lx.data.ExampleData(
                text="User: Find the Breville Barista Express\nAgent: Found product gid://shopify/Product/7923456789 - Breville Barista Express (SKU: BES870XL)",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="user_intent",
                        extraction_text="Find the Breville Barista Express",
                        attributes={"action": "search", "target": "product"}
                    ),
                    lx.data.Extraction(
                        extraction_class="product",
                        extraction_text="gid://shopify/Product/7923456789",
                        attributes={
                            "title": "Breville Barista Express",
                            "sku": "BES870XL",
                            "found_by": "agent"
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="operation",
                        extraction_text="Found product",
                        attributes={
                            "type": "search",
                            "result": "success",
                            "product_id": "gid://shopify/Product/7923456789"
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="Agent: Product: Sanremo YOU - Black\nPrice: $9,500.00\nCompare at: $10,500.00\nInventory: 6 units in stock\nVariant ID: gid://shopify/ProductVariant/41072167878690",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="product_details",
                        extraction_text="Sanremo YOU - Black",
                        attributes={
                            "title": "Sanremo YOU - Black",
                            "price": "$9,500.00",
                            "compare_at_price": "$10,500.00",
                            "inventory": "6",
                            "variant_id": "gid://shopify/ProductVariant/41072167878690",
                            "in_stock": "true"
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="pricing",
                        extraction_text="Price: $9,500.00, Compare at: $10,500.00",
                        attributes={
                            "product": "Sanremo YOU - Black",
                            "price": "$9,500.00",
                            "compare_at_price": "$10,500.00",
                            "has_discount": "true"
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="inventory",
                        extraction_text="6 units in stock",
                        attributes={
                            "product": "Sanremo YOU - Black",
                            "quantity": "6",
                            "status": "in_stock"
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="User: Check my important emails\nAgent: Here are your unread emails: 1) Sender: Gianni Lagrasta - Subject: Parts Site Launch Plan - Message ID: 1989f1383e53a79f 2) Sender: Teresa Simpson - Subject: Re: coupon code leak - Message ID: 1989f1383e53a80f",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="user_intent",
                        extraction_text="Check my important emails",
                        attributes={"action": "check", "target": "emails"}
                    ),
                    lx.data.Extraction(
                        extraction_class="email",
                        extraction_text="Gianni Lagrasta - Parts Site Launch Plan",
                        attributes={
                            "sender": "Gianni Lagrasta",
                            "subject": "Parts Site Launch Plan",
                            "message_id": "1989f1383e53a79f",
                            "position": "1"
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="email",
                        extraction_text="Teresa Simpson - Re: coupon code leak",
                        attributes={
                            "sender": "Teresa Simpson",
                            "subject": "Re: coupon code leak",
                            "message_id": "1989f1383e53a80f",
                            "position": "2"
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="operation",
                        extraction_text="Listed unread emails",
                        attributes={
                            "type": "email_list",
                            "result": "success",
                            "count": "2"
                        }
                    )
                ]
            ),
            lx.data.ExampleData(
                text="User: open the second one\nAgent: Opening email from Teresa Simpson",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="user_intent",
                        extraction_text="open the second one",
                        attributes={"action": "open", "target": "second_item"}
                    ),
                    lx.data.Extraction(
                        extraction_class="reference",
                        extraction_text="the second one",
                        attributes={"refers_to": "second email - Teresa Simpson"}
                    ),
                    lx.data.Extraction(
                        extraction_class="operation",
                        extraction_text="Opening email from Teresa Simpson",
                        attributes={
                            "type": "email_open",
                            "result": "success",
                            "sender": "Teresa Simpson"
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
                           agent_results: Optional[Dict[str, str]] = None) -> ExtractedContext:
        """Compress a conversation turn into structured context"""
        
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
        
        conversation_text = "\n".join(text_parts)
        
        # Add agent results if provided
        if agent_results:
            text_parts.append("\nAgent Results:")
            for agent, result in agent_results.items():
                text_parts.append(f"{agent}: {result[:500]}")  # Limit length
            conversation_text = "\n".join(text_parts)
        
        try:
            # Extract structured data using LangExtract
            logger.info(f"Extracting context from {len(conversation_text)} chars of conversation")
            
            # Log a sample of the conversation to debug
            logger.debug(f"First 500 chars of conversation text: {conversation_text[:500]}")
            
            # Use OpenAI models via LangExtract
            if self.model_id.startswith("gpt"):
                # For OpenAI models, we need to set the API key
                import os
                if not self.api_key:
                    self.api_key = os.getenv("OPENAI_API_KEY")
                
                logger.debug(f"Using OpenAI model {self.model_id} for extraction")
                result = lx.extract(
                    text_or_documents=conversation_text,
                    prompt_description=self.extraction_prompt,
                    examples=self.extraction_examples,
                    model_id=self.model_id,
                    api_key=self.api_key
                )
            else:
                # For other models (Gemini, local)
                logger.debug(f"Using non-OpenAI model {self.model_id} for extraction")
                result = lx.extract(
                    text_or_documents=conversation_text,
                    prompt_description=self.extraction_prompt,
                    examples=self.extraction_examples,
                    model_id=self.model_id
                )
            
            logger.info(f"LangExtract returned {len(result.extractions)} extractions")
            
            # Process extractions into our context structure
            for i, extraction in enumerate(result.extractions):
                logger.debug(f"Extraction {i}: class={extraction.extraction_class}, text={extraction.extraction_text[:100] if extraction.extraction_text else 'None'}..., attrs={extraction.attributes}")
                self._process_extraction(context, extraction)
            
            logger.info(f"Extracted {len(result.extractions)} items into compressed context")
            logger.info(f"Context summary: {len(context.products)} products, {len(context.operations)} operations, {len(context.user_goals)} goals")
            
        except Exception as e:
            logger.error(f"Failed to compress turn: {e}")
            # Fallback: Store raw agent results
            if agent_results:
                for agent, result in agent_results.items():
                    if agent not in context.agent_results:
                        context.agent_results[agent] = []
                    context.agent_results[agent].append({
                        "summary": result[:200],
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        return context
    
    def _process_extraction(self, context: ExtractedContext, extraction: lx.data.Extraction):
        """Process a single extraction into the context structure - stores EVERYTHING dynamically"""
        
        try:
            ext_class = extraction.extraction_class
            ext_text = extraction.extraction_text
            attrs = extraction.attributes or {}
            
            # Store source grounding
            if extraction.char_interval:
                source_key = f"{ext_class}:{ext_text[:50]}"
                context.source_map[source_key] = (
                    extraction.char_interval.start_pos,
                    extraction.char_interval.end_pos
                )
            
            # Track this extraction class
            if ext_class not in context.extraction_classes:
                context.extraction_classes.append(ext_class)
            
            # Store the extraction dynamically
            if ext_class not in context.extractions:
                context.extractions[ext_class] = []
            
            # Store the full extraction with all its data
            extraction_data = {
                'text': ext_text,
                'attributes': attrs,
                'timestamp': datetime.utcnow().isoformat()
            }
            context.extractions[ext_class].append(extraction_data)
            context.extraction_count += 1
            
            logger.info(f"✅ Stored extraction: class={ext_class}, text_len={len(ext_text)}, attrs={len(attrs)}")
            
            # Also populate legacy fields for backward compatibility (if applicable)
            self._populate_legacy_fields(context, ext_class, ext_text, attrs)
            
        except Exception as e:
            logger.error(f"Error processing extraction: {e}")
    
    def _populate_legacy_fields(self, context: ExtractedContext, ext_class: str, ext_text: str, attrs: dict):
        """Populate legacy fields for minimal backward compatibility"""
        try:
            # Keep minimal backward compatibility for common extraction types
            if "product" in ext_class.lower() and "gid://shopify/Product/" in str(ext_text):
                # Extract product ID
                import re
                match = re.search(r'(gid://shopify/Product/\d+)', str(ext_text))
                if match:
                    product_id = match.group(1)
                    # Store all attributes
                    context.products[product_id] = attrs.copy()
                    context.products[product_id]['text'] = ext_text
                
                # Validate that this is a real product ID with proper digits
                # Real IDs look like: gid://shopify/Product/7923456789
                if "gid://shopify/Product/" in product_id:
                    # Extract the numeric part to validate
                    import re
                    match = re.search(r'gid://shopify/Product/(\d+)', product_id)
                    if match and len(match.group(1)) > 3:  # Real IDs have many digits
                        # Store ALL attributes from the extraction
                        product_data = {
                            "title": attrs.get("title", "Unknown"),
                            "sku": attrs.get("sku"),
                            "found_by": attrs.get("found_by"),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        # Add pricing information if present
                        if "price" in attrs:
                            product_data["price"] = attrs["price"]
                        if "compare_at_price" in attrs:
                            product_data["compare_at_price"] = attrs["compare_at_price"]
                        if "inventory" in attrs:
                            product_data["inventory"] = attrs["inventory"]
                        if "variant_id" in attrs:
                            product_data["variant_id"] = attrs["variant_id"]
                        if "status" in attrs:
                            product_data["status"] = attrs["status"]
                        if "handle" in attrs:
                            product_data["handle"] = attrs["handle"]
                        
                        context.products[product_id] = product_data
                        logger.info(f"✅ Added valid product to context: {product_id} with {len(product_data)} fields")
                    else:
                        logger.warning(f"⚠️ Skipping invalid product ID: {product_id} (too short or malformed)")
            
            elif ext_class == "operation":
                context.operations.append({
                    "type": attrs.get("type", "unknown"),
                    "result": attrs.get("result", "unknown"),
                    "details": ext_text,
                    "product_id": attrs.get("product_id"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif ext_class == "user_intent":
                goal = ext_text
                if goal not in context.user_goals:
                    context.user_goals.append(goal)
                
                # Extract constraints if mentioned
                if "constraint" in attrs:
                    context.constraints.append(attrs["constraint"])
            
            elif ext_class == "agent_result":
                agent_name = attrs.get("agent", "unknown")
                if agent_name not in context.agent_results:
                    context.agent_results[agent_name] = []
                
                context.agent_results[agent_name].append({
                    "summary": ext_text[:200],
                    "success": attrs.get("success", True),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif ext_class == "decision":
                context.decisions.append({
                    "decision": ext_text,
                    "reasoning": attrs.get("reasoning"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif ext_class == "search":
                context.searches.append({
                    "query": ext_text,
                    "results": attrs.get("results", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif ext_class == "email" or ext_class == "emails":
                # Store email details in operations for now
                context.operations.append({
                    "type": "email",
                    "details": ext_text,
                    "sender": attrs.get("sender"),
                    "subject": attrs.get("subject"),
                    "message_id": attrs.get("message_id"),
                    "preview": attrs.get("preview"),  # Add preview content
                    "position": attrs.get("position"),  # Track position (1st, 2nd, etc.)
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif ext_class == "reference" or ext_class == "references":
                # Track pronoun references
                context.decisions.append({
                    "decision": f"Reference: {ext_text}",
                    "reasoning": attrs.get("refers_to"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif ext_class == "product_details":
                # Rich product details - merge into existing product or create new
                title = attrs.get("title", ext_text)
                variant_id = attrs.get("variant_id")
                
                # Find product by variant ID or title
                product_id = None
                for pid, details in context.products.items():
                    if details.get("title") == title or details.get("variant_id") == variant_id:
                        product_id = pid
                        break
                
                # If not found, create a new entry
                if not product_id and variant_id:
                    # Extract product ID from variant if possible
                    import re
                    match = re.search(r'gid://shopify/Product/(\d+)', str(variant_id))
                    if match:
                        product_id = f"gid://shopify/Product/{match.group(1)}"
                
                if not product_id:
                    product_id = f"product_{title.replace(' ', '_').lower()}"
                
                # Merge all attributes
                if product_id not in context.products:
                    context.products[product_id] = {}
                
                context.products[product_id].update({
                    "title": title,
                    "price": attrs.get("price"),
                    "compare_at_price": attrs.get("compare_at_price"),
                    "inventory": attrs.get("inventory"),
                    "variant_id": variant_id,
                    "in_stock": attrs.get("in_stock", "true") == "true",
                    "timestamp": datetime.utcnow().isoformat()
                })
                logger.info(f"✅ Added rich product details for: {title}")
            
            elif ext_class == "pricing":
                # Pricing information - update product if exists
                product_name = attrs.get("product")
                if product_name:
                    # Find product by name
                    for pid, details in context.products.items():
                        if details.get("title") == product_name:
                            details["price"] = attrs.get("price")
                            details["compare_at_price"] = attrs.get("compare_at_price")
                            details["has_discount"] = attrs.get("has_discount", "false") == "true"
                            logger.info(f"✅ Updated pricing for: {product_name}")
                            break
            
            elif ext_class == "inventory":
                # Inventory information - update product if exists
                product_name = attrs.get("product")
                if product_name:
                    # Find product by name
                    for pid, details in context.products.items():
                        if details.get("title") == product_name:
                            details["inventory"] = attrs.get("quantity")
                            details["inventory_status"] = attrs.get("status", "in_stock")
                            logger.info(f"✅ Updated inventory for: {product_name}")
                            break
            
            else:
                # Handle any other extraction class dynamically
                # Store in operations as a generic extraction
                logger.info(f"Processing dynamic extraction class: {ext_class}")
                context.operations.append({
                    "type": ext_class,
                    "details": ext_text,
                    "attributes": attrs,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Also track in agent_results if it seems like an agent finding
                if ext_class.endswith("_data") or ext_class.endswith("_result"):
                    if "unknown" not in context.agent_results:
                        context.agent_results["unknown"] = []
                    context.agent_results["unknown"].append({
                        "summary": f"{ext_class}: {ext_text[:200]}",
                        "success": True,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
        except Exception as e:
            logger.warning(f"Failed to process extraction {extraction.extraction_class}: {e}")
    
    def clear_old_context(self, thread_id: str, keep_products: bool = True):
        """Clear old context to prevent unbounded growth"""
        if thread_id not in self.contexts:
            return
        
        context = self.contexts[thread_id]
        
        # Keep only recent operations
        if len(context.operations) > 20:
            context.operations = context.operations[-20:]
        
        # Keep only recent searches
        if len(context.searches) > 10:
            context.searches = context.searches[-10:]
        
        # Keep only recent decisions
        if len(context.decisions) > 10:
            context.decisions = context.decisions[-10:]
        
        # Optionally clear products (usually we want to keep these)
        if not keep_products and len(context.products) > 50:
            # Keep only the 50 most recently found products
            sorted_products = sorted(
                context.products.items(),
                key=lambda x: x[1].get('timestamp', ''),
                reverse=True
            )
            context.products = dict(sorted_products[:50])
        
        # Clear old agent results
        for agent in context.agent_results:
            if len(context.agent_results[agent]) > 5:
                context.agent_results[agent] = context.agent_results[agent][-5:]
        
        logger.info(f"Cleared old context for thread {thread_id}")