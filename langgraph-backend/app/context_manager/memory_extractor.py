"""
Memory Extractor - Separate process to extract memories from compressed context
"""
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class MemoryExtractor:
    """Extracts memories from compressed context as a separate process with deduplication"""
    
    def __init__(self):
        self.extraction_count = 0
        self.duplicates_prevented = 0
    
    async def extract_memories_from_context(self, context_manager, thread_id: str, user_id: str = "1") -> int:
        """Extract and save memories from compressed context"""
        
        try:
            # Get the compressed context
            context = context_manager.get_context(thread_id)
            if not context or context.extraction_count == 0:
                logger.info(f"No context found for thread {thread_id}")
                return 0
            
            memories_saved = 0
            
            logger.info(f"🔍 Processing {context.extraction_count} context items from thread {thread_id}")
            
            # Process all extractions and save MEMORY_WORTHY ones
            for ext_class in context.extraction_classes:
                items = context.extractions.get(ext_class, [])
                
                for item in items:
                    ext_text = item.get('text', '')
                    attrs = item.get('attributes', {})
                    
                    if self._should_save_as_memory(ext_class, ext_text, attrs):
                        memory_saved = await self._save_memory_direct(ext_class, ext_text, attrs, user_id, context_manager)
                        if memory_saved:
                            memories_saved += 1
                        elif memory_saved is False:  # Explicitly False means duplicate was detected
                            self.duplicates_prevented += 1
            
            if self.duplicates_prevented > 0:
                logger.info(f"💾 Extracted {memories_saved} memories from context for thread {thread_id} ({self.duplicates_prevented} duplicates prevented)")
            else:
                logger.info(f"💾 Extracted {memories_saved} memories from context for thread {thread_id}")
            
            self.extraction_count += memories_saved
            return memories_saved
            
        except Exception as e:
            logger.error(f"Failed to extract memories from context: {e}")
            return 0
    
    def _should_save_as_memory(self, ext_class: str, ext_text: str, attrs: dict) -> bool:
        """Determine if an extraction should be saved as memory"""
        
        # Check LangExtract classification first
        memory_classification = attrs.get('memory_classification', '').upper()
        
        if memory_classification == 'CONTEXT_ONLY':
            logger.debug(f"📄 Context-only: {ext_text[:50]}... (not saved to memory)")
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
            
            reason = self._generate_memory_reason(ext_class, ext_text, attrs)
            logger.info(f"✅ Memory-worthy: {ext_text[:50]}... (reason: {reason})")
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
        
        if should_save and len(ext_text.strip()) >= 10:
            reason = self._generate_memory_reason(ext_class, ext_text, attrs)
            logger.info(f"✅ Memory-worthy (heuristic): {ext_text[:50]}... (reason: {reason})")
            return True
        
        return False
    
    async def _save_memory_direct(self, ext_class: str, ext_text: str, attrs: dict, user_id: str, context_manager) -> bool:
        """Save extraction as memory directly with enhanced deduplication"""
        try:
            from ..memory.postgres_memory_manager_v2 import SimpleMemoryManager, Memory
            from ..memory.shared_manager import get_shared_memory_manager
            
            # Check for duplicates before saving
            if await self._is_duplicate_memory(ext_text, user_id, ext_class):
                logger.info(f"🔄 Duplicate memory skipped: {ext_text[:50]}...")
                return False
            
            # Extract confidence score from attributes or calculate default
            confidence_score = context_manager._extract_confidence_score(attrs)
            
            # Generate human-readable reason why this memory is worth saving
            reason = self._generate_memory_reason(ext_class, ext_text, attrs)
            
            # Create memory object
            memory = Memory(
                user_id=user_id,
                content=ext_text,
                category=context_manager._map_extraction_to_memory_category(ext_class),
                importance_score=context_manager._calculate_importance(ext_class, attrs, confidence_score),
                metadata={
                    "extraction_class": ext_class,
                    "extraction_method": "separate_memory_extraction",
                    "reason": reason,
                    "attributes": attrs,
                    "model": context_manager.model_id,
                    "confidence": confidence_score
                }
            )
            
            # Save memory (postgres manager will do additional exact-match deduplication)
            manager = await get_shared_memory_manager()
            memory_id = await manager.store_memory(memory)
            
            if memory_id:
                logger.info(f"💾 Saved memory {memory_id}: {ext_text[:60]}... (reason: {reason})")
                return True
            else:
                logger.error(f"Failed to save memory: {ext_text[:60]}...")
                return False
                
        except Exception as e:
            logger.error(f"Memory save error: {e}")
            return False
    
    async def _is_duplicate_memory(self, ext_text: str, user_id: str, ext_class: str) -> bool:
        """Enhanced deduplication check using semantic similarity"""
        try:
            from ..memory.shared_manager import get_shared_memory_manager
            from ..db.connection_pool import get_database_pool
            
            db = get_database_pool()
            
            # Get recent memories for this user (last 100) to check for duplicates
            recent_memories = await db.fetch(
                """
                SELECT content, metadata->>'extraction_class' as extraction_class,
                       created_at, importance_score
                FROM memories 
                WHERE user_id = $1 AND status = 'active'
                ORDER BY created_at DESC 
                LIMIT 100
                """,
                user_id
            )
            
            if not recent_memories:
                return False
            
            # Check for exact duplicates first (fast check)
            for memory in recent_memories:
                if memory['content'].strip().lower() == ext_text.strip().lower():
                    logger.debug(f"📍 Exact duplicate found: {ext_text[:40]}...")
                    return True
            
            # Check for semantic duplicates (more expensive)
            similar_memories = await self._find_similar_memories(ext_text, recent_memories, ext_class)
            
            if similar_memories:
                logger.info(f"📍 Similar memory found ({similar_memories[0]['similarity']:.2f} similarity): {ext_text[:40]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Deduplication check failed: {e}")
            return False  # If check fails, allow saving (better to have duplicate than lose memory)
    
    async def _find_similar_memories(self, ext_text: str, recent_memories: list, ext_class: str) -> list:
        """Find semantically similar memories using text similarity"""
        try:
            import difflib
            from datetime import datetime, timedelta
            
            similar_threshold = 0.85  # 85% similarity threshold
            similar_memories = []
            
            # Only check memories from the same extraction class for similarity
            same_class_memories = [
                m for m in recent_memories 
                if m.get('extraction_class') == ext_class
            ]
            
            # Prioritize recent memories (weight by recency)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            for memory in same_class_memories:
                # Skip very old memories for similarity checking
                if memory['created_at'] < cutoff_date:
                    continue
                
                # Calculate text similarity
                similarity = difflib.SequenceMatcher(
                    None, 
                    ext_text.lower().strip(), 
                    memory['content'].lower().strip()
                ).ratio()
                
                if similarity >= similar_threshold:
                    similar_memories.append({
                        'content': memory['content'],
                        'similarity': similarity,
                        'created_at': memory['created_at']
                    })
            
            # Sort by similarity (highest first)
            similar_memories.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similar_memories
            
        except Exception as e:
            logger.error(f"Similar memory search failed: {e}")
            return []
    
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
                return f"Valuable professional experience ({years} years) that indicates skill level and context"
            else:
                return "Professional experience that indicates user's skill level and background"
        
        elif "business" in ext_class.lower() or "company" in ext_class.lower():
            return "Business context that helps tailor recommendations and understand user's environment"
        
        elif "tool" in ext_class.lower():
            tool_name = attrs.get("tool") or attrs.get("preferred") or attrs.get("technology")
            if tool_name:
                return f"Tool preference ({tool_name}) that influences technical recommendations"
            else:
                return "Tool preference that guides technical suggestions and workflow advice"
        
        elif ext_class in ["user_standards", "policy", "guideline", "rule"]:
            return "User's standards or policies that must be respected in future interactions"
        
        elif "workflow" in ext_class.lower() or "process" in ext_class.lower():
            return "User's established workflow that should be considered in recommendations"
        
        else:
            # Generic fallback based on content analysis
            if any(word in ext_text.lower() for word in ["always", "never", "prefer", "love", "hate"]):
                return "Strong user preference that should influence future recommendations"
            elif any(word in ext_text.lower() for word in ["specialize", "expert", "years", "experience"]):
                return "Professional context that helps determine appropriate interaction style"
            elif any(word in ext_text.lower() for word in ["company", "team", "organization"]):
                return "Professional environment context that informs business-appropriate responses"
            else:
                return "Lasting user information that provides valuable context for personalized assistance"

# Global memory extractor instance
_memory_extractor = None

def get_memory_extractor():
    """Get or create global memory extractor instance"""
    global _memory_extractor
    if _memory_extractor is None:
        _memory_extractor = MemoryExtractor()
    return _memory_extractor