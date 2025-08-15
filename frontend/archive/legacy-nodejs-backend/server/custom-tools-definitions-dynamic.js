import { tool } from '@openai/agents';
import { z } from 'zod';
import { customToolDiscovery } from './custom-tool-discovery.js';
import { getMCPTools } from './tools/mcp-client.js';

// Initialize custom tool discovery
await customToolDiscovery.discoverTools();

/**
 * Convert MCP tool schema to Zod schema
 * This handles the JSON Schema to Zod conversion
 */
function convertToZodSchema(jsonSchema) {
  if (!jsonSchema || !jsonSchema.properties) {
    return z.object({});
  }

  const shape = {};
  
  for (const [key, prop] of Object.entries(jsonSchema.properties)) {
    let zodType;
    
    // Handle different JSON schema types
    switch (prop.type) {
      case 'string':
        zodType = z.string();
        if (prop.enum) {
          zodType = z.enum(prop.enum);
        }
        break;
      case 'number':
      case 'integer':
        zodType = z.number();
        break;
      case 'boolean':
        zodType = z.boolean();
        break;
      case 'array':
        // For arrays, we need to handle the items type
        if (prop.items) {
          if (prop.items.type === 'string') {
            zodType = z.array(z.string());
          } else if (prop.items.type === 'object') {
            // For complex objects in arrays, use z.any() for now
            zodType = z.array(z.any());
          } else {
            zodType = z.array(z.any());
          }
        } else {
          zodType = z.array(z.any());
        }
        break;
      case 'object':
        // For nested objects, use z.record or z.any
        if (prop.additionalProperties) {
          zodType = z.record(z.any());
        } else {
          zodType = z.any();
        }
        break;
      default:
        zodType = z.any();
    }
    
    // Handle optional fields
    if (!jsonSchema.required || !jsonSchema.required.includes(key)) {
      zodType = zodType.nullable().default(null);
    }
    
    // Add description if available
    if (prop.description) {
      zodType = zodType.describe(prop.description);
    }
    
    shape[key] = zodType;
  }
  
  return z.object(shape);
}

/**
 * Dynamically generate tool definitions from MCP tools
 */
async function generateDynamicTools() {
  console.log('🔧 Generating dynamic tool definitions from MCP...');
  
  try {
    // Get all MCP tools
    const mcpTools = await getMCPTools();
    console.log(`Found ${mcpTools.length} MCP tools to convert`);
    
    // Convert each MCP tool to OpenAI SDK format
    const dynamicTools = mcpTools.map(mcpTool => {
      console.log(`Converting tool: ${mcpTool.name}`);
      
      // Convert the input schema
      const zodSchema = convertToZodSchema(mcpTool.inputSchema);
      
      return tool({
        name: mcpTool.name,
        description: mcpTool.description || `MCP tool: ${mcpTool.name}`,
        parameters: zodSchema,
        execute: async (args) => {
          try {
            const result = await customToolDiscovery.executeTool(mcpTool.name, args);
            return JSON.stringify(result);
          } catch (error) {
            return JSON.stringify({ error: error.message });
          }
        }
      });
    });
    
    console.log(`✅ Successfully generated ${dynamicTools.length} tool definitions`);
    return dynamicTools;
    
  } catch (error) {
    console.error('❌ Failed to generate dynamic tools:', error);
    // Return empty array if MCP is not available
    return [];
  }
}

// Generate all tools dynamically
export const shopifyTools = await generateDynamicTools();

// Also export the generation function for testing
export { generateDynamicTools };

console.log(`📦 Exported ${shopifyTools.length} tools for orchestrator use`);