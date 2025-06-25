import { getShopifyClient } from '../shopify/shopify-client.js';

/**
 * Base class for all native JavaScript tools
 * Provides common functionality and consistent interface
 */
export class BaseTool {
  constructor() {
    this.shopifyClient = getShopifyClient();
    this.debug = process.env.DEBUG?.toLowerCase() === 'true';
  }

  /**
   * Tool metadata - must be overridden by subclasses
   */
  get metadata() {
    throw new Error('Tool must define metadata getter');
  }

  /**
   * Execute the tool with given arguments
   * Must be overridden by subclasses
   * @param {Object} args - Tool arguments
   * @returns {Promise<Object>} Tool result
   */
  async execute(args) {
    throw new Error('Tool must implement execute method');
  }

  /**
   * Validate arguments against expected schema
   * @param {Object} args - Arguments to validate
   * @param {Object} schema - Expected schema with required fields
   * @throws {Error} If validation fails
   */
  validateArgs(args, schema) {
    const required = schema.required || [];
    const properties = schema.properties || {};
    
    // Check required fields
    for (const field of required) {
      if (args[field] === undefined || args[field] === null) {
        throw new Error(`Missing required field: ${field}`);
      }
    }
    
    // Validate field types
    for (const [field, value] of Object.entries(args)) {
      if (properties[field]) {
        const expectedType = properties[field].type;
        const actualType = Array.isArray(value) ? 'array' : typeof value;
        
        if (expectedType && actualType !== expectedType) {
          throw new Error(`Invalid type for ${field}: expected ${expectedType}, got ${actualType}`);
        }
        
        // Validate enum values
        if (properties[field].enum && !properties[field].enum.includes(value)) {
          throw new Error(`Invalid value for ${field}: must be one of ${properties[field].enum.join(', ')}`);
        }
      }
    }
  }

  /**
   * Format successful response
   * @param {Object} data - Response data
   * @returns {Object} Formatted response
   */
  formatSuccess(data) {
    return {
      success: true,
      data,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Format error response
   * @param {Error} error - Error object
   * @returns {Object} Formatted error response
   */
  formatError(error) {
    return {
      success: false,
      error: {
        message: error.message,
        code: error.code || 'UNKNOWN_ERROR',
        details: error.details || {}
      },
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Log debug information
   * @param {string} message - Debug message
   * @param {Object} data - Additional data to log
   */
  log(message, data = {}) {
    if (this.debug) {
      console.log(`[${this.constructor.name}] ${message}`, data);
    }
  }

  /**
   * Safe execution wrapper with error handling
   * @param {Object} args - Tool arguments
   * @returns {Promise<Object>} Formatted result
   */
  async run(args) {
    try {
      this.log('Executing with args:', args);
      
      // Validate arguments if schema is defined
      if (this.metadata.inputSchema) {
        this.validateArgs(args, this.metadata.inputSchema);
      }
      
      // Execute the tool
      const result = await this.execute(args);
      
      this.log('Execution successful:', result);
      return this.formatSuccess(result);
      
    } catch (error) {
      this.log('Execution failed:', error);
      return this.formatError(error);
    }
  }
}

/**
 * Create a tool wrapper for OpenAI agents format
 * @param {BaseTool} toolInstance - Instance of a tool class
 * @returns {Object} Tool configuration for OpenAI agents
 */
export function createToolWrapper(toolInstance) {
  return {
    name: toolInstance.metadata.name,
    description: toolInstance.metadata.description,
    inputSchema: toolInstance.metadata.inputSchema,
    handler: async (args) => {
      const result = await toolInstance.run(args);
      return JSON.stringify(result);
    }
  };
}