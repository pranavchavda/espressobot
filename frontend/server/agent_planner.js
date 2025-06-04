import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { Agent, Runner } from 'openai-agents-js';

const prisma = new PrismaClient();
const router = Router();

/**
 * POST /api/agent/planner
 * Body: { conv_id: number }
 * Returns: { plan: string } where plan is the Planner agent's output.
 */
router.post('/', async (req, res) => {
  try {
    const { conv_id } = req.body || {};
    if (typeof conv_id !== 'number') {
      return res.status(400).json({ error: 'Request body must include numeric conv_id' });
    }

    const conversation = await prisma.conversations.findUnique({
      where: { id: conv_id },
    });
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation not found' });
    }

    // Load full message history for the conversation
    const messages = await prisma.messages.findMany({
      where: { conv_id },
      orderBy: { id: 'asc' },
    });

    const historyText = messages
      .map((m) => `${m.role}: ${m.content}`)
      .join('\n');

    const plannerAgent = new Agent({
      name: 'Planner',
      instructions: `You are the Planner sub-agent in an agentic workflow. You receive a user's task
description and must output a JSON plan of discrete tool-driven steps for the primary agent to execute.
Respond ONLY with a JSON object of the form:
  {"tasks":[{"name":<tool_name>,"args":<tool_args_object>}, ...]}
Do not include any additional commentary, markdown, or text beyond the JSON.`,
      model: process.env.PLANNER_AGENT_MODEL || 'o4-mini',
    });

    // Run the agent on the conversation history
    const result = await Runner.run(plannerAgent, historyText);

    return res.json({ plan: result.finalOutput });
  } catch (err) {
    console.error('Planner agent error:', err);
    return res.status(500).json({ error: err.message || 'Internal server error' });
  }
});

export default router;