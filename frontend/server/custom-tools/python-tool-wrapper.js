import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class PythonToolWrapper {
  constructor(toolsPath = null) {
    // Use local python-tools directory by default
    this.toolsPath = toolsPath || path.join(__dirname, '../python-tools');
  }

  async executeTool(toolName, args = {}, positionalArgs = []) {
    return new Promise((resolve, reject) => {
      const toolPath = path.join(this.toolsPath, `${toolName}.py`);
      
      // Start with positional arguments
      const cmdArgs = [...positionalArgs];
      
      // Convert args object to command line arguments
      for (const [key, value] of Object.entries(args)) {
        if (value !== undefined && value !== null) {
          cmdArgs.push(`--${key.replace(/_/g, '-')}`);
          if (typeof value === 'boolean') {
            // Boolean flags don't need a value
            if (!value) cmdArgs.pop(); // Remove the flag if false
          } else if (Array.isArray(value)) {
            cmdArgs.push(...value);
          } else {
            cmdArgs.push(String(value));
          }
        }
      }

      const python = spawn('python3', [toolPath, ...cmdArgs]);
      let stdout = '';
      let stderr = '';

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Tool ${toolName} failed with code ${code}: ${stderr}`));
        } else {
          try {
            // Try to parse as JSON first
            const result = JSON.parse(stdout);
            resolve(result);
          } catch (e) {
            // If not JSON, return raw output
            resolve(stdout.trim());
          }
        }
      });

      python.on('error', (err) => {
        reject(new Error(`Failed to execute tool ${toolName}: ${err.message}`));
      });
    });
  }

  // Specific tool wrappers for better typing and validation
  async searchProducts(query, options = {}) {
    // The Python tool expects positional argument for query
    const args = [query];
    const cmdOptions = {};
    
    if (options.first) {
      cmdOptions.limit = options.first;
    }
    
    return this.executeTool('search_products', cmdOptions, args);
  }

  async getProduct(identifier, options = {}) {
    return this.executeTool('get_product', {
      ...options,
      id: identifier.id,
      handle: identifier.handle,
      sku: identifier.sku
    });
  }

  async createProduct(productData) {
    return this.executeTool('create_full_product', productData);
  }

  async updatePricing(updates) {
    return this.executeTool('update_pricing', updates);
  }

  async updateStatus(productId, status) {
    return this.executeTool('update_status', {
      product_id: productId,
      status
    });
  }

  async manageTags(productId, addTags = [], removeTags = []) {
    return this.executeTool('manage_tags', {
      product_id: productId,
      add_tags: addTags,
      remove_tags: removeTags
    });
  }

  async runGraphQLQuery(query, variables = {}) {
    return this.executeTool('graphql_query', {
      query,
      variables: JSON.stringify(variables)
    });
  }

  async runGraphQLMutation(mutation, variables = {}) {
    return this.executeTool('graphql_mutation', {
      mutation,
      variables: JSON.stringify(variables)
    });
  }
}

export default PythonToolWrapper;