import { BaseTool } from './base-tool.js';

/**
 * Native JavaScript implementation of update_status tool
 * Updates product status (ACTIVE, DRAFT, ARCHIVED)
 */
export class UpdateStatusTool extends BaseTool {
  get metadata() {
    return {
      name: 'update_product_status',
      description: 'Update product status (ACTIVE, DRAFT, ARCHIVED)',
      inputSchema: {
        type: 'object',
        properties: {
          product_id: { 
            type: 'string', 
            description: 'Product ID (numeric or GID format)' 
          },
          status: { 
            type: 'string', 
            enum: ['ACTIVE', 'DRAFT', 'ARCHIVED'], 
            description: 'New product status' 
          }
        },
        required: ['product_id', 'status']
      }
    };
  }

  /**
   * Execute status update
   */
  async execute(args) {
    const { product_id, status } = args;
    
    this.log('Updating product status', { product_id, status });
    
    // Normalize product ID
    const productId = this.shopifyClient.normalizeId(product_id);
    
    // Validate status
    const validStatuses = ['ACTIVE', 'DRAFT', 'ARCHIVED'];
    if (!validStatuses.includes(status)) {
      throw new Error(`Invalid status: ${status}. Must be one of: ${validStatuses.join(', ')}`);
    }
    
    // Get current product details
    const query = `
      query getProductStatus($id: ID!) {
        product(id: $id) {
          id
          title
          status
        }
      }
    `;
    
    const data = await this.shopifyClient.query(query, { id: productId });
    
    if (!data.product) {
      throw new Error(`Product not found: ${productId}`);
    }
    
    const previousStatus = data.product.status;
    
    // Skip if status is already the same
    if (previousStatus === status) {
      return {
        product: data.product,
        message: `Product already has status: ${status}`,
        changed: false
      };
    }
    
    // Update product status
    const mutation = `
      mutation updateProductStatus($input: ProductInput!) {
        productUpdate(input: $input) {
          product {
            id
            title
            status
            publishedAt
            updatedAt
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
        status: status
      }
    };
    
    const result = await this.shopifyClient.mutate(mutation, variables);
    
    return {
      product: result.productUpdate.product,
      changes: {
        previousStatus,
        currentStatus: result.productUpdate.product.status
      },
      changed: true,
      message: `Product status updated from ${previousStatus} to ${status}`
    };
  }
}

// Export singleton instance
export const updateStatusTool = new UpdateStatusTool();

/**
 * Convenience tool for publishing products (setting status to ACTIVE)
 */
export class PublishProductTool extends BaseTool {
  get metadata() {
    return {
      name: 'publish_product',
      description: 'Publish a product by setting its status to ACTIVE',
      inputSchema: {
        type: 'object',
        properties: {
          product_id: { 
            type: 'string', 
            description: 'Product ID to publish' 
          }
        },
        required: ['product_id']
      }
    };
  }

  async execute(args) {
    const updateStatus = new UpdateStatusTool();
    return updateStatus.execute({
      product_id: args.product_id,
      status: 'ACTIVE'
    });
  }
}

export const publishProductTool = new PublishProductTool();

/**
 * Convenience tool for unpublishing products (setting status to DRAFT)
 */
export class UnpublishProductTool extends BaseTool {
  get metadata() {
    return {
      name: 'unpublish_product',
      description: 'Unpublish a product by setting its status to DRAFT',
      inputSchema: {
        type: 'object',
        properties: {
          product_id: { 
            type: 'string', 
            description: 'Product ID to unpublish' 
          }
        },
        required: ['product_id']
      }
    };
  }

  async execute(args) {
    const updateStatus = new UpdateStatusTool();
    return updateStatus.execute({
      product_id: args.product_id,
      status: 'DRAFT'
    });
  }
}

export const unpublishProductTool = new UnpublishProductTool();

/**
 * Convenience tool for archiving products
 */
export class ArchiveProductTool extends BaseTool {
  get metadata() {
    return {
      name: 'archive_product',
      description: 'Archive a product by setting its status to ARCHIVED',
      inputSchema: {
        type: 'object',
        properties: {
          product_id: { 
            type: 'string', 
            description: 'Product ID to archive' 
          }
        },
        required: ['product_id']
      }
    };
  }

  async execute(args) {
    const updateStatus = new UpdateStatusTool();
    return updateStatus.execute({
      product_id: args.product_id,
      status: 'ARCHIVED'
    });
  }
}

export const archiveProductTool = new ArchiveProductTool();