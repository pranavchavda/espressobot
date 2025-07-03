# EspressoBot Autonomy Test Scenarios

## Test Cases for Improved Autonomy

### 1. Specific Value Commands (Should Execute Immediately)

#### Test 1.1: Direct Price Update
**Input**: "Update SKU123 price to $49.99"
**Expected**: 
- Intent analysis: High autonomy
- Agent executes immediately without confirmation
- Shows: "Updating SKU123 price to $49.99..."

#### Test 1.2: Question with Specific Values
**Input**: "Can you update the Breville Barista Pro to $899?"
**Expected**:
- Intent analysis: High autonomy (question with specific values)
- Agent executes immediately
- Shows: "Updating the Breville Barista Pro to $899..."

#### Test 1.3: Multiple Specific Items
**Input**: "Set these products to active: SKU123, SKU456, SKU789"
**Expected**:
- Intent analysis: High autonomy (specific list)
- Agent executes all three immediately
- Shows progress for each item

### 2. High-Risk Operations (Should Confirm)

#### Test 2.1: Bulk Operation Over 50 Items
**Input**: "Update all product prices by 10%"
**Expected**:
- Intent analysis: Medium autonomy (high-risk)
- Agent shows approval UI
- Description: "This will update prices for 287 products by 10%"

#### Test 2.2: Destructive Operation
**Input**: "Delete all discontinued products"
**Expected**:
- Intent analysis: Medium autonomy
- Shows approval request with list of products to delete
- Only proceeds after approval

### 3. Ambiguous Requests (Should Clarify)

#### Test 3.1: Missing Critical Information
**Input**: "Update the price"
**Expected**:
- Intent analysis: Low autonomy
- Agent asks: "Which product and what price?"

#### Test 3.2: Vague Request
**Input**: "Can you help with pricing?"
**Expected**:
- Intent analysis: Low autonomy
- Agent asks for specifics about what pricing help is needed

### 4. Progressive Autonomy

#### Test 4.1: Building Trust
**Sequence**:
1. "Update SKU123 to $49.99" → Executes immediately
2. "Also update SKU456 to $79.99" → Executes immediately
3. "Update all coffee grinders by 5%" → Executes with summary (user has been approving)

**Expected**: System recognizes pattern of approvals and increases autonomy

### 5. Conversation Context Persistence

#### Test 5.1: Context Awareness
**Sequence**:
1. "Can you update the Breville Barista Pro Black Stainless to $899?"
2. Agent executes
3. "Also update the Olive color to the same price"

**Expected**: Agent understands "same price" from context and executes

### 6. Approval UI Tests

#### Test 6.1: Approval Flow
**Input**: "Delete all products with zero inventory" (assuming 75 products)
**Expected**:
- Approval UI shows:
  - Operation: Delete Products
  - Impact: Will delete 75 products
  - Risk Level: High (yellow/red indicator)
- Approve button → Operation proceeds
- Reject button → Operation cancelled

#### Test 6.2: Approval History
**After multiple approvals/rejections**:
- System shows recent decision history
- Adapts autonomy based on patterns

## Running the Tests

1. Start the frontend dev server:
   ```bash
   cd /home/pranav/espressobot/frontend
   npm run dev
   ```

2. Test each scenario in order
3. Verify console logs show correct intent analysis
4. Confirm UI behavior matches expectations

## Success Criteria

- ✅ Commands with specific values execute immediately
- ✅ Questions with specific values are treated as commands
- ✅ High-risk operations show approval UI
- ✅ Ambiguous requests prompt for clarification
- ✅ Conversation context is maintained
- ✅ Progressive autonomy based on user patterns
- ✅ No unnecessary "Should I proceed?" confirmations

## Common Issues to Avoid

1. **Over-confirmation**: Asking "Should I update SKU123 to $49.99?" when user already said to do it
2. **Missing context**: Not understanding references to previous messages
3. **Ignoring patterns**: Not learning from user's approval/rejection history
4. **Slow execution**: Waiting for confirmation on clear, specific instructions