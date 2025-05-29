import { LoaderFunctionArgs } from '@remix-run/node'; // Or appropriate Remix package
import { requireUserId } from '../lib/auth.server';
import { prisma } from '../lib/db.server'; // Add this
// We'll need to import or define ReadableStream and Response utilities if not directly from @remix-run/node
// For Node.js environments, ReadableStream is globally available.

// Simulate an async generator that yields chunks of data (like an AI agent)
async function* generatePlaceholderStream(message: string, convId?: string) { 
  yield 'Thinking...\n\n'; // Initial thought or status
  await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay

  const words = [
    `You said: "${message}". `,
    `This is a placeholder response for conversation ${convId || 'new chat'}. `,
    `The real AI agent logic is complex and will be implemented later. `,
    `For now, I am just streaming back a few chunks of text. `,
    `Each word, or group of words, could be a separate chunk. `,
    `This demonstrates the streaming capability.`,
  ];

  for (const word of words) {
    yield word;
    await new Promise(resolve => setTimeout(resolve, 100)); // Simulate delay between chunks
  }
  yield '\n\nDone streaming placeholder content.';
}

export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await requireUserId(request);
  const url = new URL(request.url);
  const userMessage = url.searchParams.get('message') || 'No message provided';
  const convIdString = url.searchParams.get('conv_id');

  if (!convIdString) {
    return new Response("Conversation ID is required for streaming.", { status: 400 });
  }
  const conversationId = parseInt(convIdString, 10);
  if (isNaN(conversationId)) {
    return new Response("Invalid Conversation ID format.", { status: 400 });
  }

  // Verify conversation ownership
  const conversation = await prisma.conversation.findFirst({
    where: { id: conversationId, userId: userId }
  });
  if (!conversation) {
    return new Response("Conversation not found or access denied.", { status: 404 });
  }

  let fullResponseContent = ''; // Accumulator

  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      try {
        for await (const chunk of generatePlaceholderStream(userMessage, convIdString)) {
          fullResponseContent += chunk; // Accumulate
          controller.enqueue(encoder.encode(chunk));
        }
        
        // After stream finishes, save the full response
        if (fullResponseContent.trim().length > 0) {
          // Remove the "Thinking..." and "Done streaming placeholder content." parts if they are fixed.
          // This is a simple way, might need more robust parsing if content is dynamic.
          let contentToSave = fullResponseContent.trim();
          if (contentToSave.startsWith('Thinking...\n\n')) {
            contentToSave = contentToSave.substring('Thinking...\n\n'.length).trim();
          }
          if (contentToSave.endsWith('\n\nDone streaming placeholder content.')) {
            contentToSave = contentToSave.substring(0, contentToSave.length - '\n\nDone streaming placeholder content.'.length).trim();
          }
          
          if (contentToSave.length > 0) {
            await prisma.message.create({
              data: {
                conv_id: conversationId,
                role: 'assistant',
                content: contentToSave,
              },
            });
            console.log(`Saved full assistant response for convId: ${conversationId}`);
          }
        }

      } catch (error: any) {
        console.error('Error during stream generation or saving:', error);
        controller.enqueue(encoder.encode(`\n\nError: Could not generate full response. ${error.message}`));
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8', 
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}

// No default export component needed for this API route.
