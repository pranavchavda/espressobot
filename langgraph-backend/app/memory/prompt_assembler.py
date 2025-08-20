"""Intelligent Prompt Assembly with GPT-5 for context consolidation"""

import os
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import asyncio
from openai import AsyncOpenAI

from .postgres_memory_manager import Memory, PromptFragment, SearchResult
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

class ContextTier(Enum):
    """Context tiers for different complexity levels"""
    CORE = "core"          # Essential context only
    STANDARD = "standard"   # Standard context
    FULL = "full"          # Complete context

@dataclass
class AssembledPrompt:
    """Result of prompt assembly"""
    system_prompt: str
    context_summary: str
    relevant_memories: List[Memory]
    prompt_fragments: List[PromptFragment]
    context_tier: ContextTier
    token_estimate: int
    consolidation_applied: bool = False

class PromptAssembler:
    """Intelligent prompt assembly using GPT-5 for consolidation"""
    
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.embedding_service = get_embedding_service()
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Token limits for different tiers
        self.tier_limits = {
            ContextTier.CORE: 2000,
            ContextTier.STANDARD: 4000,
            ContextTier.FULL: 8000
        }
        
        # Base system prompts for different agent types
        self.base_prompts = {
            "general": "You are a helpful AI assistant focused on providing accurate and useful information.",
            "sales": "You are a sales assistant helping with product recommendations and sales processes.",
            "products": "You are a product management assistant helping with inventory and product information.",
            "pricing": "You are a pricing specialist helping with pricing strategies and analysis.",
            "media": "You are a media assistant helping with content creation and media management.",
            "integrations": "You are an integrations specialist helping with system connections and workflows."
        }
    
    async def assemble_prompt(self, user_query: str, user_id: str, 
                            agent_type: str = "general",
                            context_tier: ContextTier = ContextTier.STANDARD,
                            conversation_context: Optional[List[Dict]] = None) -> AssembledPrompt:
        """Assemble intelligent prompt with context consolidation"""
        
        # 1. Search for relevant memories
        relevant_memories = await self._search_relevant_memories(
            user_query, user_id, context_tier
        )
        
        # 2. Get relevant prompt fragments
        # TODO: Re-enable when prompt_fragments table has vector type
        prompt_fragments = []  # Temporarily disabled until prompt_fragments uses vector type
        # prompt_fragments = await self._get_prompt_fragments(
        #     user_query, agent_type, context_tier
        # )
        
        # 3. Determine if consolidation is needed
        estimated_tokens = self._estimate_tokens(relevant_memories, prompt_fragments, conversation_context)
        tier_limit = self.tier_limits[context_tier]
        
        consolidation_applied = False
        if estimated_tokens > tier_limit:
            # Apply GPT-5 consolidation
            relevant_memories, prompt_fragments = await self._consolidate_context(
                relevant_memories, prompt_fragments, user_query, tier_limit
            )
            consolidation_applied = True
        
        # 4. Build final prompt
        system_prompt = await self._build_system_prompt(
            agent_type, prompt_fragments, relevant_memories
        )
        
        # 5. Create context summary
        context_summary = await self._create_context_summary(
            relevant_memories, conversation_context
        )
        
        final_token_estimate = self._estimate_tokens(relevant_memories, prompt_fragments, conversation_context)
        
        return AssembledPrompt(
            system_prompt=system_prompt,
            context_summary=context_summary,
            relevant_memories=relevant_memories,
            prompt_fragments=prompt_fragments,
            context_tier=context_tier,
            token_estimate=final_token_estimate,
            consolidation_applied=consolidation_applied
        )
    
    async def _search_relevant_memories(self, query: str, user_id: str, 
                                      context_tier: ContextTier) -> List[Memory]:
        """Search for relevant memories based on context tier"""
        
        # Adjust search parameters based on tier
        tier_params = {
            ContextTier.CORE: {"limit": 5, "threshold": 0.3},  # Lowered from 0.8
            ContextTier.STANDARD: {"limit": 10, "threshold": 0.25},  # Lowered from 0.7
            ContextTier.FULL: {"limit": 20, "threshold": 0.2}  # Lowered from 0.6
        }
        
        params = tier_params[context_tier]
        
        try:
            search_results = await self.memory_manager.search_memories(
                user_id=user_id,
                query=query,
                limit=params["limit"],
                similarity_threshold=params["threshold"]
            )
            
            return [result.memory for result in search_results]
        except Exception as e:
            logger.error(f"Failed to search memories: {str(e)[:500]}")
            logger.debug(f"Search params - user_id: {user_id}, query: {query[:100]}, limit: {params['limit']}, threshold: {params['threshold']}")
            return []
    
    async def _get_prompt_fragments(self, query: str, agent_type: str,
                                  context_tier: ContextTier) -> List[PromptFragment]:
        """Get relevant prompt fragments for the agent and context tier"""
        
        # Generate query embedding for similarity search
        try:
            embedding_result = await self.embedding_service.get_embedding(query)
            query_embedding = embedding_result.embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for prompt fragments: {e}")
            return []
        
        # Search for relevant fragments
        # Note: Simplified query - prompt_fragments table may not have embeddings yet
        search_query = """
        SELECT id, category, priority, content, tags, agent_type, context_tier, 
               is_active, created_at, updated_at
        FROM prompt_fragments 
        WHERE (agent_type = $2 OR agent_type IS NULL)
          AND context_tier = $3
          AND is_active = true
        ORDER BY priority DESC
        LIMIT 10
        """
        
        try:
            results = await self.memory_manager._execute_query(
                search_query, agent_type, context_tier.value
            )
            
            fragments = []
            for row in results:
                fragment = PromptFragment(
                    id=row['id'],
                    category=row['category'],
                    priority=row['priority'],
                    content=row['content'],
                    tags=row['tags'] or [],
                    agent_type=row['agent_type'],
                    context_tier=row['context_tier'],
                    is_active=row['is_active'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                fragments.append(fragment)
            
            return fragments
        except Exception as e:
            logger.error(f"Failed to get prompt fragments: {e}")
            return []
    
    async def _consolidate_context(self, memories: List[Memory], 
                                 fragments: List[PromptFragment],
                                 user_query: str, token_limit: int) -> Tuple[List[Memory], List[PromptFragment]]:
        """Use GPT-4.1-nano to consolidate context intelligently"""
        
        # Prepare context for consolidation
        memories_text = "\n".join([f"Memory {i+1}: {mem.content}" for i, mem in enumerate(memories)])
        fragments_text = "\n".join([f"Fragment {i+1} ({frag.category}): {frag.content}" 
                                  for i, frag in enumerate(fragments)])
        
        consolidation_prompt = f"""
You are an AI context consolidation specialist. Your task is to intelligently reduce the following context while preserving the most relevant information for the user query.

User Query: "{user_query}"
Token Limit: {token_limit}

MEMORIES TO CONSOLIDATE:
{memories_text}

PROMPT FRAGMENTS TO CONSOLIDATE:
{fragments_text}

Instructions:
1. Identify the most relevant memories and fragments for the user query
2. Consolidate similar or redundant information
3. Preserve key facts, preferences, and context
4. Return a JSON response with consolidated content

Response format:
{{
    "consolidated_memories": [
        {{"content": "consolidated memory content", "importance": 0.9, "original_ids": [1, 3]}},
        ...
    ],
    "consolidated_fragments": [
        {{"content": "consolidated fragment content", "category": "category", "original_ids": [1, 2]}},
        ...
    ],
    "reasoning": "Brief explanation of consolidation decisions"
}}
"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": consolidation_prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            consolidation_result = json.loads(response.choices[0].message.content)
            
            # Create consolidated memories
            consolidated_memories = []
            for mem_data in consolidation_result.get("consolidated_memories", []):
                memory = Memory(
                    content=mem_data["content"],
                    importance_score=mem_data.get("importance", 1.0),
                    metadata={"consolidated": True, "original_ids": mem_data.get("original_ids", [])}
                )
                consolidated_memories.append(memory)
            
            # Create consolidated fragments
            consolidated_fragments = []
            for frag_data in consolidation_result.get("consolidated_fragments", []):
                fragment = PromptFragment(
                    content=frag_data["content"],
                    category=frag_data.get("category", "consolidated"),
                    priority=10  # High priority for consolidated content
                )
                consolidated_fragments.append(fragment)
            
            logger.info(f"Context consolidated: {len(memories)} → {len(consolidated_memories)} memories, "
                       f"{len(fragments)} → {len(consolidated_fragments)} fragments")
            
            return consolidated_memories, consolidated_fragments
            
        except Exception as e:
            logger.error(f"Context consolidation failed: {e}")
            # Fallback: simple truncation
            return memories[:3], fragments[:3]
    
    async def _build_system_prompt(self, agent_type: str, fragments: List[PromptFragment],
                                 memories: List[Memory]) -> str:
        """Build comprehensive system prompt"""
        
        base_prompt = self.base_prompts.get(agent_type, self.base_prompts["general"])
        
        # Add fragments by category
        fragments_by_category = {}
        for fragment in fragments:
            category = fragment.category
            if category not in fragments_by_category:
                fragments_by_category[category] = []
            fragments_by_category[category].append(fragment.content)
        
        # Build system prompt sections
        prompt_sections = [base_prompt]
        
        if fragments_by_category:
            prompt_sections.append("\nADDITIONAL GUIDELINES:")
            for category, contents in fragments_by_category.items():
                prompt_sections.append(f"\n{category.upper()}:")
                for content in contents:
                    prompt_sections.append(f"- {content}")
        
        if memories:
            prompt_sections.append(f"\nRELEVANT CONTEXT ({len(memories)} items):")
            for i, memory in enumerate(memories[:5], 1):  # Limit to top 5 memories
                prompt_sections.append(f"{i}. {memory.content}")
        
        return "\n".join(prompt_sections)
    
    async def _create_context_summary(self, memories: List[Memory],
                                    conversation_context: Optional[List[Dict]] = None) -> str:
        """Create context summary for the conversation"""
        
        summary_parts = []
        
        if memories:
            summary_parts.append(f"Found {len(memories)} relevant memories from past interactions.")
            
            # Group by category if available
            categories = {}
            for memory in memories:
                cat = memory.category or "general"
                if cat not in categories:
                    categories[cat] = 0
                categories[cat] += 1
            
            if len(categories) > 1:
                cat_summary = ", ".join([f"{count} {cat}" for cat, count in categories.items()])
                summary_parts.append(f"Categories: {cat_summary}.")
        
        if conversation_context:
            summary_parts.append(f"Conversation includes {len(conversation_context)} previous messages.")
        
        return " ".join(summary_parts) if summary_parts else "No additional context available."
    
    def _estimate_tokens(self, memories: List[Memory], fragments: List[PromptFragment],
                        conversation_context: Optional[List[Dict]] = None) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        
        total_chars = 0
        
        # Count memory content
        for memory in memories:
            total_chars += len(memory.content)
        
        # Count fragment content  
        for fragment in fragments:
            total_chars += len(fragment.content)
        
        # Count conversation context
        if conversation_context:
            for msg in conversation_context:
                total_chars += len(str(msg))
        
        return total_chars // 4  # Rough token estimate
    
    async def store_prompt_fragment(self, fragment: PromptFragment) -> int:
        """Store a new prompt fragment with embedding"""
        
        # Generate embedding
        embedding_result = await self.embedding_service.get_embedding(fragment.content)
        fragment.embedding = embedding_result.embedding
        
        # Store in database
        query = """
        INSERT INTO prompt_fragments (category, priority, content, tags, embedding, 
                                    agent_type, context_tier, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """
        
        result = await self.memory_manager._execute_one(
            query,
            fragment.category,
            fragment.priority,
            fragment.content,
            fragment.tags,
            fragment.embedding,
            fragment.agent_type,
            fragment.context_tier,
            fragment.is_active
        )
        
        fragment_id = result['id']
        logger.info(f"Stored prompt fragment {fragment_id} for agent {fragment.agent_type}")
        return fragment_id
    
    async def update_prompt_fragment(self, fragment_id: int, **updates) -> bool:
        """Update existing prompt fragment"""
        
        if not updates:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        param_idx = 1
        
        for field, value in updates.items():
            if field in ['category', 'priority', 'content', 'tags', 'agent_type', 'context_tier', 'is_active']:
                set_clauses.append(f"{field} = ${param_idx}")
                values.append(value)
                param_idx += 1
        
        if 'content' in updates:
            # Regenerate embedding if content changed
            embedding_result = await self.embedding_service.get_embedding(updates['content'])
            set_clauses.append(f"embedding = ${param_idx}")
            values.append(embedding_result.embedding)
            param_idx += 1
        
        set_clauses.append(f"updated_at = CURRENT_TIMESTAMP")
        values.append(fragment_id)
        
        query = f"""
        UPDATE prompt_fragments 
        SET {', '.join(set_clauses)}
        WHERE id = ${param_idx}
        """
        
        result = await self.memory_manager._execute_command(query, *values)
        return "UPDATE 1" in str(result)
    
    async def get_fragment_stats(self) -> Dict[str, Any]:
        """Get prompt fragment statistics"""
        
        stats_query = """
        SELECT 
            COUNT(*) as total_fragments,
            COUNT(DISTINCT category) as categories,
            COUNT(DISTINCT agent_type) as agent_types,
            AVG(priority) as avg_priority,
            COUNT(*) FILTER (WHERE is_active = true) as active_fragments
        FROM prompt_fragments
        """
        
        result = await self.memory_manager._execute_one(stats_query)
        
        return {
            "total_fragments": result['total_fragments'],
            "categories": result['categories'],
            "agent_types": result['agent_types'],
            "avg_priority": float(result['avg_priority']) if result['avg_priority'] else 0.0,
            "active_fragments": result['active_fragments']
        }