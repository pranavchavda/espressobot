import { tool } from '@openai/agents';
import { z } from 'zod';

/**
 * Approval Tool for Human-in-the-Loop Operations
 * 
 * This tool allows agents to request approval for high-risk operations
 * before executing them, implementing the OpenAI Agents JS pattern.
 */

// Store pending approvals (in production, use a proper store)
const pendingApprovals = new Map();

/**
 * Request approval for an operation
 */
export const requestApprovalTool = tool({
  name: 'request_approval',
  description: 'Request user approval for a high-risk operation',
  parameters: z.object({
    operationType: z.string().describe('Type of operation (e.g., "Bulk Price Update", "Delete Products")'),
    description: z.string().describe('Clear description of what will be done'),
    impact: z.string().describe('Impact description (e.g., "Will affect 87 products")'),
    details: z.any().optional().describe('Additional details about the operation'),
    riskLevel: z.enum(['low', 'medium', 'high']).optional().default('medium')
  }),
  needsApproval: false, // This tool itself doesn't need approval
  execute: async ({ operationType, description, impact, details, riskLevel }) => {
    const approvalId = `approval_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Store the pending approval
    const approval = {
      id: approvalId,
      operationType,
      description,
      impact,
      details,
      riskLevel,
      status: 'pending',
      createdAt: new Date().toISOString()
    };
    
    pendingApprovals.set(approvalId, approval);
    
    // Emit SSE event for approval request
    const sseEmitter = global.currentSseEmitter;
    if (sseEmitter) {
      sseEmitter('approval_required', {
        id: approvalId,
        operation_type: operationType,
        description,
        impact,
        details,
        risk_level: riskLevel
      });
    }
    
    // Wait for approval/rejection (with timeout)
    const timeout = 300000; // 5 minutes
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const currentApproval = pendingApprovals.get(approvalId);
      
      if (currentApproval.status === 'approved') {
        pendingApprovals.delete(approvalId);
        return {
          approved: true,
          message: 'Operation approved by user',
          approvalId
        };
      }
      
      if (currentApproval.status === 'rejected') {
        pendingApprovals.delete(approvalId);
        return {
          approved: false,
          message: 'Operation rejected by user',
          approvalId
        };
      }
      
      // Check for abort signal
      if (global.currentAbortSignal?.aborted) {
        pendingApprovals.delete(approvalId);
        return {
          approved: false,
          message: 'Operation cancelled - execution interrupted',
          approvalId
        };
      }
      
      // Wait a bit before checking again
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Timeout
    pendingApprovals.delete(approvalId);
    return {
      approved: false,
      message: 'Approval request timed out after 5 minutes',
      approvalId
    };
  }
});

/**
 * Handle approval from frontend
 */
export function approveOperation(approvalId) {
  const approval = pendingApprovals.get(approvalId);
  if (approval && approval.status === 'pending') {
    approval.status = 'approved';
    
    // Emit status update
    const sseEmitter = global.currentSseEmitter;
    if (sseEmitter) {
      sseEmitter('approval_status', {
        id: approvalId,
        status: 'approved'
      });
    }
    
    return true;
  }
  return false;
}

/**
 * Handle rejection from frontend
 */
export function rejectOperation(approvalId) {
  const approval = pendingApprovals.get(approvalId);
  if (approval && approval.status === 'pending') {
    approval.status = 'rejected';
    
    // Emit status update
    const sseEmitter = global.currentSseEmitter;
    if (sseEmitter) {
      sseEmitter('approval_status', {
        id: approvalId,
        status: 'rejected'
      });
    }
    
    return true;
  }
  return false;
}

/**
 * Check if an operation needs approval based on criteria
 */
export function needsApproval(operation) {
  // High-risk operations that always need approval
  if (operation.type === 'delete' && operation.count > 5) return true;
  if (operation.type === 'bulk_update' && operation.count > 50) return true;
  if (operation.priceChangePercent && Math.abs(operation.priceChangePercent) > 50) return true;
  if (operation.affectsAllProducts) return true;
  
  // Check user preference from conversation history
  const autonomyLevel = global.currentIntentAnalysis?.level || 'high';
  if (autonomyLevel === 'low') return true;
  if (autonomyLevel === 'medium' && operation.count > 10) return true;
  
  return false;
}

console.log('[ApprovalTool] Initialized with human-in-the-loop support');