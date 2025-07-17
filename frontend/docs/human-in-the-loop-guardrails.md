# Human-in-the-Loop Guardrails Implementation

## Overview
Implemented a human-in-the-loop guardrail system using OpenAI SDK's `needsApproval` feature. This allows users to control when guardrails should enforce task completion vs allowing the agent to return early.

## Key Components

### 1. Guardrail Approval Tool (`/server/tools/guardrail-approval-tool.js`)
- Uses OpenAI SDK's `needsApproval` feature for interruptions
- Detects incomplete responses (e.g., "here's how", GraphQL mutations without execution)
- Emits SSE events when user decision is needed
- Handles approval/rejection flow

### 2. Approval Tool (`/server/tools/approval-tool.js`)
- General-purpose approval tool for high-risk operations
- Supports various operation types (bulk updates, deletions, price changes)
- 5-minute timeout for user decisions
- Stores pending approvals in memory

### 3. Frontend Demo (`/public/guardrail-approval-demo.html`)
- Shows real-time SSE connection status
- Displays approval requests with context
- Allows users to approve/reject guardrail enforcement
- Logs all events for debugging

### 4. API Handler (`/server/api/guardrail-decision-handler.js`)
- POST `/api/guardrail-decision` endpoint
- Processes user decisions (approve/reject)
- Updates approval status via SSE

## Integration Points

### Orchestrator Integration
```javascript
// Create guardrail approval tool
const guardrailApprovalTool = createGuardrailApprovalTool(bulkOperationState, sseEmitter);

// Pass to orchestrator
const orchestrator = createOrchestratorAgent(
  contextualMessage, 
  orchestratorContext, 
  spawnMCPAgent, 
  builtInSearchTool, 
  guardrailApprovalTool, 
  userProfile
);

// Handle interruptions after execution
if (result && result.interruptions && result.interruptions.length > 0) {
  const approvalResult = await handleGuardrailApproval(result, orchestratorContext, sseEmitter);
  if (approvalResult.needsApproval && approvalResult.approved) {
    // Re-run with enforcement
    result = await run(orchestrator, { state: approvalResult.state }, runOptions);
  }
}
```

### Bulk Operation Guardrail Update
Modified the bulk operation output guardrail to support approval:
```javascript
// Store context for approval tool
bulkOperationState.pendingGuardrailDecision = {
  pattern: 'announce_and_stop',
  reasoning: analysis.reasoning,
  completedItems: bulkOperationState.completedItems,
  expectedItems: bulkOperationState.expectedItems
};

return {
  outputInfo: `Detected announce and stop pattern: ${analysis.reasoning}`,
  tripwireTriggered: true,
  requiresApproval: true  // Signal that human approval is needed
};
```

## Usage Flow

1. **Agent Detection**: Agent detects potential incomplete response
2. **Tool Invocation**: Agent calls `check_guardrail_enforcement` tool
3. **Approval Check**: Tool's `needsApproval` function evaluates the situation
4. **SSE Event**: If approval needed, emits `guardrail_decision_needed` event
5. **User Interface**: Frontend shows approval card with context
6. **User Decision**: User clicks "Enforce Completion" or "Allow Current Response"
7. **API Call**: Frontend sends decision to `/api/guardrail-decision`
8. **Resolution**: Tool execution continues based on decision
9. **Re-execution**: If approved, orchestrator re-runs with enforcement

## Benefits

1. **User Control**: Users decide when to enforce completion vs accepting partial results
2. **Context Awareness**: Shows completion progress and output preview
3. **Efficiency**: Only interrupts when genuinely incomplete
4. **Flexibility**: Works with existing guardrail system
5. **Real-time**: SSE provides immediate feedback

## Testing

To test the implementation:
1. Open `/guardrail-approval-demo.html` in browser
2. Run a bulk operation task (e.g., "create 5 smart collections")
3. When agent tries to return instructions instead of executing, approval UI appears
4. Choose to enforce completion or allow the response
5. Monitor event log for the flow

## Future Enhancements

1. **Persistence**: Store approval history in database
2. **Patterns**: Learn from user decisions to improve detection
3. **Batch Operations**: Handle multiple approval requests
4. **WebSocket**: Replace SSE with bidirectional communication
5. **Mobile UI**: Responsive approval interface