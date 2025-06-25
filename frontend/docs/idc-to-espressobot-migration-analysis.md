# IDC to EspressoBot Multi-Agent System Migration Analysis

## Executive Summary

This document analyzes the system prompt structure from ~/idc/CLAUDE.md and provides a comprehensive migration plan for the multi-agent EspressoBot system. The goal is to ensure each specialized agent has access to all critical information without losing any capabilities.

## Current System Analysis

### 1. IDC System Structure (~/idc/CLAUDE.md)

The IDC system is a monolithic assistant with:
- **Single comprehensive prompt** containing all Shopify operations knowledge
- **25+ Python tools** for various operations
- **Extensive domain knowledge** about iDrinkCoffee.com specifics
- **Task management** capabilities (Taskwarrior integration)
- **Detailed workflows** for common operations
- **Product guidelines** in separate documentation files

### 2. EspressoBot Current Structure

#### Frontend (Custom Tools) - `/home/pranav/espressobot/frontend`
- Single system prompt at `/server/espresso-system-prompt.txt`
- Custom tool implementations without MCP
- Task management with todo tools
- Unified orchestrator architecture

#### Backend (Multi-Agent) - `/home/pranav/espressobot/espressobot-v2`
- 7 specialized agents using OpenAI Agents SDK
- Native Python tool imports
- Agent-specific instructions embedded in Python files
- Context management system

## Migration Requirements

### 1. Core Knowledge to Preserve

#### A. Domain-Specific Knowledge
- iDrinkCoffee.com business rules
- Product naming conventions
- Tagging system
- Metafields structure
- Channel IDs and pricelists
- Special operations (preorders, MAP sales, etc.)

#### B. Technical Knowledge
- GraphQL mutation patterns
- Tool usage best practices
- Error handling approaches
- Bulk operation strategies
- Feature management (metaobjects vs JSON)

#### C. Operational Workflows
- Product creation process
- Open box listing creation
- Combo product generation
- Bulk price updates
- Inventory management
- SkuVault integration

### 2. Agent-Specific Knowledge Distribution

#### Triage Agent
- Overview of all capabilities
- Routing logic and patterns
- Common request types
- When to use Task Manager

#### Product Search Agent
- Shopify query syntax
- Search optimization techniques
- Product browsing patterns
- Perplexity integration for research

#### Product Editor Agent
- Tag management rules
- Pricing update patterns
- Status management
- MAP pricing specifics
- Variant linking

#### Product Creator Agent
- Product naming conventions
- Required metafields
- Tag requirements
- Feature box creation
- Open box and combo creation patterns

#### Inventory Manager Agent
- Inventory policy rules
- SkuVault sync procedures
- Bulk operations
- Cost management
- Warehouse integration

#### Analytics & Orders Agent
- GraphQL query patterns
- Report generation
- Data extraction techniques
- Custom analysis capabilities

#### Task Manager Agent
- Multi-step operation patterns
- Task breakdown strategies
- Progress tracking
- Bulk operation coordination

## Migration Strategy

### 1. Shared Knowledge Base

Create a shared knowledge module that all agents can access:

```python
# shared_knowledge.py
SHOPIFY_KNOWLEDGE = {
    "conventions": {
        "product_naming": "Format: {Brand} {Product Name} {Descriptors}",
        "open_box_sku": "OB-{YYMM}-{Serial}-{OriginalSKU}",
        "combo_sku": "{Prefix}-{Serial}-{Suffix}",
        # ... more conventions
    },
    "channels": {
        "online_store": "gid://shopify/Channel/46590273",
        "point_of_sale": "gid://shopify/Channel/46590337",
        # ... all channels
    },
    "special_operations": {
        "preorder": {
            "add_tags": ["preorder-2-weeks", "shipping-nis-{Month}"],
            "inventory_policy": "CONTINUE"
        },
        # ... more operations
    },
    "metafields": {
        # Complete metafield reference
    },
    "tags": {
        # Complete tag system
    }
}
```

### 2. Agent Instruction Enhancement

Each agent's instructions should be enhanced with:

#### A. Base Template
```python
BASE_INSTRUCTIONS = """
You are the {agent_role} for EspressoBot, the friendly and meticulous Shopify assistant for iDrinkCoffee.com.

## Core Principles:
1. Always verify before modifying (use get_product first)
2. Never guess - use documentation tools when unsure
3. Maintain Canadian English spelling
4. Create products in DRAFT status
5. Include COGS for all products

## iDrinkCoffee.com Specifics:
{domain_specific_knowledge}

## Your Specialized Capabilities:
{agent_specific_capabilities}

## Common Patterns:
{relevant_workflows}

## Hand-off Guidelines:
{when_to_transfer}
"""
```

#### B. Agent-Specific Sections

For each agent, include relevant sections from the IDC CLAUDE.md:
- Relevant tool documentation
- Specific workflows
- Domain knowledge pertinent to their role
- Error handling patterns

### 3. Context Enrichment

Enhance the ShopifyAgentContext to carry:
```python
class EnhancedShopifyAgentContext:
    # Existing fields
    conversation_id: str
    messages: list
    
    # New fields for knowledge preservation
    session_cache: dict  # For caching product lookups
    active_tasks: list   # For task tracking
    domain_knowledge: dict  # Loaded from shared knowledge
    workflow_state: dict  # For multi-step operations
```

### 4. Tool Documentation Integration

Each agent should have access to relevant tool documentation:

```python
# In each agent file
TOOL_DOCS = {
    "search_products": """
    Search for products using Shopify query syntax.
    Examples:
    - title:*coffee* - Products with "coffee" in title
    - vendor:Lavazza - All Lavazza products
    - tag:sale AND status:active - Active sale items
    """,
    # ... more tool docs
}
```

### 5. Workflow Preservation

Convert key workflows into agent-specific guides:

```python
# workflows/product_creation.py
PRODUCT_CREATION_WORKFLOW = """
1. Search for existing products to avoid duplicates
2. Create product in DRAFT status with required fields
3. Add metafields (buy box, technical specs)
4. Create feature boxes (as metaobjects)
5. Add appropriate tags
6. Set inventory policy
7. Configure channels
8. Review and activate when ready
"""
```

## Implementation Plan

### Phase 1: Knowledge Extraction (Week 1)
1. Extract all domain knowledge from IDC CLAUDE.md
2. Create shared knowledge modules
3. Document all workflows and patterns
4. Map knowledge to appropriate agents

### Phase 2: Agent Enhancement (Week 2)
1. Update each agent's instructions with relevant knowledge
2. Add shared knowledge imports
3. Enhance context handling
4. Test individual agent capabilities

### Phase 3: Integration Testing (Week 3)
1. Test agent handoffs with enriched knowledge
2. Verify workflow completeness
3. Test edge cases and special operations
4. Performance optimization

### Phase 4: Documentation (Week 4)
1. Create agent-specific documentation
2. Update system documentation
3. Create migration guide for users
4. Training materials

## Risk Mitigation

### 1. Knowledge Loss Prevention
- Create comprehensive test suite covering all IDC capabilities
- Maintain backward compatibility where possible
- Document any behavioral changes

### 2. Performance Considerations
- Lazy load knowledge modules
- Cache frequently accessed data
- Optimize agent instructions for token efficiency

### 3. Consistency Maintenance
- Central knowledge repository
- Version control for knowledge updates
- Regular synchronization checks

## Validation Checklist

- [ ] All 25+ tools documented and accessible
- [ ] All workflows preserved and distributed
- [ ] Domain knowledge available to relevant agents
- [ ] Special operations (preorders, MAP, etc.) handled
- [ ] Metafield system fully documented
- [ ] Tag system complete and accessible
- [ ] Channel configurations preserved
- [ ] Error handling patterns maintained
- [ ] Task management capabilities retained
- [ ] GraphQL patterns documented

## Conclusion

The migration from IDC's monolithic system to EspressoBot's multi-agent architecture requires careful knowledge distribution while maintaining the comprehensive capabilities. By creating a shared knowledge base, enhancing agent instructions, and preserving workflows, we can ensure each specialized agent has the information needed to excel at their specific role while maintaining the system's overall capabilities.

The key is to balance specialization with comprehensive knowledge access, ensuring no capability is lost in the transition while gaining the benefits of a more scalable, maintainable multi-agent architecture.