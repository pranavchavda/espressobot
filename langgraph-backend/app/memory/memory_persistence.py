"""Memory Persistence Node for LangGraph Integration"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import langextract as lx

from ..state.graph_state import GraphState
from .postgres_memory_manager_v2 import SimpleMemoryManager, Memory
from .prompt_assembler import PromptAssembler, ContextTier
from .embedding_service import get_embedding_service
from .memory_decay_service import get_decay_service

logger = logging.getLogger(__name__)

# Feature flag: when True, use LangExtract exclusively (no GPT fallback)
FORCE_LANGEXTRACT_ONLY = True  # Use langextract exclusively with proper configuration

# Debug flag: when True, emit detailed logs for LangExtract pipeline
DEBUG_LANGEXTRACT_LOGS = True

# Quality thresholds to reduce empty/low-value memories
MIN_MEMORY_CONTENT_CHARS = 20  # Skip memories shorter than this after normalization
MIN_MEMORY_CONFIDENCE = 0.5    # Stricter than previous 0.3
MIN_MEMORY_CONTENT_CHARS_SHORT = 12  # For durable instrumentation policies

# Domain signal lists to preserve durable instrumentation/tracking policies
INSTRUMENTATION_KEYWORDS = [
    "tracking script", "analytics", "ga4", "google analytics", "gtm", "google tag manager",
    "tag manager", "pixel", "meta pixel", "facebook pixel", "tiktok pixel", "hotjar",
    "klaviyo", "segment", "rudderstack", "measurement id", "conversion tracking",
    "server-side tracking", "consent mode", "cookie consent", "data layer"
]
LONGTERM_QUALIFIERS = [
    "always", "sitewide", "across the site", "policy", "standard", "default", "every page"
]

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
        
        # Use langextract exclusively with proper configuration
        logger.info("Extracting memories using langextract (langextract-only mode)")
        return await self._extract_memories_langextract(conversation_text, user_id)
    
    def _normalize_memory_content(self, text: str) -> str:
        """Normalize and sanitize memory content string.
        - Strips code fences, quotes, and excess whitespace
        - Collapses spaces/newlines
        """
        if not text:
            return ""
        s = str(text)
        # Remove markdown code fences
        s = re.sub(r"^```[a-zA-Z0-9]*\n", "", s.strip())
        s = re.sub(r"\n```$", "", s)
        # Strip surrounding quotes
        s = s.strip().strip('"').strip("'")
        # Collapse whitespace
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    def _is_longterm_instrumentation(self, text_normalized: str) -> bool:
        """Detect durable sitewide instrumentation/tracking policies.
        Requires at least one instrumentation keyword and one long-term qualifier.
        """
        t = text_normalized.lower()
        if not t:
            return False
        has_kw = any(k in t for k in INSTRUMENTATION_KEYWORDS)
        has_q = any(q in t for q in LONGTERM_QUALIFIERS)
        return has_kw and has_q

    def _maybe_adjust_category(self, text_normalized: str, category: str) -> str:
        """Adjust memory category based on content signals."""
        if self._is_longterm_instrumentation(text_normalized) and (not category or category == "general"):
            return "preferences"
        return category or "general"

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
                # Durable instrumentation/tracking policy (should be extracted)
                lx.data.ExampleData(
                    text=(
                        "User: We always load GA4 via Google Tag Manager across the site. "
                        "Do not embed GA scripts directly. Use Consent Mode v2 and keep ad_storage denied until consent.\n"
                        "Assistant: Got it, that will be our standard tracking policy."
                    ),
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="instrumentation_policy",
                            extraction_text=(
                                "always load GA4 via GTM across the site; do not embed GA directly; "
                                "use Consent Mode v2; ad_storage denied until consent"
                            ),
                            attributes={
                                "content": (
                                    "Sitewide tracking policy: Always load GA4 via Google Tag Manager; "
                                    "never embed GA scripts directly; use Consent Mode v2; default ad_storage denied until consent"
                                ),
                                "category": "preferences",
                                "importance": 0.85,
                                "confidence": 0.95,
                                "reasoning": "Long-term sitewide analytics policy that impacts many future tasks",
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
                ),
                lx.data.ExampleData(
                    text="User: I need help setting up the Breville MAP sale from August 15-21. Please update prices and configure the metafields correctly. I'm working with Monalisa from ClearSale on order analysis.\nAssistant: I'll help set up the Breville promotion.",
                    extractions=[
                        # No extractions - all content is task-specific and ephemeral:
                        # - "Breville MAP sale from August 15-21" is date-specific task
                        # - "working with Monalisa from ClearSale" is current project detail
                        # - Price updates and metafields are specific technical tasks
                    ]
                ),
                # One-off tracking task (should NOT be extracted)
                lx.data.ExampleData(
                    text=(
                        "User: Please add the tracking script to the back-to-school landing page today and test conversions.\n"
                        "Assistant: I'll add it to that page and run tests."
                    ),
                    extractions=[
                        # No extractions – this is a one-off, page-specific task, not a durable policy
                    ]
                ),
                lx.data.ExampleData(
                    text="User: For ClearSale fraud review, I need order details from last 3 days - order IDs, customer names, amounts and risk levels. Limit to 5 orders for analysis.\nAssistant: I'll fetch the detailed order information.",
                    extractions=[
                        # No extractions - all content is task-specific:
                        # - "last 3 days" is time-specific  
                        # - "order IDs, customer names, amounts" are specific data requests
                        # - "limit to 5 orders" is specific task parameter
                        # - Nothing reveals lasting user identity or preferences
                    ]
                ),
                lx.data.ExampleData(
                    text="User: I'm the head of operations at iDrinkCoffee.com and handle all fraud prevention systems. We process about 150 orders daily and work with multiple payment processors.\nAssistant: That's helpful context for understanding your business needs.",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="user_role",
                            extraction_text="I'm the head of operations at iDrinkCoffee.com",
                            attributes={
                                "content": "User is head of operations at iDrinkCoffee.com",
                                "category": "facts", 
                                "importance": 0.95,
                                "confidence": 0.95,
                                "reasoning": "Core professional identity that affects all business discussions",
                                "is_ephemeral": False
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="business_context",
                            extraction_text="handle all fraud prevention systems...process about 150 orders daily",
                            attributes={
                                "content": "User manages fraud prevention for e-commerce business processing ~150 orders daily",
                                "category": "expertise",
                                "importance": 0.85,
                                "confidence": 0.9,
                                "reasoning": "Business context that informs technical needs and priorities",
                                "is_ephemeral": False
                            }
                        )
                    ]
                )
            ]
            
            # Extract memories using langextract with proper parameters
            prompt_description = """Extract ONLY essential, reusable memories that will have long-term value for future conversations.

                STRICT CRITERIA - INCLUDE only if the information:
                1. Describes the USER'S identity, role, or core expertise (not temporary work)
                2. Reveals consistent preferences or patterns that affect multiple conversations
                3. Establishes context about their business or industry (not specific tasks)
                4. Shows expertise areas that inform how to help them
                5. Defines sitewide analytics/instrumentation policies or durable tracking preferences (e.g., GA4 via GTM, Consent Mode)
                
                EXAMPLES OF GOOD EXTRACTIONS:
                - "User is a senior backend engineer specializing in Python"
                - "User prefers command-line tools over GUI applications"
                - "User manages an e-commerce platform with 100+ daily orders"
                - "User works with payment systems and fraud prevention"
                - "Sitewide tracking policy: Always load GA4 via GTM; no direct GA; Consent Mode v2 with default denied until consent"
                
                ALWAYS EXCLUDE (mark is_ephemeral=True):
                - ANY specific task, request, or one-time activity
                - Date ranges, deadlines, or time-specific information
                - Specific order numbers, amounts, or data analysis tasks
                - References to specific people they're working with on current tasks
                - Workflow steps, process details, or how-to information
                - Assistant responses, suggestions, or conversational content
                - System configurations or technical setup for specific projects
                - Any information that starts with "User needs", "User wants", "User requires"
                - One-off tracking changes for a specific page/campaign/date (e.g., "add tracking script to this page today")
                
                CRITICAL RULE: If uncertain whether something has long-term value, DON'T extract it.
                Most conversations should extract 0-1 memories. Only extract if genuinely essential."""
            
            # Call langextract using EXACT same configuration as working context compression
            import os
            
            model_id = "gpt-4.1-mini"
            api_key = os.getenv("OPENAI_API_KEY")
            
            # Use same configuration logic as context compression for consistency
            is_openai = model_id.startswith("gpt") or "gpt-" in model_id
            
            if DEBUG_LANGEXTRACT_LOGS:
                logger.debug(f"LangExtract call parameters: model_id={model_id}, is_openai={is_openai}")
                logger.debug(f"fence_output={is_openai}, use_schema_constraints={not is_openai}")
                logger.debug(f"OPENAI_API_KEY present={bool(api_key)}")
            
            # Use EXACT same parameters as working context compression - no language_model_type!
            try:
                result = lx.extract(
                    text_or_documents=conversation_text,
                    prompt_description=prompt_description,
                    examples=examples,
                    model_id=model_id,
                    api_key=api_key if is_openai else None,
                    fence_output=True,  # Always True for proper parsing
                    use_schema_constraints=False,  # Always False for OpenAI compatibility
                    temperature=0.1  # Low temperature for consistent output
                )
            except Exception as lx_error:
                logger.error(f"LangExtract extraction failed: {lx_error}, falling back to GPT-4.1-nano")
                # Fall back to GPT extraction method
                return await self._extract_memories_gpt(conversation_text, user_id)
            
            # Handle case where result might be wrapped in markdown code blocks
            if isinstance(result, str):
                # Strip markdown code blocks if present
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
            seen_keys = set()  # dedupe within this extraction batch
            
            # Result is an AnnotatedDocument with extractions
            if DEBUG_LANGEXTRACT_LOGS:
                try:
                    ext_count = len(result.extractions) if (result and hasattr(result, 'extractions') and result.extractions is not None) else 0
                    logger.debug(f"LangExtract result type={type(result).__name__}, has_extractions={hasattr(result, 'extractions')}, extractions_count={ext_count}")
                except Exception as _e:
                    logger.debug(f"LangExtract result inspection failed: {_e}")
            if result and hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    attrs = extraction.attributes or {}
                    if DEBUG_LANGEXTRACT_LOGS:
                        preview = attrs.get('content', '')[:80]
                        logger.debug(f"LX extraction candidate: class={extraction.extraction_class}, confidence={attrs.get('confidence')}, ephemeral={attrs.get('is_ephemeral')}, preview='{preview}'")
                    
                    # Prefer attribute content; fallback to extraction_text
                    raw_content = attrs.get("content") or extraction.extraction_text or ""
                    normalized = self._normalize_memory_content(raw_content)
                    content = normalized.lower()

                    longterm_inst = self._is_longterm_instrumentation(normalized)

                    # Skip ephemeral memories unless it's a durable instrumentation policy
                    if attrs.get("is_ephemeral", False) and not longterm_inst:
                        filtered_count += 1
                        if DEBUG_LANGEXTRACT_LOGS:
                            logger.debug(f"Filtered[E] ephemeral: {attrs.get('content', '')[:50]}...")
                        continue
                    elif attrs.get("is_ephemeral", False) and longterm_inst and DEBUG_LANGEXTRACT_LOGS:
                        logger.debug(f"Override[E] keeping durable instrumentation policy despite ephemeral flag: '{normalized[:80]}'")

                    # Skip low confidence memories
                    confidence = float(attrs.get("confidence", 0.5))
                    if confidence < MIN_MEMORY_CONFIDENCE:
                        filtered_count += 1
                        if DEBUG_LANGEXTRACT_LOGS:
                            logger.debug(f"Filtered[C] low confidence ({confidence} < {MIN_MEMORY_CONFIDENCE}): {attrs.get('content', '')[:50]}...")
                        continue

                    # Additional filtering for task-specific content (allow if durable instrumentation)
                    
                    task_indicators = [
                        # Specific task patterns
                        "needs to", "wants to", "requires", "requesting", "asked for",
                        "working on", "currently", "this time", "today", "yesterday",
                        "last week", "next week", "for analysis", "for review", "for fraud",
                        
                        # Specific data requests
                        "order ids", "customer names", "amounts", "risk levels", 
                        "order details", "order information", "order data",
                        "3-day window", "5 orders", "limit", "specific orders",
                        
                        # Workflow/process indicators
                        "analyzes recent", "focuses on", "reviews", "examines",
                        "coordinates with", "collaborates with", "works with",
                        "handles order management", "fraud review processes",
                        
                        # Time-specific patterns
                        "window", "period", "timeframe", "recent", "current",
                        "specific", "particular", "detailed", "individual",
                        
                        # System access patterns
                        "access to systems", "with access", "systems that handle"
                    ]
                    
                    if any(indicator in content for indicator in task_indicators) and not longterm_inst:
                        filtered_count += 1
                        if DEBUG_LANGEXTRACT_LOGS:
                            logger.debug(f"Filtered[T] task-specific: {content[:50]}...")
                        continue
                    elif any(indicator in content for indicator in task_indicators) and longterm_inst and DEBUG_LANGEXTRACT_LOGS:
                        logger.debug(f"Override[T] keeping durable instrumentation policy: '{normalized[:80]}'")

                    # Skip empty/short/placeholder content
                    min_len = MIN_MEMORY_CONTENT_CHARS_SHORT if longterm_inst else MIN_MEMORY_CONTENT_CHARS
                    if not normalized or len(normalized) < min_len:
                        filtered_count += 1
                        if DEBUG_LANGEXTRACT_LOGS:
                            logger.debug(f"Filtered[N] empty/short (<{min_len} chars): '{normalized}'")
                        continue
                    
                    # Skip if content contains too few alphabetic characters
                    if not re.search(r"[A-Za-z]{3,}", normalized):
                        filtered_count += 1
                        if DEBUG_LANGEXTRACT_LOGS:
                            logger.debug(f"Filtered[A] non-informative content: '{normalized}'")
                        continue
                    
                    # Deduplicate within batch
                    dedupe_key = " ".join(normalized.lower().split())
                    if dedupe_key in seen_keys:
                        filtered_count += 1
                        if DEBUG_LANGEXTRACT_LOGS:
                            logger.debug(f"Filtered[D] duplicate content: '{normalized[:60]}'")
                        continue
                    seen_keys.add(dedupe_key)
                    
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
                        content=normalized,
                        category=self._maybe_adjust_category(normalized, attrs.get("category", "general")),
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
            logger.error(f"Langextract memory extraction failed: {e}")
            # Try GPT fallback if langextract fails completely
            logger.info("Attempting GPT-4.1-nano fallback for memory extraction")
            try:
                return await self._extract_memories_gpt(conversation_text, user_id)
            except Exception as fallback_error:
                logger.error(f"GPT fallback also failed: {fallback_error}")
                return []  # Return empty list if both methods fail
    
    async def _extract_memories_gpt(self, conversation_text: str, user_id: str) -> List[Memory]:
        """GPT-4.1-nano extraction method (primary method)"""
        
        if not self.openai_client:
            return []
        
        # ORIGINAL EXTRACTION CODE - KEPT AS FALLBACK
        extraction_prompt = f"""
Extract ONLY essential, reusable memories that will have long-term value for future conversations.

STRICT CRITERIA - INCLUDE only if the information:
1. Describes the USER'S identity, role, or core expertise (not temporary work)
2. Reveals consistent preferences or patterns that affect multiple conversations
3. Establishes context about their business or industry (not specific tasks)
4. Shows expertise areas that inform how to help them

EXAMPLES OF GOOD EXTRACTIONS:
- "User is a senior backend engineer specializing in Python"
- "User prefers command-line tools over GUI applications"
- "User manages an e-commerce platform with 100+ daily orders"
- "User works with payment systems and fraud prevention"

ALWAYS EXCLUDE (mark is_ephemeral=True):
- ANY specific task, request, or one-time activity
- Date ranges, deadlines, or time-specific information
- Specific order numbers, amounts, or data analysis tasks
- References to specific people they're working with on current tasks
- Workflow steps, process details, or how-to information
- Assistant responses, suggestions, or conversational content
- System configurations or technical setup for specific projects
- Any information that starts with "User needs", "User wants", "User requires"

CRITICAL RULE: If uncertain whether something has long-term value, DON'T extract it.
Most conversations should extract 0-1 memories. Only extract if genuinely essential.

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
            seen_keys = set()
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
                if confidence < MIN_MEMORY_CONFIDENCE:
                    filtered_count += 1
                    logger.debug(f"Filtered low confidence ({confidence} < {MIN_MEMORY_CONFIDENCE}) memory: {item.get('content', '')[:50]}...")
                    continue
                
                # Additional filtering for task-specific content (same as langextract)
                raw_content = item.get("content", "")
                normalized = self._normalize_memory_content(raw_content)
                content = normalized.lower()
                longterm_inst = self._is_longterm_instrumentation(normalized)
                
                task_indicators = [
                    # Specific task patterns
                    "needs to", "wants to", "requires", "requesting", "asked for",
                    "working on", "currently", "this time", "today", "yesterday",
                    "last week", "next week", "for analysis", "for review", "for fraud",
                    
                    # Specific data requests
                    "order ids", "customer names", "amounts", "risk levels", 
                    "order details", "order information", "order data",
                    "3-day window", "5 orders", "limit", "specific orders",
                    
                    # Workflow/process indicators
                    "analyzes recent", "focuses on", "reviews", "examines",
                    "coordinates with", "collaborates with", "works with",
                    "handles order management", "fraud review processes",
                    
                    # Time-specific patterns
                    "window", "period", "timeframe", "recent", "current",
                    "specific", "particular", "detailed", "individual",
                    
                    # System access patterns
                    "access to systems", "with access", "systems that handle"
                ]
                
                if any(indicator in content for indicator in task_indicators) and not longterm_inst:
                    filtered_count += 1
                    logger.debug(f"Filtered task-specific memory: {content[:50]}...")
                    continue
                elif any(indicator in content for indicator in task_indicators) and longterm_inst:
                    logger.debug(f"Override task-specific for durable instrumentation: '{normalized[:80]}'")
                
                # Check for task-specific opening patterns
                content_start = content[:30]
                bad_starts = [
                    "user is involved in", "user requires", "user needs",
                    "user specifically", "user analyzes", "user focuses",
                    "user works on", "user handles", "user coordinates",
                    "user reviews", "user requests", "user wants"
                ]
                
                if any(content_start.startswith(start) for start in bad_starts) and not longterm_inst:
                    filtered_count += 1
                    logger.debug(f"Filtered task-oriented start pattern: {content[:50]}...")
                    continue
                elif any(content_start.startswith(start) for start in bad_starts) and longterm_inst:
                    logger.debug(f"Override start-pattern for durable instrumentation: '{normalized[:80]}'")
                
                # Skip empty/short/placeholder content
                min_len = MIN_MEMORY_CONTENT_CHARS_SHORT if longterm_inst else MIN_MEMORY_CONTENT_CHARS
                if not normalized or len(normalized) < min_len:
                    filtered_count += 1
                    logger.debug(f"Filtered empty/short memory (<{min_len} chars): '{normalized}'")
                    continue
                
                if not re.search(r"[A-Za-z]{3,}", normalized):
                    filtered_count += 1
                    logger.debug(f"Filtered non-informative memory: '{normalized}'")
                    continue
                
                # Deduplicate within batch
                dedupe_key = " ".join(normalized.lower().split())
                if dedupe_key in seen_keys:
                    filtered_count += 1
                    logger.debug(f"Filtered duplicate memory: '{normalized[:60]}'")
                    continue
                seen_keys.add(dedupe_key)
                
                # Build metadata including new fields
                metadata = item.get("metadata", {})
                metadata["confidence"] = confidence
                metadata["reasoning"] = item.get("reasoning", "")
                metadata["extraction_version"] = "v3_quality_focused_gpt_fallback"
                
                memory = Memory(
                    user_id=user_id,
                    content=normalized,
                    category=self._maybe_adjust_category(normalized, item.get("category", "general")),
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