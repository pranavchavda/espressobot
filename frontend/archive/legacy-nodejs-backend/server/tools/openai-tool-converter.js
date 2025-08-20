import { tool } from '@openai/agents';
import { z } from 'zod';
import { customToolDiscovery } from '../custom-tool-discovery.js';

// Initialize custom tool discovery
await customToolDiscovery.discoverTools();

/**
 * Converts a tool registry schema to Zod schema
 */
function convertToZodSchema(inputSchema) {
  if (!inputSchema || !inputSchema.properties) {
    return z.object({});
  }

  const zodProperties = {};
  const required = inputSchema.required || [];

  for (const [key, prop] of Object.entries(inputSchema.properties)) {
    let zodType;

    switch (prop.type) {
      case 'string':
        zodType = z.string();
        break;
      case 'number':
        zodType = z.number();
        break;
      case 'boolean':
        zodType = z.boolean();
        break;
      case 'array':
        if (prop.items) {
          if (prop.items.type === 'string') {
            zodType = z.array(z.string());
          } else if (prop.items.type === 'object' && prop.items.properties) {
            // Recursively convert nested object schema
            const itemSchema = convertToZodSchema(prop.items);
            zodType = z.array(itemSchema);
          } else if (prop.items.type) {
            // Handle other primitive types
            const itemType = prop.items.type;
            if (itemType === 'number') {
              zodType = z.array(z.number());
            } else if (itemType === 'boolean') {
              zodType = z.array(z.boolean());
            } else {
              zodType = z.array(z.unknown());
            }
          } else {
            zodType = z.array(z.unknown());
          }
        } else {
          zodType = z.array(z.unknown());
        }
        break;
      case 'object':
        zodType = z.record(z.unknown());
        break;
      default:
        zodType = z.unknown();
    }

    // Add description
    if (prop.description) {
      zodType = zodType.describe(prop.description);
    }

    // Handle default values
    if (prop.default !== undefined && !required.includes(key)) {
      zodType = zodType.default(prop.default);
    }

    // Handle enum values
    if (prop.enum) {
      zodType = z.enum(prop.enum);
      if (prop.description) {
        zodType = zodType.describe(prop.description);
      }
    }

    // Make optional if not required - OpenAI SDK requires nullable() instead of optional()
    if (!required.includes(key)) {
      zodType = zodType.nullable();
    }

    zodProperties[key] = zodType;
  }

  return z.object(zodProperties);
}

/**
 * Converts registry tools to OpenAI agent tools
 */
export function convertRegistryToolsToOpenAI() {
  const openAITools = {};
  const allTools = customToolDiscovery.allTools;

  for (const registryTool of allTools) {
    try {
      const zodSchema = convertToZodSchema(registryTool.inputSchema);
      
      const openAITool = tool({
        name: registryTool.name,
        description: registryTool.description,
        parameters: zodSchema,
        execute: async (args) => {
          try {
            const result = await customToolDiscovery.executeTool(registryTool.name, args);
            // Return result as-is if it's already a string, otherwise stringify
            return typeof result === 'string' ? result : JSON.stringify(result);
          } catch (error) {
            return JSON.stringify({ error: error.message });
          }
        }
      });

      openAITools[registryTool.name] = openAITool;
    } catch (error) {
      console.error(`Failed to convert tool ${registryTool.name}:`, error);
    }
  }

  return openAITools;
}

/**
 * Get all tools as an array
 */
export function getAllOpenAITools() {
  const tools = convertRegistryToolsToOpenAI();
  return Object.values(tools);
}

/**
 * Get a specific tool by name
 */
export function getOpenAITool(toolName) {
  const tools = convertRegistryToolsToOpenAI();
  return tools[toolName];
}

// Export pre-converted tools for convenience
export const openAITools = convertRegistryToolsToOpenAI();
export const openAIToolsArray = getAllOpenAITools();