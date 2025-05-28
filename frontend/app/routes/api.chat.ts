import { json, ActionFunctionArgs } from '@remix-run/node';
import { prisma } from '../lib/db.server';
import { requireUserId } from '../lib/auth.server';
import { Conversation, Message } from '@prisma/client'; // Import types

// Helper function to generate a simple title (can be expanded later)
function generateConversationTitle(firstMessage: string): string {
  const words = firstMessage.split(/\s+/);
  if (words.length === 0) return "New Chat";
  // Take up to 5 words, add ellipsis if longer
  return words.slice(0, 5).join(' ') + (words.length > 5 ? '...' : '');
}

export async function action({ request }: ActionFunctionArgs) {
  const userId = await requireUserId(request);

  if (request.method !== 'POST') {
    return json({ message: 'Method not allowed' }, { status: 405 });
  }

  const formData = await request.formData();
  const userMessageContent = formData.get('message');
  const convIdString = formData.get('conv_id'); // Can be null or string

  if (typeof userMessageContent !== 'string' || userMessageContent.trim().length === 0) {
    return json({ error: 'Message content is required' }, { status: 400 });
  }

  let conversationId: number;
  let conversation: Conversation | null = null;

  if (convIdString && typeof convIdString === 'string') {
    const parsedId = parseInt(convIdString, 10);
    if (isNaN(parsedId)) {
      return json({ error: 'Invalid conversation ID format' }, { status: 400 });
    }
    conversationId = parsedId;

    // Verify conversation exists and belongs to the user
    conversation = await prisma.conversation.findUnique({
      where: { id: conversationId },
    });

    if (!conversation) {
      return json({ error: 'Conversation not found' }, { status: 404 });
    }
    if (conversation.userId !== userId) {
      return json({ error: 'Access denied to this conversation' }, { status: 403 });
    }
  } else {
    // Create a new conversation
    const title = generateConversationTitle(userMessageContent);
    // The 'filename' field was marked non-null unique in Prisma schema.
    // This was based on Flask's `Conversation.filename`.
    // For now, let's generate a unique filename, e.g., using timestamp + random string.
    // This needs to be revisited if 'filename' has a more specific meaning from Flask.
    const uniqueFilename = `chat_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
    
    const newConversation = await prisma.conversation.create({
      data: {
        userId: userId,
        title: title,
        filename: uniqueFilename, // Placeholder - needs proper generation or review
      },
    });
    conversationId = newConversation.id;
    conversation = newConversation;
  }

  // Store the user's message
  await prisma.message.create({
    data: {
      conv_id: conversationId,
      role: 'user',
      content: userMessageContent,
    },
  });

  // --- Placeholder for AI Agent Logic ---
  const assistantResponseContent = "This is a placeholder response from the assistant. AI logic will be implemented later.";
  const steps: any[] = [{ type: 'placeholder', detail: 'AI agent processing not yet implemented.' }];
  const tool_calls: any[] = [];
  const suggestions: string[] = ["Suggestion 1 (placeholder)", "Suggestion 2 (placeholder)"];
  // --- End Placeholder ---

  // Store the assistant's message
  await prisma.message.create({
    data: {
      conv_id: conversationId,
      role: 'assistant',
      content: assistantResponseContent,
    },
  });

  return json({
    conv_id: conversationId,
    response: assistantResponseContent,
    steps: steps.length, // Or actual steps array
    tool_calls: tool_calls,
    suggestions: suggestions,
  });
}

// No default export needed for a resource route that only has an action.
// If Remix requires it, export default function ApiChatRoute() { return null; }
// However, for .ts files used as resource routes, no default export is typically needed.
