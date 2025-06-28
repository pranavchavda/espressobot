
import { Agent } from '@openai/agents';

const inventoryAgent = new Agent({
  name: 'Inventory_Agent',
  description: 'Handles inventory policies and synchronization with SkuVault.',
  instructions: 'You are a specialized agent for managing inventory. Use the available tools to manage inventory policies and sync with SkuVault.',
  tools: [
    'manage_inventory_policy',
    'manage_skuvault_kits',
    'upload_to_skuvault',
    'update_skuvault_prices',
    'update_skuvault_prices_v2'
  ],
  model: 'gpt-4.1-mini'
});

export default inventoryAgent;
