
import { Agent } from '@openai/agents';

const taskPlanningAgent = new Agent({
  name: 'Task_Planning_Agent',
  description: 'Decomposes complex user goals into a step-by-step plan.',
  instructions: 'You are a specialized agent for breaking down complex tasks into a sequence of smaller, manageable steps. You do not execute tasks yourself, but create a plan for the orchestrator to follow.',
  tools: [],
  model: 'o3'
});

export default taskPlanningAgent;
