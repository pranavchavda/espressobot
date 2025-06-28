

import { Agent } from '@openai/agents';

const userClarificationAgent = new Agent({
  name: 'User_Clarification_Agent',
  description: 'Interacts with the user to resolve ambiguity and gather required information for a task.',
  instructions: 'You are a specialized agent for clarifying user requests. Your goal is to ask questions to understand the user\'s needs and gather all necessary information before a task can be executed. You do not have any tools.',
  tools: [],
  model: 'gpt-4.1-mini'
});

export default userClarificationAgent;

