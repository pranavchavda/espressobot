/**
 * MCP-only Tool Registry
 * This simplified registry only handles MCP tools and native JavaScript tools
 * Python subprocess tools have been migrated to MCP
 */

class MCPOnlyToolRegistry {
  constructor() {
    this.nativeTools = new Map();
    this.tools = [];
  }

  /**
   * Register a native JavaScript tool
   */
  registerNativeTool(toolInstance) {
    const metadata = toolInstance.metadata;
    this.nativeTools.set(metadata.name, toolInstance);
    
    const toolConfig = {
      name: metadata.name,
      description: metadata.description,
      inputSchema: metadata.inputSchema,
      type: 'native',
      handler: async (args) => toolInstance.run(args)
    };
    
    const existingIndex = this.tools.findIndex(t => t.name === metadata.name);
    if (existingIndex >= 0) {
      this.tools[existingIndex] = toolConfig;
    } else {
      this.tools.push(toolConfig);
    }
  }

  /**
   * Register a generic tool (OpenAI SDK format)
   */
  registerTool(name, toolInstance) {
    if (toolInstance._spec) {
      const spec = toolInstance._spec;
      const toolConfig = {
        name: spec.name,
        description: spec.description || '',
        inputSchema: spec.parameters || {},
        type: 'openai-sdk',
        handler: async (args) => toolInstance.execute(args)
      };
      
      const existingIndex = this.tools.findIndex(t => t.name === spec.name);
      if (existingIndex >= 0) {
        this.tools[existingIndex] = toolConfig;
      } else {
        this.tools.push(toolConfig);
      }
    }
  }

  getTools() {
    return this.tools;
  }

  getOpenAIFunctions() {
    return this.tools.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.inputSchema
      }
    }));
  }

  async executeTool(toolName, args) {
    const tool = this.tools.find(t => t.name === toolName);
    if (!tool) {
      throw new Error(`Tool ${toolName} not found`);
    }
    return tool.handler(args);
  }
}

export default MCPOnlyToolRegistry;