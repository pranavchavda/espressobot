"""
Dynamic Agent Implementation
Loads agent configuration from database at runtime
"""

from typing import Dict, Any, List, Optional
from app.agents.base import BaseAgent
from app.tools.mcp_client import get_mcp_manager
import logging
import json

logger = logging.getLogger(__name__)


class DynamicAgent(BaseAgent):
    """Agent created dynamically from database configuration"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize from database configuration
        
        Args:
            config: Dictionary containing agent configuration from database
        """
        self.config = config
        
        # Store additional configuration FIRST (before super().__init__)
        self.capabilities = config.get('capabilities', [])
        self.routing_keywords = config.get('routing_keywords', [])
        self.example_queries = config.get('example_queries', [])
        self.mcp_servers = config.get('mcp_servers', [])
        
        # Store model configuration before calling super()
        self.model_provider = config.get('model_provider', 'openai')
        self.model_name = config.get('model_name', 'gpt-4o-mini')
        
        # Handle temperature safely
        temp_config = config.get('temperature')
        if temp_config is not None and isinstance(temp_config, dict):
            self.temperature = temp_config.get('value', 0.0)
        elif temp_config is not None and isinstance(temp_config, (int, float)):
            self.temperature = temp_config
        else:
            self.temperature = 0.0
            
        self.max_tokens = config.get('max_tokens', 2048)
        
        super().__init__(
            name=config['name'],
            description=config['description'],
            temperature=self.temperature
        )
        
        # Override the model with dynamic agent specific configuration
        self._create_dynamic_model()
        
        # Initialize basic tools (MCP tools will be loaded async)
        self.tools = self._get_tools()
        self._mcp_tools_loaded = False
        self._loaded_user_servers = set()
        self._react_agent = None
        self._react_recursion_limit = int(self.config.get("react_recursion_limit", 4))
        
        logger.info(f"Initialized dynamic agent: {self.name}")
    
    def _create_dynamic_model(self):
        """Create model with proper parameters for dynamic agent configuration"""
        from app.config.llm_factory import llm_factory, Provider
        from app.config.agent_model_manager import AgentModelManager
        
        try:
            # Map provider strings to Provider enum
            provider_map = {
                "openrouter": Provider.OPENROUTER,
                "openai": Provider.OPENAI,
                "anthropic": Provider.ANTHROPIC
            }
            
            preferred_provider = provider_map.get(self.model_provider, Provider.OPENROUTER)
            
            # Create agent model manager instance and get proper parameters
            agent_model_manager = AgentModelManager()
            model_params = agent_model_manager._get_model_parameters(
                self.model_name, 
                self.temperature,
                self.max_tokens,
                preferred_provider
            )
            
            # Convert max_completion_tokens to max_tokens for create_llm()
            create_params = model_params.copy()
            if 'max_completion_tokens' in create_params:
                create_params['max_tokens'] = create_params.pop('max_completion_tokens')
            
            # Create model using factory with proper parameters
            self.model = llm_factory.create_llm(
                model_name=self.model_name,
                preferred_provider=preferred_provider,
                **create_params
            )
            
            logger.info(f"Dynamic agent {self.name} created model {self.model_name} with params: {model_params}")
            
        except Exception as e:
            logger.error(f"Failed to create dynamic model for {self.name}: {e}")
            # Fall back to Claude as safe default
            from langchain_anthropic import ChatAnthropic
            import os
            self.model = ChatAnthropic(
                model="claude-3-5-haiku-20241022",
                temperature=self.temperature,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            logger.info(f"Dynamic agent {self.name} fell back to Claude 3.5 Haiku")
    
    def _get_system_prompt(self) -> str:
        """Return the system prompt from configuration"""
        base_prompt = self.config.get('system_prompt', '')
        
        # Add capabilities to prompt if defined
        if self.capabilities:
            capabilities_text = "\n".join([f"- {cap}" for cap in self.capabilities])
            base_prompt += f"\n\nYour capabilities:\n{capabilities_text}"
        
        # Add example queries if defined
        if self.example_queries:
            examples_text = "\n".join([f"- {ex}" for ex in self.example_queries])
            base_prompt += f"\n\nExample queries you can handle:\n{examples_text}"
        
        return base_prompt
    
    def _get_tools(self) -> List[Any]:
        """Load basic tools based on configuration (non-MCP)"""
        tools = []
        
        # Load configured tools
        tool_configs = self.config.get('tools', [])
        for tool_config in tool_configs:
            try:
                tool = self._load_tool(tool_config)
                if tool:
                    tools.append(tool)
            except Exception as e:
                logger.error(f"Failed to load tool {tool_config}: {e}")
        
        return tools

    async def _ensure_react_agent(self):
        """Create a LangGraph ReAct agent if we have callable tools (LangChain Tools)."""
        if self._react_agent is not None:
            return
        try:
            from langgraph.prebuilt import create_react_agent
            # Filter only LangChain Tool objects (dicts come from MCP list_tools)
            callable_tools = [t for t in (self.tools or []) if hasattr(t, "invoke") or hasattr(t, "coroutine")]
            if callable_tools:
                self._react_agent = create_react_agent(
                    self.model,
                    callable_tools,
                    prompt=self._get_system_prompt()
                )
                logger.info(f"Initialized ReAct agent for dynamic agent {self.name} with {len(callable_tools)} callable tools")
        except Exception as e:
            logger.error(f"Failed to create ReAct agent for {self.name}: {e}")
    
    async def _load_mcp_tools(self):
        """Load MCP tools asynchronously"""
        if self._mcp_tools_loaded:
            return
            
        # Load MCP servers if configured
        if self.mcp_servers:
            try:
                # Get MCP manager for built-in servers
                mcp_manager = await get_mcp_manager()
                built_in_servers = ["products", "pricing", "inventory", "sales", "features", 
                                  "media", "integrations", "product_management", "utility", 
                                  "graphql", "orders"]
                
                for server_name in self.mcp_servers:
                    if server_name in built_in_servers:
                        # Load from built-in MCP servers
                        server_tools = await mcp_manager.get_tools_for_agent(server_name)
                        self.tools.extend(server_tools)
                        logger.info(f"Loaded {len(server_tools)} tools from built-in MCP server: {server_name}")
                    else:
                        # For user-defined servers, we'll handle them differently to avoid event loop issues
                        # Instead of loading tools here, we'll mark them as available
                        logger.info(f"User-defined MCP server '{server_name}' configured (tools will be loaded on-demand)")
                
                self._mcp_tools_loaded = True
            except Exception as e:
                logger.error(f"Failed to load MCP tools: {e}")
    
    async def _load_user_mcp_server(self, server_name: str, db_session=None):
        """Load tools from a user-defined MCP server.

        If db_session is provided, uses it to avoid cross-event-loop issues.
        """
        try:
            logger.info(f"🔧 Starting to load user-defined MCP server: {server_name}")
            
            from app.services.user_mcp_service import UserMCPService
            session_ctx = None
            session = db_session
            # If no session provided, try to create one (may fail across loops)
            if session is None:
                logger.warning("No db_session provided; creating new AsyncSessionLocal may cause event loop issues")
                from app.database.session import AsyncSessionLocal
                session_ctx = AsyncSessionLocal()
                session = session_ctx

            # Get user MCP service
            logger.info(f"🔧 Creating UserMCPService instance")
            mcp_service = UserMCPService()

            try:
                # Get server configuration (default user_id=1 for now)
                logger.info(f"🔧 Looking up server configuration for: {server_name}")
                server_config = await mcp_service.get_server_by_name(session, server_name, user_id=1)
                if not server_config:
                    logger.warning(f"User-defined MCP server '{server_name}' not found in database")
                    return []
                
                logger.info(f"🔧 Found server config: {server_config}")
                
                # Test connection and get tools
                logger.info(f"🔧 Testing connection to server: {server_name}")
                test_result = await mcp_service.test_mcp_server(session, server_config)
                logger.info(f"🔧 Test result: {test_result}")
                
                if not test_result.get('success'):
                    logger.error(f"Failed to connect to user-defined MCP server '{server_name}': {test_result.get('error')}")
                    return []
                
                # Extract tools from test result if available
                mcp_tools = test_result.get('tools', [])
                if mcp_tools:
                    # Convert MCP tools to LangChain tools
                    langchain_tools = []
                    for mcp_tool in mcp_tools:
                        try:
                            lc_tool = self._convert_mcp_to_langchain_tool(mcp_tool, server_config)
                            langchain_tools.append(lc_tool)
                            logger.info(f"✅ Converted MCP tool '{mcp_tool['name']}' to LangChain tool")
                        except Exception as e:
                            logger.error(f"Failed to convert MCP tool '{mcp_tool.get('name', 'unknown')}': {e}")
                    
                    logger.info(f"Successfully loaded {len(langchain_tools)} LangChain tools from user-defined MCP server '{server_name}'")
                    return langchain_tools
                else:
                    logger.info(f"Successfully connected to user-defined MCP server '{server_name}', but no tools available")
                    return []
            finally:
                if session_ctx is not None:
                    await session_ctx.close()
                
        except Exception as e:
            logger.error(f"Failed to load user-defined MCP server '{server_name}': {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []
    
    def _convert_mcp_to_langchain_tool(self, mcp_tool_def: Dict[str, Any], server_config: Dict[str, Any]) -> Any:
        """Convert MCP tool definition to a LangChain StructuredTool with proper args schema.

        - Maps MCP JSON Schema (inputSchema) to a Pydantic model
        - Delegates execution to UserMCPService (supports stdio and HTTP)
        """
        from langchain_core.tools import StructuredTool
        import json
        from pydantic import create_model, Field
        from typing import Any as TypingAny, Dict as TypingDict, List as TypingList
        from app.services.user_mcp_service import UserMCPService

        tool_name = mcp_tool_def['name']
        tool_description = mcp_tool_def.get('description', f"User MCP tool: {tool_name}")
        server_id = server_config.get('id')

        # Prefer inputSchema; some servers include a fallback 'schema'
        input_schema = mcp_tool_def.get('inputSchema') or mcp_tool_def.get('schema') or {}

        def _map_json_type(t: str):
            t = (t or '').lower()
            if t == 'string':
                return str
            if t == 'number' or t == 'integer':
                return float
            if t == 'boolean':
                return bool
            if t == 'array':
                return TypingList[TypingAny]
            if t == 'object':
                return TypingDict[str, TypingAny]
            return TypingAny

        # Build Pydantic args model from JSON schema
        fields = {}
        if isinstance(input_schema, dict) and input_schema.get('type') == 'object':
            props = input_schema.get('properties', {}) or {}
            required = set(input_schema.get('required', []) or [])
            for pname, pdef in props.items():
                ptype = _map_json_type(pdef.get('type'))
                desc = pdef.get('description')
                default = pdef.get('default', ... if pname in required else None)
                # If required and no default, use Ellipsis to enforce
                default_val = default if default is not None else (... if pname in required else None)
                fields[pname] = (ptype, Field(default_val, description=desc))

        ArgsModel = create_model(
            f"{tool_name.title().replace('-', '').replace(' ', '')}Args",
            **fields
        ) if fields else None

        async def tool_function(**kwargs):
            """Execute MCP tool call via the UserMCPService abstraction"""
            try:
                if not server_config:
                    raise Exception("Missing server configuration for user MCP server")

                svc = UserMCPService()
                result = await svc.execute_tool_with_config(
                    server_config=server_config,
                    tool_name=tool_name,
                    input_data=kwargs
                )

                if not result.get('success'):
                    raise Exception(result.get('error', 'Unknown MCP execution error'))

                output = result.get('output')
                # Try to extract standard MCP content if present
                if isinstance(output, dict):
                    if 'result' in output and isinstance(output['result'], dict):
                        res = output['result']
                        content = res.get('content')
                        if isinstance(content, list) and content:
                            first = content[0]
                            if isinstance(first, dict) and 'text' in first:
                                return first['text']
                        # Fallback to string dump
                        return json.dumps(res)
                    # Fallback
                    return json.dumps(output)
                # If it's already a string or other type
                return str(output)
            except Exception as e:
                logger.error(f"Error calling MCP tool {tool_name}: {e}")
                return f"Error calling {tool_name}: {str(e)}"

        if ArgsModel is not None:
            return StructuredTool(
                name=tool_name,
                description=tool_description,
                coroutine=tool_function,  # async execution
                args_schema=ArgsModel
            )
        # Fallback if no schema was provided
        return StructuredTool(
            name=tool_name,
            description=tool_description,
            coroutine=tool_function
        )
    
    async def __call__(self, state: Dict[str, Any], **kwargs) -> Any:
        """Execute the agent with async MCP loading. Expects full state dict."""
        msg_count = len(state.get("messages", [])) if isinstance(state, dict) else 0
        logger.info(f"🚀 Dynamic agent {self.name} called with {msg_count} messages")

        # Ensure MCP tools are loaded (built-ins)
        if not self._mcp_tools_loaded and self.mcp_servers:
            await self._load_mcp_tools()

        # Load user-defined MCP server tools if configured
        if hasattr(self, 'mcp_servers') and self.mcp_servers:
            user_servers = [s for s in self.mcp_servers if s not in [
                "products", "pricing", "inventory", "sales", "features",
                "media", "integrations", "product_management", "utility",
                "graphql", "orders"
            ]]
            if user_servers:
                to_load = [s for s in user_servers if s not in self._loaded_user_servers]
                if to_load:
                    logger.info(f"🔧 Dynamic agent {self.name} will defer loading user MCP servers to factory/preload: {to_load}")
                    logger.info("Provide db_session during agent creation to preload user MCP tools and avoid event loop issues.")

        # If we have a ReAct agent with callable tools, use it to enable tool execution
        await self._ensure_react_agent()
        if self._react_agent is not None:
            try:
                # Run the react agent with current messages
                agent_state = {"messages": state.get("messages", [])}
                # Cap the number of LLM planning steps to reduce extra calls
                result = await self._react_agent.ainvoke(agent_state, {"recursion_limit": self._react_recursion_limit})
                if result.get("messages"):
                    # Append the last AI message from the result
                    from langchain_core.messages import AIMessage
                    agent_messages = result["messages"]
                    for msg in reversed(agent_messages):
                        if hasattr(msg, 'content') and msg.content:
                            state.setdefault("messages", []).append(AIMessage(content=msg.content, metadata={"agent": self.name}))
                            break
                state["last_agent"] = self.name
                return state
            except Exception as e:
                logger.error(f"Error running ReAct agent for {self.name}: {e}")
                # Fall back to base behavior
                return await super().__call__(state, **kwargs)

        # Default: Call parent implementation with full state
        return await super().__call__(state, **kwargs)
    
    def _load_tool(self, tool_config: Dict[str, Any]):
        """Load a single tool based on its configuration"""
        tool_type = tool_config.get('type')
        
        if tool_type == 'mcp':
            # Load MCP tool
            tool_name = tool_config.get('name')
            server_name = tool_config.get('server')
            # Implementation would fetch from MCP
            return None  # Placeholder
        
        elif tool_type == 'function':
            # Load function-based tool
            # Could dynamically import or use pre-registered functions
            return None  # Placeholder
        
        elif tool_type == 'api':
            # Create API-based tool
            # Could create HTTP request tools dynamically
            return None  # Placeholder
        
        else:
            logger.warning(f"Unknown tool type: {tool_type}")
            return None
    
    def _get_keywords(self) -> List[str]:
        """Return keywords for routing and capability matching"""
        keywords = []
        keywords.extend(self.routing_keywords)
        keywords.extend(self.capabilities)
        return keywords
    
    def can_handle(self, query: str) -> bool:
        """Check if this agent can handle the query based on keywords"""
        query_lower = query.lower()
        
        # Check routing keywords
        for keyword in self.routing_keywords:
            if keyword.lower() in query_lower:
                return True
        
        # Check capabilities
        for capability in self.capabilities:
            if any(word in query_lower for word in capability.lower().split()):
                return True
        
        return False


class DynamicAgentFactory:
    """Factory for creating dynamic agents from database"""
    
    @staticmethod
    async def create_from_database(db_session, agent_name: str) -> Optional[DynamicAgent]:
        """
        Create a dynamic agent from database configuration
        
        Args:
            db_session: Database session
            agent_name: Name of the agent to load
            
        Returns:
            DynamicAgent instance or None if not found
        """
        from sqlalchemy import select
        from app.database.models import DynamicAgent as DynamicAgentModel
        
        # Query database for agent configuration
        result = await db_session.execute(
            select(DynamicAgentModel).where(
                DynamicAgentModel.name == agent_name,
                DynamicAgentModel.is_active == True
            )
        )
        agent_model = result.scalar_one_or_none()
        
        if not agent_model:
            logger.warning(f"Dynamic agent not found: {agent_name}")
            return None
        
        # Convert model to configuration dict
        config = {
            'name': agent_model.name,
            'description': agent_model.description,
            'system_prompt': agent_model.system_prompt,
            'model_provider': agent_model.model_provider,
            'model_name': agent_model.model_name,
            'temperature': agent_model.temperature,
            'max_tokens': agent_model.max_tokens,
            'tools': agent_model.tools or [],
            'mcp_servers': agent_model.mcp_servers or [],
            'capabilities': agent_model.capabilities or [],
            'routing_keywords': agent_model.routing_keywords or [],
            'example_queries': agent_model.example_queries or []
        }
        
        # Create and return agent
        try:
            agent = DynamicAgent(config)

            # Preload user-defined MCP servers' tools using the provided DB session
            try:
                await agent_preload_user_servers(agent, db_session)
            except Exception as preload_err:
                logger.warning(f"Preloading user MCP tools failed for {agent_name}: {preload_err}")
            
            # Update usage count (initialize to 0 if None)
            if agent_model.usage_count is None:
                agent_model.usage_count = 0
            agent_model.usage_count += 1
            await db_session.commit()
            
            return agent
        except Exception as e:
            logger.error(f"Failed to create dynamic agent {agent_name}: {e}")
            
            # Update error in database
            agent_model.last_error = str(e)
            await db_session.commit()
            
            return None
    
    @staticmethod
    async def list_available_agents(db_session) -> List[Dict[str, Any]]:
        """List all available dynamic agents"""
        from sqlalchemy import select
        from app.database.models import DynamicAgent as DynamicAgentModel
        
        result = await db_session.execute(
            select(DynamicAgentModel).where(
                DynamicAgentModel.is_active == True
            )
        )
        agents = result.scalars().all()
        
        return [
            {
                'name': agent.name,
                'display_name': agent.display_name,
                'description': agent.description,
                'capabilities': agent.capabilities,
                'usage_count': agent.usage_count,
                'success_rate': agent.success_rate
            }
            for agent in agents
        ]

# Helper to preload user MCP servers for a dynamic agent with an existing DB session
async def agent_preload_user_servers(agent: DynamicAgent, db_session):
    if not hasattr(agent, 'mcp_servers') or not agent.mcp_servers:
        return
    user_servers = [s for s in agent.mcp_servers if s not in [
        "products", "pricing", "inventory", "sales", "features",
        "media", "integrations", "product_management", "utility",
        "graphql", "orders"
    ]]
    if not user_servers:
        return
    logger.info(f"Preloading user MCP servers for agent {agent.name}: {user_servers}")
    for server_name in user_servers:
        tools = await agent._load_user_mcp_server(server_name, db_session=db_session)
        if tools:
            agent.tools.extend(tools)
            agent._loaded_user_servers.add(server_name)
            logger.info(f"Loaded {len(tools)} tools from user MCP server '{server_name}' for agent {agent.name}")
