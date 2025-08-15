/**
 * API handler for guardrail approval decisions
 * This endpoint receives approval/rejection decisions from the frontend
 */

import { approveOperation, rejectOperation } from '../tools/approval-tool.js';

export async function handleGuardrailDecision(req, res) {
  try {
    const { approvalId, approved } = req.body;
    
    if (!approvalId) {
      return res.status(400).json({ 
        error: 'Missing approvalId' 
      });
    }
    
    console.log(`[GuardrailDecision] Received decision for ${approvalId}: ${approved ? 'APPROVED' : 'REJECTED'}`);
    
    let success;
    if (approved) {
      success = approveOperation(approvalId);
    } else {
      success = rejectOperation(approvalId);
    }
    
    if (success) {
      return res.json({ 
        success: true, 
        message: `Operation ${approved ? 'approved' : 'rejected'}` 
      });
    } else {
      return res.status(404).json({ 
        error: 'Approval request not found or already processed' 
      });
    }
  } catch (error) {
    console.error('[GuardrailDecision] Error handling decision:', error);
    return res.status(500).json({ 
      error: 'Internal server error' 
    });
  }
}

/**
 * Express route setup
 */
export function setupGuardrailRoutes(app) {
  app.post('/api/guardrail-decision', handleGuardrailDecision);
  
  console.log('[GuardrailDecision] Routes configured');
}