import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import OpenAI from 'openai';
import { Agent, Runner } from 'openai-agents-js';

const prisma = new PrismaClient();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const router = Router();

/**
 * POST /api/agent/run
 * Orchestrate agent flow: plan tasks then execute them sequentially with SSE.
 * Body: { conv_id?: number, message: string }
 * SSE events: { type: 'task_update', tasks: Task[] }, { done: true }
 */
router.post('/', async (req, res) => {
  try {
    const { message, conv_id } = req.body || {};
    if (typeof message !== 'string' || !message.trim()) {
      return res.status(400).json({ error: 'Request body must include a non-empty message string' });
    }

    const USER_ID = 1;
    let conversation;
    if (conv_id) {
      conversation = await prisma.conversations.findUnique({ where: { id: conv_id } });
      if (!conversation) {
        return res.status(404).json({ error: 'Conversation not found' });
      }
    } else {
      conversation = await prisma.conversations.create({
        data: {
          user_id: USER_ID,
          title: `Conversation ${new Date().toISOString()}`,
          filename: `conversation-${Date.now()}.json`,
        },
      });
    }

    // Persist user message
    await prisma.messages.create({
      data: {
        conv_id: conversation.id,
        role: 'user',
        content: message,
      },
    });

    // Fetch full history for context
    const history = await prisma.messages.findMany({
      where: { conv_id: conversation.id },
      orderBy: { id: 'asc' },
    });
    const inputMessages = history.map((m) => ({
      type: 'message',
      role: m.role === 'assistant' ? 'assistant' : 'user',
      content: m.content,
    }));
    const historyText = history.map((m) => `${m.role}: ${m.content}`).join('\n');

    // Initialize SSE headers and notify client of conversation ID
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();
    // Emit conversation ID so frontend can maintain context
    res.write(`data: ${JSON.stringify({ conv_id: conversation.id })}\n\n`);

    const plannerAgent = new Agent({
      name: 'Planner',
      instructions: `You are the Planner sub-agent in an agentic workflow. You receive a user's task
description and must output a JSON plan of discrete tool-driven steps for the primary agent to execute.
Respond ONLY with a JSON object of the form:
  {"tasks":[{"name":<tool_name>,"args":<tool_args_object>}, ...]}
Do not include any additional commentary, markdown, or text beyond the JSON.`,
      model: process.env.PLANNER_AGENT_MODEL || 'o4-mini',
    });
    const plannerRes = await Runner.run(plannerAgent, message);
    let plan;
    try {
      plan = JSON.parse(plannerRes.finalOutput);
    } catch {
      plan = { tasks: [] };
    }

    // Build initial task list
    const tasks = (plan.tasks || []).map((t, i) => ({
      id: i,
      content: `${t.name}: ${JSON.stringify(t.args)}`,
      status: 'pending',
      subtasks: [],
    }));
    // Send initial tasks
    res.write(`data: ${JSON.stringify({ type: 'task_update', tasks })}\n\n`);

    // Sequentially execute each task
    for (let i = 0; i < tasks.length; i++) {
      tasks[i].status = 'in_progress';
      res.write(`data: ${JSON.stringify({ type: 'task_update', tasks })}\n\n`);

      try {
        // Call tools via Responses API for each task
        const toolStream = await openai.responses.create({
          model: process.env.OPENAI_MODEL,
          input: inputMessages,
          text: { format: { type: 'text' } },
          tools: [
            {
              type: 'web_search_preview',
              user_location: { type: 'approximate' },
              search_context_size: 'medium',
            },
            {
              type: 'mcp',
              server_label: 'Shopify_MCP',
              server_url:
                // process.env.MCP_SERVER_URL ||
                // process.env.MCP_MEMORY_SERVER_URL ||
                'https://webhook-listener-pranavchavda.replit.app/mcp',
              allowed_tools: [
                'upload_to_sku_vault',
                "run_full_shopify_graphql_mutation",
                "run_full_shopify_graphql_query",        
                'update_pricing',
                'product_create_full',
                'add_product_to_collection',
                'get_collections',
                'set_metafield',
                'variant_create',
                'product_create',
                'get_single_product',
                'search_products',
                'create_feature_box',
                'get_product',
                'product_update',
                'product_tags_add',
                'product_tags_remove'
              ],
              require_approval: 'never',
            },
          ],
          stream: false,
        });
        const rawOutput = toolStream.output;
        const output = Array.isArray(rawOutput)
          ? rawOutput.map(part => typeof part === 'object' ? JSON.stringify(part) : part).join('')
          : typeof rawOutput === 'object'
          ? JSON.stringify(rawOutput)
          : rawOutput || '';
        tasks[i].subtasks.push({ content: output, status: 'completed' });
        tasks[i].status = 'completed';
      } catch (err) {
        tasks[i].status = 'error';
        tasks[i].subtasks.push({ content: `${err.message}`, status: 'error' });
      }
      res.write(`data: ${JSON.stringify({ type: 'task_update', tasks })}\n\n`);
    }

    await prisma.agent_runs.create({ data: { conv_id: conversation.id, tasks: JSON.stringify(tasks) } });

    // After all tasks, invoke the primary assistant to synthesize task results
    try {
      // Prepare a summary prompt including original user request and each task output
      const summaryMessages = [
        { role: 'system', content: `You are a helpful assistant. The user asked: "${message}". Based on the results of the executed tasks below, present a clear, concise response to the user.` },
        ...tasks.map((t) => ({
          role: 'system',
          content: `Task ${t.id} (${t.content}) output: ${t.subtasks.map((s) => s.content).join(' ')}`,
        })),
      ];
      const chatStream = await openai.chat.completions.create({
        model: process.env.OPENAI_MODEL,
        messages: summaryMessages,
        stream: true,
      });
      let assistantResponse = '';
      for await (const part of chatStream) {
        const delta = part.choices?.[0]?.delta?.content || '';
        assistantResponse += delta;
        res.write(`data: ${JSON.stringify({ delta })}\n\n`);
      }
      // Persist the final assistant summary to the database
      await prisma.messages.create({ data: { conv_id: conversation.id, role: 'assistant', content: assistantResponse } });
    } catch (e) {
      console.error('Error in final assistant synthesis:', e);
    }

    // Signal completion of agent run
    res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
    res.end();
  } catch (err) {
    console.error('Master agent error:', err);
    res.write(`data: ${JSON.stringify({ error: err.message || 'Internal server error' })}\n\n`);
    res.end();
  }
});

export default router;