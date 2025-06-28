
import { Agent } from '@openai/agents';

const channelSpecialsAgent = new Agent({
  name: 'Channel_Specials_Agent',
  description: 'Handles MAP, promotional collections, and channel-specific logic (e.g., Breville, Miele sales, etc).',
  instructions: 'You are a specialized agent for managing channel-specific sales and promotions. Use the available tools to manage MAP and Miele sales.',
  tools: [
    'manage_map_sales',
    'manage_miele_sales'
  ],
  model: 'gpt-4.1-mini'
});

export default channelSpecialsAgent;
