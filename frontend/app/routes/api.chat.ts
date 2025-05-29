import {
  json,
  ActionFunctionArgs,
  unstable_parseMultipartFormData,
  unstable_createMemoryUploadHandler,
  // NodeOnDiskFile, // If using a disk handler
} from '@remix-run/node'; // Or your specific runtime package
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

  // if (request.method !== 'POST') { // This check is usually not needed as Remix routes typically handle specific methods
  //   return json({ message: 'Method not allowed' }, { status: 405 });
  // }

  const uploadHandler = unstable_createMemoryUploadHandler({
    maxPartSize: 20 * 1024 * 1024, // 20MB limit for files in memory
    // filter: ({ contentType }) => contentType.startsWith("image/"), // Optional: only allow images
  });

  // let processedImageUrl: string | null = null; // Placeholder for conceptual image URL processing

  try {
    const formData = await unstable_parseMultipartFormData(request, uploadHandler);

    const userMessageContentField = formData.get('message');
    const convIdStringField = formData.get('conv_id');
    const imageFile = formData.get('image_file') as File; // Type assertion for memory handler
    const imageUrlString = formData.get('image_url') as string;

    const userMessageContent = typeof userMessageContentField === 'string' ? userMessageContentField : '';
    const convIdString = typeof convIdStringField === 'string' ? convIdStringField : null;
    
    // Validate that either message content or an image is present
    if (userMessageContent.trim().length === 0 && (!imageFile || imageFile.size === 0) && (!imageUrlString || imageUrlString.trim().length === 0)) {
      return json({ error: 'Message content or an image is required' }, { status: 400 });
    }

    if (imageFile && imageFile.size > 0) {
      console.log('Received image file in api.chat:', imageFile.name, imageFile.type, imageFile.size);
      // In a real app, you'd upload this to storage and get a URL.
      // For now, just acknowledge it.
      // processedImageUrl = `user_uploaded_files/${imageFile.name}`; // Placeholder
    } else if (imageUrlString && typeof imageUrlString === 'string' && imageUrlString.trim().length > 0) {
      console.log('Received image URL in api.chat:', imageUrlString);
      // processedImageUrl = imageUrlString;
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

  // --- Placeholder for AI Agent Logic (if any part runs before streaming) ---
  const tool_calls: any[] = []; 
  const suggestions: string[] = ["Suggestion 1 (placeholder)", "Suggestion 2 (placeholder)"]; 
  // --- End Placeholder ---

  // DO NOT Store the assistant's message here.
  // This will be handled by api.chat.stream.ts after the stream completes.
  // await prisma.message.create({
  //   data: {
  //     conv_id: conversationId,
  //     role: 'assistant',
  //     content: assistantResponseContent, // This is removed
  //   },
  // });

  return json({
    conv_id: conversationId,
    tool_calls: tool_calls, 
    suggestions: suggestions, 
  });

  } catch (error: any) { // Ensure 'error' is typed if accessing properties like error.message
    console.error("Error processing chat form data:", error);
    // Check if it's a known error type or just a generic message
    const errorMessage = error.message || 'Failed to process request.';
    return json({ error: errorMessage }, { status: 500 });
  }
}

// No default export needed for a resource route that only has an action.
// If Remix requires it, export default function ApiChatRoute() { return null; }
// However, for .ts files used as resource routes, no default export is typically needed.
