"""
Module for handling MCP server connections for Shopify Dev MCP, Perplexity Ask, and other services.

This module provides a hybrid approach:
1. When MCP packages (mcp-client, mcp-server-fetch) are available, it will use them for full functionality
2. When the packages are not available, it falls back to simplified implementations that use direct API calls

To enable full MCP functionality, uncomment and install the optional packages in requirements.txt:
- mcp-client>=0.1.0
- mcp-server-fetch>=0.1.0

The simplified implementation doesn't require external MCP dependencies but may have limited functionality.
"""
import os
import json
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import timedelta

# Setup logging
logger = logging.getLogger(__name__)

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ShopifyMCPServer:
    """
    A class to handle communication with a local Shopify Dev MCP server instance.
    This spawns an npx process running @shopify/dev-mcp to provide schema information
    and documentation search capabilities.
    """
    def __init__(self):
        # Ensure XDG_CONFIG_HOME is set to prevent unbound variable errors
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")
        
        # Params for local Shopify Dev MCP server
        self.params = {
            "command": "npx", 
            "args": ["-y", "@shopify/dev-mcp@latest"],
            "env": os.environ.copy()  # Explicitly pass environment variables
        }
        self.cache = True
    
    async def introspect_admin_schema(self, query, filter_types=None):
        """Query the Shopify Admin API schema using the MCP server"""
        if filter_types is None:
            filter_types = ["all"]
        try:
            print(f"[DEBUG] Starting introspect_admin_schema with query: {query}")
            
            # Execute npx command to run Shopify Dev MCP
            command = [self.params["command"]] + self.params["args"] + ["introspect_admin_schema", query]
            
            try:
                result = subprocess.run(
                    command,
                    env=self.params["env"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Process successful output
                    content = result.stdout
                else:
                    # Process error
                    content = f"## Matching GraphQL Types for '{query}':\nError from Shopify MCP server: {result.stderr}\n\nPlease check the Shopify Admin API documentation for accurate schema information."
            except subprocess.TimeoutExpired:
                content = f"## Matching GraphQL Types for '{query}':\nTimeout while querying Shopify MCP server.\n\nPlease check the Shopify Admin API documentation for accurate schema information."
            
            # Return formatted result
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": content,
                    "annotations": None
                }],
                "isError": False
            }
        except Exception as e:
            print(f"Error in introspect_admin_schema: {e}")
            # Fallback response
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"## Matching GraphQL Types for '{query}':\nError connecting to Shopify MCP server: {str(e)}\n\nPlease check the Shopify Admin API documentation for accurate schema information.",
                    "annotations": None
                }],
                "isError": False
            }
    
    async def search_dev_docs(self, prompt):
        """Search Shopify developer documentation using the MCP server"""
        try:
            # Execute npx command to run Shopify Dev MCP
            command = [self.params["command"]] + self.params["args"] + ["search_dev_docs", prompt]
            
            try:
                result = subprocess.run(
                    command,
                    env=self.params["env"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Process successful output
                    content = result.stdout
                else:
                    # Process error and use mock response
                    content = self._get_mock_docs_response(prompt)["content"][0]["text"]
            except subprocess.TimeoutExpired:
                # Use mock response on timeout
                content = self._get_mock_docs_response(prompt)["content"][0]["text"]
            
            # Return formatted result
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": content,
                    "annotations": None
                }],
                "isError": False
            }
        except Exception as e:
            print(f"Error in search_dev_docs: {e}")
            # Fallback response
            return self._get_mock_docs_response(prompt)
    
    def stop(self):
        """Stop the MCP server process (no-op; context manager handles teardown)"""
        pass
    
    def _get_mock_docs_response(self, prompt):
        """Get a mock documentation response when the MCP server fails"""
        
        # Basic mock response with common Shopify documentation
        mock_content = f"""## Search Results for '{prompt}':

### Shopify Admin API

The Shopify Admin API lets you build apps that extend Shopify's admin functionality. You can use the Admin API to create apps that integrate with merchants' stores and help them run their businesses.

**Key Resources:**
- [Admin API Overview](https://shopify.dev/api/admin) - Learn about the Admin API and how to use it
- [GraphQL Admin API](https://shopify.dev/api/admin-graphql) - Use GraphQL to query and modify data in a Shopify store
- [REST Admin API](https://shopify.dev/api/admin-rest) - Use REST to interact with Shopify resources

### Common GraphQL Patterns

**Querying Products:**
```graphql
query {{
  products(first: 10) {{
    edges {{
      node {{
        id
        title
        handle
        variants(first: 5) {{
          edges {{
            node {{
              id
              title
              sku
              price
            }}
          }}
        }}
      }}
    }}
  }}
}}
```

**Creating a Product:**
```graphql
mutation {{
  productCreate(input: {{
    title: "New Product",
    productType: "Accessories",
    vendor: "My Store",
    status: DRAFT
  }}) {{
    product {{
      id
      title
    }}
    userErrors {{
      field
      message
    }}
  }}
}}
```

For more specific information, please refer to the [official Shopify documentation](https://shopify.dev/docs).
"""
        
        return {
            "meta": None,
            "content": [{
                "type": "text",
                "text": mock_content,
                "annotations": None
            }],
            "isError": False
        }
    
    def stop(self):
        """Stop the MCP server process (no-op)"""
        pass

# Create a singleton instance
mcp_server = ShopifyMCPServer()

class PerplexityMCPServer:
    """
    A class to handle communication with a local Perplexity MCP server instance.
    This is a simplified implementation that makes direct API calls instead of using MCP.
    """
    def __init__(self):
        # Ensure XDG_CONFIG_HOME is set
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")
        
        # Get API key from environment
        self.api_key = os.environ.get("PERPLEXITY_API_KEY", "")
        
    async def perplexity_ask(self, messages):
        """Ask Perplexity a question using direct API calls."""
        print("[MCP_SERVER_DEBUG] Attempting to call Perplexity API...")
        try:
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Convert MCP-style messages to Perplexity API format if needed
            formatted_messages = messages
            
            data = {
                "model": "sonar-medium-online",
                "messages": formatted_messages
            }
            
            # Make API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    json=data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Extract response content
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return {
                            "meta": None,
                            "content": [{
                                "type": "text",
                                "text": content,
                                "annotations": None
                            }],
                            "isError": False
                        }
                    else:
                        return {
                            "meta": None,
                            "content": [{
                                "type": "text",
                                "text": "No content in response from Perplexity API.",
                                "annotations": None
                            }],
                            "isError": False
                        }
                else:
                    return {
                        "meta": None,
                        "content": [{
                            "type": "text",
                            "text": f"Error from Perplexity API: {response.status_code} - {response.text}",
                            "annotations": None
                        }],
                        "isError": False
                    }
        except Exception as e:
            print(f"[MCP_SERVER_DEBUG] Exception during Perplexity API call: {e}")
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"Error connecting to Perplexity API: {str(e)}\n\nPlease try again later.",
                    "annotations": None
                }],
                "isError": False
            }

perplexity_mcp_server = PerplexityMCPServer()

# Import our simple memory implementation
from simple_memory import memory_server as memory_mcp_server

# Import the actual MCP fetch server implementation
try:
    import asyncio
    import json
    import subprocess
    import os
    from mcp.client.session import ClientSession
    
    class FetchMCPServer:
        """
        A class to handle web content fetching using the mcp-server-fetch Python package.
        """
        def __init__(self):
            # Parameters for the fetch server
            self.params = {
                "command": "python",  # or "uvx" if available
                "args": ["-m", "mcp_server_fetch"],
                "env": os.environ.copy()
            }
            
        async def _run_mcp_server(self, tool_name, args):
            """Helper method to run a tool on the MCP fetch server"""
            try:
                # First, start the fetch server as a subprocess
                process = subprocess.Popen(
                    [self.params["command"]] + self.params["args"],
                    env=self.params["env"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False
                )
                
                # Use the MCP client to connect to the server's standard I/O
                from mcp.client.stdio import StdioServerParameters, stdio_client
                
                # Create parameters
                mcp_params = StdioServerParameters(
                    command=None,  # No command needed as we've already started the process
                    args=[],
                    process=process
                )
                
                # Connect to the server
                client = stdio_client(mcp_params)
                session = ClientSession(client)
                
                # Call the tool
                async with session as s:
                    result = await s.call_tool(
                        name=tool_name,
                        arguments=args
                    )
                    
                    # Process the result
                    content = ""
                    if hasattr(result, "content") and result.content:
                        for content_item in result.content:
                            if hasattr(content_item, "text"):
                                content += content_item.text
                                
                    return {
                        "success": True,
                        "content": content,
                        "meta": result.meta if hasattr(result, "meta") else None
                    }
            except Exception as e:
                print(f"[FETCH_MCP] Error running MCP server: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
                
    
        
        async def fetch_and_extract_text(self, url, selector=None):
            """
            Fetch a URL and extract text content, optionally filtered by a CSS selector.
            
            Args:
                url: The URL to fetch
                selector: Optional CSS selector to filter content
                
            Returns:
                Dictionary with the extracted text content
            """
            print(f"[FETCH_MCP] Fetching and extracting text from URL: {url}")
            
            try:
                # Call the extractText tool
                args = {"url": url}
                if selector:
                    args["selector"] = selector
                    
                result = await self._run_mcp_server("extractText", args)
                
                if not result["success"]:
                    raise Exception(result.get("error", "Unknown error"))
                    
                # Extract metadata
                meta = result.get("meta", {})
                status = meta.get("status", 200) if meta else 200
                
                return {
                    "success": True,
                    "url": url,
                    "text": result.get("content", ""),
                    "status": status
                }
            except Exception as e:
                print(f"[FETCH_MCP] Error extracting text from URL: {e}")
                # Fall back to the simplified implementation
                return await self._fetch_and_extract_text_simplified(url, selector)
                
        async def _fetch_and_extract_text_simplified(self, url, selector=None):
            """Simplified fallback implementation"""
            try:
                import httpx
                from bs4 import BeautifulSoup
                
                # Fetch the content
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, follow_redirects=True)
                    
                    # Parse HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract text based on selector
                    if selector:
                        elements = soup.select(selector)
                        text = "\n\n".join([elem.get_text(strip=True) for elem in elements])
                    else:
                        # Remove script and style elements
                        for script_or_style in soup(["script", "style"]):
                            script_or_style.extract()
                        
                        # Get text
                        text = soup.get_text(separator="\n")
                        
                        # Clean up the text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    return {
                        "success": True,
                        "url": url,
                        "text": text,
                        "status": response.status_code
                    }
            except Exception as e:
                print(f"[FETCH_MCP] Error in simplified text extraction: {e}")
                return {
                    "success": False,
                    "url": url,
                    "error": str(e),
                    "text": "",
                    "status": 0
                }
        
        async def fetch_json(self, url, options=None):
            """
            Fetch and parse JSON content from a URL.
            
            Args:
                url: The URL to fetch
                options: Optional dict of fetch options (e.g., headers, timeout)
                
            Returns:
                Dictionary with the parsed JSON content
            """
            if options is None:
                options = {}
                
            print(f"[FETCH_MCP] Fetching JSON from URL: {url}")
            
            try:
                # Call the fetchJson tool
                args = {"url": url}
                for key, value in options.items():
                    args[key] = value
                    
                result = await self._run_mcp_server("fetchJson", args)
                
                if not result["success"]:
                    raise Exception(result.get("error", "Unknown error"))
                    
                # Extract metadata
                meta = result.get("meta", {})
                status = meta.get("status", 200) if meta else 200
                headers = meta.get("headers", {}) if meta else {}
                
                # Parse the JSON
                content = result.get("content", "")
                try:
                    json_data = json.loads(content) if content else None
                except json.JSONDecodeError:
                    json_data = None
                    
                return {
                    "success": True,
                    "url": url,
                    "json": json_data,
                    "status": status,
                    "headers": headers
                }
            except Exception as e:
                print(f"[FETCH_MCP] Error fetching JSON: {e}")
                # Fall back to the simplified implementation
                return await self._fetch_json_simplified(url, options)
                
        async def _fetch_json_simplified(self, url, options=None):
            """Simplified fallback implementation"""
            if options is None:
                options = {}
                
            try:
                import httpx
                
                # Set up headers
                headers = options.get("headers", {})
                if "content-type" not in headers and "Content-Type" not in headers:
                    headers["Accept"] = "application/json"
                
                # Set timeout
                timeout = options.get("timeout", 15.0)
                
                # Make the request
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, headers=headers, follow_redirects=True)
                    
                    # Parse JSON
                    json_data = response.json()
                    
                    return {
                        "success": True,
                        "url": url,
                        "json": json_data,
                        "status": response.status_code,
                        "headers": dict(response.headers)
                    }
            except Exception as e:
                print(f"[FETCH_MCP] Error in simplified JSON fetch: {e}")
                return {
                    "success": False,
                    "url": url,
                    "error": str(e),
                    "json": None,
                    "status": 0
                }
except ImportError:
    # Fall back to simplified implementation if the mcp-server-fetch package is not available
    class FetchMCPServer:
        """
        A class to handle web content fetching.
        This is a simplified implementation that uses httpx directly.
        """
        def __init__(self):
            pass
                
        
        async def fetch_and_extract_text(self, url, selector=None):
            """
            Fetch a URL and extract text content, optionally filtered by a CSS selector.
            
            Args:
                url: The URL to fetch
                selector: Optional CSS selector to filter content
                
            Returns:
                Dictionary with the extracted text content
            """
            print(f"[FETCH_MCP] Fetching and extracting text from URL: {url}")
            
            try:
                import httpx
                from bs4 import BeautifulSoup
                
                # Fetch the content
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, follow_redirects=True)
                    
                    # Parse HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract text based on selector
                    if selector:
                        elements = soup.select(selector)
                        text = "\n\n".join([elem.get_text(strip=True) for elem in elements])
                    else:
                        # Remove script and style elements
                        for script_or_style in soup(["script", "style"]):
                            script_or_style.extract()
                        
                        # Get text
                        text = soup.get_text(separator="\n")
                        
                        # Clean up the text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    return {
                        "success": True,
                        "url": url,
                        "text": text,
                        "status": response.status_code
                    }
            except Exception as e:
                print(f"[FETCH_MCP] Error extracting text from URL: {e}")
                return {
                    "success": False,
                    "url": url,
                    "error": str(e),
                    "text": "",
                    "status": 0
                }
        
        async def fetch_json(self, url, options=None):
            """
            Fetch and parse JSON content from a URL.
            
            Args:
                url: The URL to fetch
                options: Optional dict of fetch options (e.g., headers, timeout)
                
            Returns:
                Dictionary with the parsed JSON content
            """
            if options is None:
                options = {}
                
            print(f"[FETCH_MCP] Fetching JSON from URL: {url}")
            
            try:
                import httpx
                
                # Set up headers
                headers = options.get("headers", {})
                if "content-type" not in headers and "Content-Type" not in headers:
                    headers["Accept"] = "application/json"
                
                # Set timeout
                timeout = options.get("timeout", 15.0)
                
                # Make the request
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, headers=headers, follow_redirects=True)
                    
                    # Parse JSON
                    json_data = response.json()
                    
                    return {
                        "success": True,
                        "url": url,
                        "json": json_data,
                        "status": response.status_code,
                        "headers": dict(response.headers)
                    }
            except Exception as e:
                print(f"[FETCH_MCP] Error fetching JSON: {e}")
                return {
                    "success": False,
                    "url": url,
                    "error": str(e),
                    "json": None,
                    "status": 0
                }

# Create a singleton instance
fetch_mcp_server = FetchMCPServer()

# Try to import the MCP client package
try:
    import asyncio
    import json
    import subprocess
    from mcp.client.session import ClientSession
    
    # MCP-based Sequential Thinking Server implementation
    class SequentialThinkingMCPServer:
        """
        A class to handle structured, step-by-step thinking using the official MCP server.
        Uses @modelcontextprotocol/server-sequential-thinking when available.
        """
        def __init__(self):
            # Ensure XDG_CONFIG_HOME is set to prevent unbound variable errors
            if "XDG_CONFIG_HOME" not in os.environ:
                os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")
                
            # Params for Sequential Thinking MCP server
            self.params = {
                "command": "npx", 
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@latest"],
                "env": os.environ.copy()  # Explicitly pass environment variables
            }
            
        async def _run_mcp_server(self, tool_name, args):
            """Helper method to run a tool on the Sequential Thinking MCP server"""
            try:
                # Start the MCP server process
                process = subprocess.Popen(
                    [self.params["command"]] + self.params["args"],
                    env=self.params["env"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False
                )
                
                # Use the MCP client to connect to the server
                from mcp.client.stdio import StdioServerParameters, stdio_client
                
                # Create parameters
                mcp_params = StdioServerParameters(
                    command=None,  # No command needed as we've already started the process
                    args=[],
                    process=process
                )
                
                # Connect to the server
                client = stdio_client(mcp_params)
                session = ClientSession(client)
                
                # Call the tool
                async with session as s:
                    result = await s.call_tool(
                        name=tool_name,
                        arguments=args
                    )
                    
                    # Process the result
                    content = []
                    if hasattr(result, "content") and result.content:
                        for content_item in result.content:
                            if hasattr(content_item, "text"):
                                content.append(content_item.text)
                                
                    # Extract steps and conclusion if available
                    steps = []
                    conclusion = ""
                    
                    # Check if the result has a meta field with steps and conclusion
                    if hasattr(result, "meta") and result.meta:
                        meta_dict = result.meta
                        if isinstance(meta_dict, dict):
                            if "steps" in meta_dict:
                                steps = meta_dict["steps"]
                            if "conclusion" in meta_dict:
                                conclusion = meta_dict["conclusion"]
                    
                    # If no steps in meta, try to parse from content
                    if not steps and content:
                        combined_content = "\n".join(content)
                        # Parse steps from content (simplified)
                        import re
                        step_pattern = re.compile(r"Step (\d+):(.*?)(?=Step \d+:|$)", re.DOTALL)
                        step_matches = step_pattern.findall(combined_content + "\n")
                        
                        steps = [{"number": int(num), "content": content.strip()} for num, content in step_matches]
                        
                        # Try to find conclusion
                        if "\n\nConclusion:" in combined_content:
                            parts = combined_content.split("\n\nConclusion:")
                            conclusion = parts[1].strip()
                    
                    return {
                        "success": True,
                        "steps": steps,
                        "conclusion": conclusion,
                        "thinking_type": args.get("thinking_type", "general"),
                        "raw_content": content
                    }
            except Exception as e:
                print(f"[THINKING_MCP] Error running MCP server: {e}")
                # Fall back to direct implementation
                return await self._think_direct(
                    args.get("prompt", ""),
                    args.get("thinking_type", "general"),
                    args.get("max_steps", 5)
                )
                
        async def think(self, prompt, thinking_type="general", max_steps=5):
            """
            Perform structured step-by-step thinking on a prompt.
            
            Args:
                prompt: The prompt to think about
                thinking_type: Type of thinking (general, problem-solving, coding)
                max_steps: Maximum number of thinking steps
                
            Returns:
                Dictionary with the thinking steps and final conclusion
            """
            print(f"[THINKING_MCP] Starting sequential thinking process: {prompt[:50]}...")
            
            # Note: MCP server communication is currently experimental and may not work correctly
            # The current implementation of the @modelcontextprotocol/server-sequential-thinking
            # package expects communication via stdin/stdout rather than through the MCP client.
            # For now, we'll use the direct implementation as our primary approach.
            
            try:
                # Use direct implementation for now until MCP server issues are resolved
                print(f"[THINKING_MCP] Using direct implementation due to known MCP server issues")
                return await self._think_direct(prompt, thinking_type, max_steps)
                
                # When MCP server issues are resolved, uncomment the following:
                # Prepare args for the MCP server
                # args = {
                #     "prompt": prompt,
                #     "thinking_type": thinking_type,
                #     "max_steps": max_steps
                # }
                # return await self._run_mcp_server("think", args)
            except Exception as e:
                print(f"[THINKING_MCP] Error in thinking implementation: {e}")
                # Fall back to direct implementation if not already using it
                return await self._think_direct(prompt, thinking_type, max_steps)
        
        async def _think_direct(self, prompt, thinking_type="general", max_steps=5):
            """
            Fallback direct implementation using OpenAI API.
            
            Args:
                prompt: The prompt to think about
                thinking_type: Type of thinking
                max_steps: Maximum number of steps
                
            Returns:
                Dictionary with thinking steps and conclusion
            """
            print(f"[THINKING_MCP] Using direct implementation for: {prompt[:50]}...")
            
            try:
                import openai
                
                # Get API key from environment
                api_key = os.environ.get("OPENAI_API_KEY", "")
                
                # Set up client
                client = openai.AsyncOpenAI(api_key=api_key)
                
                # Prepare system message based on thinking type
                system_messages = {
                    "general": "You are a thinking assistant. Break down this problem or question into clear, step-by-step reasoning. Provide exactly 3-5 steps, with each step building logically on the previous one. Each step should start with 'Step X:'. End with a clear conclusion.",
                    "problem-solving": "You are a problem-solving assistant. Analyze this problem methodically. Provide exactly 4-6 problem-solving steps, with each step clearly identified as 'Step X:'. Your steps should include: 1) Understanding the problem, 2) Breaking it down, 3) Identifying approaches, 4) Evaluating solutions, 5) Selecting the best approach. End with a firm conclusion about the solution.",
                    "coding": "You are a coding assistant. Plan the implementation of this coding task methodically. Provide exactly 4-7 steps, with each step clearly labeled as 'Step X:'. Your steps should include: 1) Requirement analysis, 2) Data structures/algorithms needed, 3) Breaking down the implementation, 4) Key functions/classes, 5) Testing approach. End with a conclusion summarizing the implementation plan."
                }
                
                system_message = system_messages.get(thinking_type, system_messages["general"])
                
                # Make API request
                response = await client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Extract thinking steps and conclusion
                thinking_text = response.choices[0].message.content
                
                # Parse steps and conclusion
                steps = []
                conclusion = ""
                
                # Try to split by conclusion marker
                if "\n\nConclusion:" in thinking_text:
                    parts = thinking_text.split("\n\nConclusion:")
                    steps_text = parts[0]
                    conclusion = parts[1].strip()
                else:
                    # Try to find the conclusion in the last paragraph
                    paragraphs = thinking_text.split("\n\n")
                    if len(paragraphs) > 1 and not paragraphs[-1].startswith("Step"):
                        steps_text = "\n\n".join(paragraphs[:-1])
                        conclusion = paragraphs[-1].strip()
                    else:
                        steps_text = thinking_text
                        conclusion = "No explicit conclusion provided."
                
                # Parse steps
                import re
                step_pattern = re.compile(r"Step (\d+):(.*?)(?=Step \d+:|$)", re.DOTALL)
                step_matches = step_pattern.findall(steps_text + "\n")
                
                steps = [{"number": int(num), "content": content.strip()} for num, content in step_matches]
                
                if not steps:
                    # If no steps found with regex, try simple splitting
                    lines = steps_text.split("\n")
                    current_step = None
                    current_content = []
                    
                    for line in lines:
                        if line.startswith("Step ") and ":" in line:
                            # Save previous step if exists
                            if current_step and current_content:
                                steps.append({
                                    "number": current_step,
                                    "content": "\n".join(current_content).strip()
                                })
                            
                            # Start new step
                            parts = line.split(":", 1)
                            step_text = parts[0].replace("Step ", "").strip()
                            try:
                                current_step = int(step_text)
                            except ValueError:
                                current_step = len(steps) + 1
                            
                            current_content = [parts[1].strip()] if len(parts) > 1 else []
                        elif current_step is not None:
                            current_content.append(line)
                    
                    # Add the last step
                    if current_step and current_content:
                        steps.append({
                            "number": current_step,
                            "content": "\n".join(current_content).strip()
                        })
                
                return {
                    "success": True,
                    "steps": steps,
                    "conclusion": conclusion,
                    "thinking_type": thinking_type
                }
            except Exception as e:
                print(f"[THINKING_MCP] Error in direct implementation: {e}")
                return {
                    "success": False,
                    "steps": [],
                    "conclusion": f"Error in sequential thinking: {str(e)}",
                    "thinking_type": thinking_type,
                    "error": str(e)
                }
        
        async def solve_problem(self, problem, max_steps=5):
            """
            Apply problem-solving thinking to a specific problem.
            
            Args:
                problem: The problem to solve
                max_steps: Maximum number of thinking steps
                
            Returns:
                Dictionary with problem-solving steps and solution
            """
            return await self.think(problem, thinking_type="problem-solving", max_steps=max_steps)
        
        async def plan_code(self, coding_task, max_steps=5):
            """
            Plan coding implementation with step-by-step thinking.
            
            Args:
                coding_task: The coding task to plan
                max_steps: Maximum number of thinking steps
                
            Returns:
                Dictionary with coding plan steps and final implementation plan
            """
            return await self.think(coding_task, thinking_type="coding", max_steps=max_steps)

except ImportError:
    # Fallback to simplified implementation when MCP client is not available
    class SequentialThinkingMCPServer:
        """
        A class to handle structured, step-by-step thinking.
        This is a simplified implementation that formats thinking steps locally.
        """
        def __init__(self):
            pass
        
        async def think(self, prompt, thinking_type="general", max_steps=5):
            """
            Perform structured step-by-step thinking on a prompt.
            
            Args:
                prompt: The prompt to think about
                thinking_type: Type of thinking (general, problem-solving, coding)
                max_steps: Maximum number of thinking steps
                
            Returns:
                Dictionary with the thinking steps and final conclusion
            """
            print(f"[THINKING_MCP] Starting sequential thinking process (simplified): {prompt[:50]}...")
            
            try:
                import openai
                
                # Get API key from environment
                api_key = os.environ.get("OPENAI_API_KEY", "")
                
                # Set up client
                client = openai.AsyncOpenAI(api_key=api_key)
                
                # Prepare system message based on thinking type
                system_messages = {
                    "general": "You are a thinking assistant. Break down this problem or question into clear, step-by-step reasoning. Provide exactly 3-5 steps, with each step building logically on the previous one. Each step should start with 'Step X:'. End with a clear conclusion.",
                    "problem-solving": "You are a problem-solving assistant. Analyze this problem methodically. Provide exactly 4-6 problem-solving steps, with each step clearly identified as 'Step X:'. Your steps should include: 1) Understanding the problem, 2) Breaking it down, 3) Identifying approaches, 4) Evaluating solutions, 5) Selecting the best approach. End with a firm conclusion about the solution.",
                    "coding": "You are a coding assistant. Plan the implementation of this coding task methodically. Provide exactly 4-7 steps, with each step clearly labeled as 'Step X:'. Your steps should include: 1) Requirement analysis, 2) Data structures/algorithms needed, 3) Breaking down the implementation, 4) Key functions/classes, 5) Testing approach. End with a conclusion summarizing the implementation plan."
                }
                
                system_message = system_messages.get(thinking_type, system_messages["general"])
                
                # Make API request
                response = await client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Extract thinking steps and conclusion
                thinking_text = response.choices[0].message.content
                
                # Parse steps and conclusion
                steps = []
                conclusion = ""
                
                # Try to split by conclusion marker
                if "\n\nConclusion:" in thinking_text:
                    parts = thinking_text.split("\n\nConclusion:")
                    steps_text = parts[0]
                    conclusion = parts[1].strip()
                else:
                    # Try to find the conclusion in the last paragraph
                    paragraphs = thinking_text.split("\n\n")
                    if len(paragraphs) > 1 and not paragraphs[-1].startswith("Step"):
                        steps_text = "\n\n".join(paragraphs[:-1])
                        conclusion = paragraphs[-1].strip()
                    else:
                        steps_text = thinking_text
                        conclusion = "No explicit conclusion provided."
                
                # Parse steps
                import re
                step_pattern = re.compile(r"Step (\d+):(.*?)(?=Step \d+:|$)", re.DOTALL)
                step_matches = step_pattern.findall(steps_text + "\n")
                
                steps = [{"number": int(num), "content": content.strip()} for num, content in step_matches]
                
                if not steps:
                    # If no steps found with regex, try simple splitting
                    lines = steps_text.split("\n")
                    current_step = None
                    current_content = []
                    
                    for line in lines:
                        if line.startswith("Step ") and ":" in line:
                            # Save previous step if exists
                            if current_step and current_content:
                                steps.append({
                                    "number": current_step,
                                    "content": "\n".join(current_content).strip()
                                })
                            
                            # Start new step
                            parts = line.split(":", 1)
                            step_text = parts[0].replace("Step ", "").strip()
                            try:
                                current_step = int(step_text)
                            except ValueError:
                                current_step = len(steps) + 1
                            
                            current_content = [parts[1].strip()] if len(parts) > 1 else []
                        elif current_step is not None:
                            current_content.append(line)
                    
                    # Add the last step
                    if current_step and current_content:
                        steps.append({
                            "number": current_step,
                            "content": "\n".join(current_content).strip()
                        })
                
                return {
                    "success": True,
                    "steps": steps,
                    "conclusion": conclusion,
                    "thinking_type": thinking_type
                }
            except Exception as e:
                print(f"[THINKING_MCP] Error in sequential thinking: {e}")
                return {
                    "success": False,
                    "steps": [],
                    "conclusion": f"Error in sequential thinking: {str(e)}",
                    "thinking_type": thinking_type,
                    "error": str(e)
                }
        
        async def solve_problem(self, problem, max_steps=5):
            """
            Apply problem-solving thinking to a specific problem.
            
            Args:
                problem: The problem to solve
                max_steps: Maximum number of thinking steps
                
            Returns:
                Dictionary with problem-solving steps and solution
            """
            return await self.think(problem, thinking_type="problem-solving", max_steps=max_steps)
        
        async def plan_code(self, coding_task, max_steps=5):
            """
            Plan coding implementation with step-by-step thinking.
            
            Args:
                coding_task: The coding task to plan
                max_steps: Maximum number of thinking steps
                
            Returns:
                Dictionary with coding plan steps and final implementation plan
            """
            return await self.think(coding_task, thinking_type="coding", max_steps=max_steps)

# Create a singleton instance
thinking_mcp_server = SequentialThinkingMCPServer()

class FilesystemMCPServer:
    """
    A class to handle filesystem operations.
    This is a simplified implementation that uses Python's file operations directly.
    """
    def __init__(self):
        # Set up the base storage directory for all files
        self.base_dir = os.path.join(PROJECT_ROOT, "storage")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Set up templates directory
        self.templates_dir = os.path.join(self.base_dir, "templates")
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Set up exports directory
        self.exports_dir = os.path.join(self.base_dir, "exports")
        os.makedirs(self.exports_dir, exist_ok=True)
        
        # Set up user files directory
        self.users_dir = os.path.join(self.base_dir, "users")
        os.makedirs(self.users_dir, exist_ok=True)
    
    def _resolve_path(self, path, user_id=None):
        """
        Resolve a path to an absolute path within the allowed directories.
        
        Args:
            path: The path to resolve (can be relative to base_dir)
            user_id: Optional user ID to scope to user directory
            
        Returns:
            Absolute path within allowed directories, or None if invalid
        """
        # Check if path is absolute or relative
        if os.path.isabs(path):
            # For absolute paths, verify they're within allowed directories
            norm_path = os.path.normpath(path)
            if not (norm_path.startswith(self.base_dir) or 
                    norm_path.startswith(self.templates_dir) or 
                    norm_path.startswith(self.exports_dir) or 
                    norm_path.startswith(self.users_dir)):
                # Path is outside allowed directories
                return None
            return norm_path
        else:
            # For relative paths, resolve based on context
            if path.startswith("templates/"):
                # Template path
                rel_path = path[len("templates/"):]
                return os.path.join(self.templates_dir, rel_path)
            elif path.startswith("exports/"):
                # Export path
                rel_path = path[len("exports/"):]
                return os.path.join(self.exports_dir, rel_path)
            elif path.startswith("users/"):
                # User path
                rel_path = path[len("users/"):]
                return os.path.join(self.users_dir, rel_path)
            elif user_id is not None:
                # User-specific path
                user_dir = os.path.join(self.users_dir, str(user_id))
                os.makedirs(user_dir, exist_ok=True)
                return os.path.join(user_dir, path)
            else:
                # Default to base directory
                return os.path.join(self.base_dir, path)
    
    async def read_file(self, path, user_id=None, encoding="utf-8"):
        """
        Read a file using direct file operations.
        
        Args:
            path: Path to the file (relative to base_dir or absolute)
            user_id: Optional user ID to scope to user directory
            encoding: Text encoding to use
            
        Returns:
            Dictionary with file content and metadata
        """
        print(f"[FILESYSTEM_MCP] Reading file: {path}")
        
        # Resolve and validate path
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {
                "success": False,
                "path": path,
                "error": "Invalid path. Path must be within allowed directories."
            }
        
        # Check if file exists
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "path": path,
                "error": "File does not exist."
            }
        
        try:
            # Read the file
            with open(abs_path, "r", encoding=encoding) as f:
                content = f.read()
            
            return {
                "success": True,
                "path": path,
                "content": content,
                "exists": True
            }
        except Exception as e:
            print(f"[FILESYSTEM_MCP] Error reading file: {e}")
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }
    
    async def write_file(self, path, content, user_id=None, encoding="utf-8"):
        """
        Write content to a file using direct file operations.
        
        Args:
            path: Path to the file (relative to base_dir or absolute)
            content: Content to write to the file
            user_id: Optional user ID to scope to user directory
            encoding: Text encoding to use
            
        Returns:
            Dictionary with operation status
        """
        print(f"[FILESYSTEM_MCP] Writing file: {path}")
        
        # Resolve and validate path
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {
                "success": False,
                "path": path,
                "error": "Invalid path. Path must be within allowed directories."
            }
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            # Write to the file
            with open(abs_path, "w", encoding=encoding) as f:
                f.write(content)
            
            return {
                "success": True,
                "path": path,
                "message": f"File written successfully to {path}"
            }
        except Exception as e:
            print(f"[FILESYSTEM_MCP] Error writing file: {e}")
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }
    
    async def list_directory(self, path, user_id=None):
        """
        List contents of a directory using direct file operations.
        
        Args:
            path: Path to the directory (relative to base_dir or absolute)
            user_id: Optional user ID to scope to user directory
            
        Returns:
            Dictionary with directory contents
        """
        print(f"[FILESYSTEM_MCP] Listing directory: {path}")
        
        # Resolve and validate path
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {
                "success": False,
                "path": path,
                "error": "Invalid path. Path must be within allowed directories."
            }
        
        # Check if directory exists
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return {
                "success": False,
                "path": path,
                "error": "Directory does not exist."
            }
        
        try:
            # Get directory contents
            items = os.listdir(abs_path)
            
            # Separate files and directories
            files = []
            directories = []
            
            for item in items:
                item_path = os.path.join(abs_path, item)
                if os.path.isdir(item_path):
                    directories.append(item)
                else:
                    files.append(item)
            
            return {
                "success": True,
                "path": path,
                "files": files,
                "directories": directories
            }
        except Exception as e:
            print(f"[FILESYSTEM_MCP] Error listing directory: {e}")
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }
    
    async def delete_file(self, path, user_id=None):
        """
        Delete a file using direct file operations.
        
        Args:
            path: Path to the file (relative to base_dir or absolute)
            user_id: Optional user ID to scope to user directory
            
        Returns:
            Dictionary with operation status
        """
        print(f"[FILESYSTEM_MCP] Deleting file: {path}")
        
        # Resolve and validate path
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {
                "success": False,
                "path": path,
                "error": "Invalid path. Path must be within allowed directories."
            }
        
        # Check if file exists
        if not os.path.exists(abs_path) or os.path.isdir(abs_path):
            return {
                "success": False,
                "path": path,
                "error": "File does not exist or is a directory."
            }
        
        try:
            # Delete the file
            os.remove(abs_path)
            
            return {
                "success": True,
                "path": path,
                "message": f"File deleted successfully: {path}"
            }
        except Exception as e:
            print(f"[FILESYSTEM_MCP] Error deleting file: {e}")
            return {
                "success": False,
                "path": path,
                "error": str(e)
            }
    
    async def check_file_exists(self, path, user_id=None):
        """
        Check if a file exists using direct file operations.
        
        Args:
            path: Path to the file (relative to base_dir or absolute)
            user_id: Optional user ID to scope to user directory
            
        Returns:
            Dictionary with existence status
        """
        print(f"[FILESYSTEM_MCP] Checking if file exists: {path}")
        
        # Resolve and validate path
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {
                "success": False,
                "path": path,
                "exists": False,
                "error": "Invalid path. Path must be within allowed directories."
            }
        
        try:
            # Check if file exists
            exists = os.path.exists(abs_path) and not os.path.isdir(abs_path)
            
            return {
                "success": True,
                "path": path,
                "exists": exists
            }
        except Exception as e:
            print(f"[FILESYSTEM_MCP] Error checking file existence: {e}")
            return {
                "success": False,
                "path": path,
                "exists": False,
                "error": str(e)
            }

# Create a singleton instance
filesystem_mcp_server = FilesystemMCPServer()