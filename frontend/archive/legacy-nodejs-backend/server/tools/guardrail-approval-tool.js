/**
 * Guardrail Approval Tool - Uses OpenAI SDK's needsApproval feature
 * to give users control over when guardrails should enforce completion
 */

import { tool } from '@openai/agents';
import { z } from 'zod';

/**
 * Create a tool that checks if guardrails should be enforced
 * This tool will interrupt execution and ask for user approval
 */
export function createGuardrailApprovalTool(bulkOperationState, sseEmitter) {
  // Set the global SSE emitter so approval tool can use it
  global.currentSseEmitter = sseEmitter;
  
  return tool({
    name: 'check_guardrail_enforcement',
    description: 'Check if bulk operation guardrails should be enforced when agent seems to be returning incomplete work',
    parameters: z.object({
      agentOutput: z.string().describe('The current agent output'),
      completedItems: z.number().describe('Number of items completed so far'),
      expectedItems: z.number().describe('Total expected items'),
      isReturningControl: z.boolean().describe('Whether agent is trying to return control')
    }),
    
    // Dynamic approval logic based on the situation
    needsApproval: async (runContext, input) => {
      // Don't need approval if operation is clearly complete
      if (input.completedItems >= input.expectedItems) {
        return false;
      }
      
      // Don't need approval if agent is still actively working
      if (!input.isReturningControl) {
        return false;
      }
      
      // Check if the output looks like it might be incomplete
      const outputLower = input.agentOutput.toLowerCase();
      const looksIncomplete = 
        outputLower.includes('here\'s how') ||
        outputLower.includes('here is how') ||
        outputLower.includes('you can use') ||
        outputLower.includes('graphql') ||
        outputLower.includes('mutation') ||
        outputLower.includes('example') ||
        (outputLower.includes('create') && !outputLower.includes('created'));
      
      if (looksIncomplete) {
        // Emit SSE event to show UI
        if (sseEmitter) {
          sseEmitter('guardrail_decision_needed', {
            message: 'Agent response may be incomplete. Would you like to enforce completion?',
            context: {
              completedItems: input.completedItems,
              expectedItems: input.expectedItems,
              outputPreview: input.agentOutput.substring(0, 200) + '...'
            }
          });
        }
        
        // This will trigger an interruption
        return true;
      }
      
      return false;
    },
    
    execute: async ({ agentOutput, completedItems, expectedItems, isReturningControl }) => {
      // If we get here, the user approved enforcing guardrails
      console.log('[GuardrailApproval] User approved guardrail enforcement');
      
      return {
        enforceGuardrails: true,
        reason: 'User approved enforcing completion of remaining items',
        remainingItems: expectedItems - completedItems
      };
    }
  });
}

/**
 * Helper to handle the approval flow in the orchestrator
 */
export async function handleGuardrailApproval(result, runContext, sseEmitter) {
  if (!result.interruptions || result.interruptions.length === 0) {
    return { needsApproval: false };
  }
  
  // Find guardrail approval requests
  const guardrailApprovals = result.interruptions.filter(
    i => i.rawItem.name === 'check_guardrail_enforcement'
  );
  
  if (guardrailApprovals.length === 0) {
    return { needsApproval: false };
  }
  
  // For now, we'll auto-approve to test the flow
  // In production, this would wait for user input via WebSocket or polling
  console.log('[GuardrailApproval] Approval needed - waiting for user decision...');
  
  // Simulate user decision (in real implementation, this would wait for frontend)
  const userDecision = await simulateUserDecision(guardrailApprovals[0]);
  
  if (userDecision.approved) {
    runContext.approveTool(guardrailApprovals[0]);
    return { 
      needsApproval: true, 
      approved: true,
      state: result.state 
    };
  } else {
    runContext.rejectTool(guardrailApprovals[0]);
    return { 
      needsApproval: true, 
      approved: false,
      state: result.state 
    };
  }
}

/**
 * Simulate user decision for testing
 * In production, this would be replaced with actual user input handling
 */
async function simulateUserDecision(approvalItem) {
  // For testing, let's approve if the output mentions GraphQL/mutations
  const args = JSON.parse(approvalItem.rawItem.arguments);
  const outputLower = args.agentOutput.toLowerCase();
  
  const shouldApprove = 
    outputLower.includes('graphql') || 
    outputLower.includes('mutation') ||
    outputLower.includes('here\'s how');
  
  console.log(`[GuardrailApproval] Simulated decision: ${shouldApprove ? 'APPROVE' : 'REJECT'}`);
  
  return {
    approved: shouldApprove,
    reason: shouldApprove ? 
      'Output appears to be instructions rather than execution' : 
      'Output seems complete enough'
  };
}