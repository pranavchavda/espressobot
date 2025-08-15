import { BaseTool } from './base-tool.js';
import { parseTags } from '../shopify/shopify-client.js';

/**
 * Native JavaScript implementation of manage_tags tool
 * Add or remove tags from products
 */
export class ManageTagsTool extends BaseTool {
  get metadata() {
    return {
      name: 'manage_tags',
      description: 'Add or remove multiple tags from a product',
      inputSchema: {
        type: 'object',
        properties: {
          product_id: { 
            type: 'string', 
            description: 'Product ID (numeric or GID format)' 
          },
          add_tags: { 
            type: 'array', 
            items: { type: 'string' }, 
            default: [],
            description: 'Tags to add to the product'
          },
          remove_tags: { 
            type: 'array', 
            items: { type: 'string' }, 
            default: [],
            description: 'Tags to remove from the product'
          }
        },
        required: ['product_id']
      }
    };
  }

  /**
   * Execute tag management
   */
  async execute(args) {
    const { product_id, add_tags = [], remove_tags = [] } = args;
    
    this.log('Managing tags', { product_id, add_tags, remove_tags });
    
    // Normalize product ID
    const productId = this.shopifyClient.normalizeId(product_id);
    
    // Parse tags if they're strings
    const tagsToAdd = Array.isArray(add_tags) ? add_tags : parseTags(add_tags);
    const tagsToRemove = Array.isArray(remove_tags) ? remove_tags : parseTags(remove_tags);
    
    // Validate we have something to do
    if (tagsToAdd.length === 0 && tagsToRemove.length === 0) {
      throw new Error('No tags to add or remove specified');
    }
    
    // Get current tags
    const query = `
      query getProductTags($id: ID!) {
        product(id: $id) {
          id
          title
          tags
        }
      }
    `;
    
    const data = await this.shopifyClient.query(query, { id: productId });
    
    if (!data.product) {
      throw new Error(`Product not found: ${productId}`);
    }
    
    // Calculate new tags
    let currentTags = data.product.tags || [];
    let newTags = [...currentTags];
    
    // Remove tags first (to handle case where same tag is in both add and remove)
    if (tagsToRemove.length > 0) {
      newTags = newTags.filter(tag => 
        !tagsToRemove.some(removeTag => 
          tag.toLowerCase() === removeTag.toLowerCase()
        )
      );
    }
    
    // Add new tags (avoid duplicates)
    if (tagsToAdd.length > 0) {
      for (const tagToAdd of tagsToAdd) {
        if (!newTags.some(tag => tag.toLowerCase() === tagToAdd.toLowerCase())) {
          newTags.push(tagToAdd);
        }
      }
    }
    
    // Update product with new tags
    const mutation = `
      mutation updateProductTags($input: ProductInput!) {
        productUpdate(input: $input) {
          product {
            id
            title
            tags
          }
          userErrors {
            field
            message
          }
        }
      }
    `;
    
    const variables = {
      input: {
        id: productId,
        tags: newTags
      }
    };
    
    const result = await this.shopifyClient.mutate(mutation, variables);
    
    // Calculate what actually changed
    const addedTags = newTags.filter(tag => 
      !currentTags.some(oldTag => oldTag.toLowerCase() === tag.toLowerCase())
    );
    const removedTags = currentTags.filter(tag => 
      !newTags.some(newTag => newTag.toLowerCase() === tag.toLowerCase())
    );
    
    return {
      product: {
        id: result.productUpdate.product.id,
        title: result.productUpdate.product.title,
        tags: result.productUpdate.product.tags
      },
      changes: {
        added: addedTags,
        removed: removedTags,
        previousTags: currentTags,
        currentTags: result.productUpdate.product.tags
      }
    };
  }
}

// Export singleton instance
export const manageTagsTool = new ManageTagsTool();

/**
 * Convenience wrapper for adding tags only
 */
export class AddTagsTool extends BaseTool {
  get metadata() {
    return {
      name: 'add_tags_to_product',
      description: 'Add tags to a product',
      inputSchema: {
        type: 'object',
        properties: {
          product_id: { 
            type: 'string', 
            description: 'Product ID' 
          },
          tags: { 
            type: 'array', 
            items: { type: 'string' }, 
            description: 'Tags to add'
          }
        },
        required: ['product_id', 'tags']
      }
    };
  }

  async execute(args) {
    const manageTags = new ManageTagsTool();
    return manageTags.execute({
      product_id: args.product_id,
      add_tags: args.tags,
      remove_tags: []
    });
  }
}

export const addTagsTool = new AddTagsTool();

/**
 * Convenience wrapper for removing tags only
 */
export class RemoveTagsTool extends BaseTool {
  get metadata() {
    return {
      name: 'remove_tags_from_product',
      description: 'Remove tags from a product',
      inputSchema: {
        type: 'object',
        properties: {
          product_id: { 
            type: 'string', 
            description: 'Product ID' 
          },
          tags: { 
            type: 'array', 
            items: { type: 'string' }, 
            description: 'Tags to remove'
          }
        },
        required: ['product_id', 'tags']
      }
    };
  }

  async execute(args) {
    const manageTags = new ManageTagsTool();
    return manageTags.execute({
      product_id: args.product_id,
      add_tags: [],
      remove_tags: args.tags
    });
  }
}

export const removeTagsTool = new RemoveTagsTool();