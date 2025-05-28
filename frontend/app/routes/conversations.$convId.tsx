import { json, LoaderFunctionArgs, ActionFunctionArgs } from '@remix-run/node';
import { prisma } from '../lib/db.server';
import { requireUserId } from '../lib/auth.server';

export async function loader({ request, params }: LoaderFunctionArgs) {
  const userId = await requireUserId(request); // Ensures user is authenticated
  const { convId } = params;

  if (!convId) {
    throw json({ message: 'Conversation ID is required' }, { status: 400 });
  }

  const conversationId = parseInt(convId, 10);
  if (isNaN(conversationId)) {
    throw json({ message: 'Invalid Conversation ID format' }, { status: 400 });
  }

  // Fetch the conversation and its messages
  // Ensure the conversation belongs to the current user
  const conversation = await prisma.conversation.findUnique({
    where: { 
      id: conversationId,
      // userId: userId, // Implicitly checked by fetching messages through this conversation if it's user-owned
    },
    include: {
      messages: {
        orderBy: { createdAt: 'asc' }, // Order messages by creation time
        select: { // Select necessary fields for messages
          id: true,
          role: true,
          content: true,
          createdAt: true,
          tool_call_id: true,
          tool_name: true,
        },
      },
    },
  });

  if (!conversation) {
    throw json({ message: 'Conversation not found' }, { status: 404 });
  }

  // Verify ownership if not strictly enforced by query structure (prisma.conversation.findFirstOrThrow({ where: {id: conversationId, userId: userId}})
  if (conversation.user_id !== userId) {
     throw json({ message: 'Access denied: Conversation does not belong to the current user' }, { status: 403 });
  }

  return json(conversation.messages); 
  // Or return json(conversation) if frontend needs conversation details + messages
}

export async function action({ request, params }: ActionFunctionArgs) {
  const userId = await requireUserId(request);
  const { convId } = params;

  if (request.method !== 'DELETE') {
    return json({ message: 'Method not allowed' }, { status: 405 });
  }

  if (!convId) {
    return json({ message: 'Conversation ID is required' }, { status: 400 });
  }

  const conversationId = parseInt(convId, 10);
  if (isNaN(conversationId)) {
    return json({ message: 'Invalid Conversation ID format' }, { status: 400 });
  }

  // Verify ownership before deleting
  const conversation = await prisma.conversation.findUnique({
    where: { id: conversationId },
    select: { userId: true }, // Only need userId for ownership check
  });

  if (!conversation) {
    return json({ message: 'Conversation not found' }, { status: 404 });
  }

  if (conversation.userId !== userId) {
    return json({ message: 'Access denied: Conversation does not belong to the current user' }, { status: 403 });
  }

  try {
    await prisma.conversation.delete({
      where: { id: conversationId },
    });
    // On successful deletion, you might want to redirect or send a success message.
    // Redirecting to the conversations list is a common pattern.
    // return redirect('/conversations'); 
    return json({ success: true, message: 'Conversation deleted successfully' });
  } catch (error) {
    console.error("Error deleting conversation:", error);
    return json({ message: 'Failed to delete conversation' }, { status: 500 });
  }
}

// This page would typically display the messages of a single conversation.
// For now, a placeholder.
export default function ConversationDetailsPage() {
  // const messages = useLoaderData<typeof loader>();
  // Render UI for displaying messages here
  return (
    <div>
      <p>Conversation Details Page. Messages are loaded via the loader.</p>
      {/* Example of how data might be used: */}
      {/* <pre>{JSON.stringify(messages, null, 2)}</pre> */}
    </div>
  );
}
