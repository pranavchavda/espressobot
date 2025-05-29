import { json, LoaderFunctionArgs, MetaFunction } from '@remix-run/node';
import { useLoaderData, useParams } from '@remix-run/react';
import { requireUserId } from '../lib/auth.server';
import { prisma } from '../lib/db.server';
import StreamingChatPage from '../../src/features/chat/StreamingChatPage.jsx'; // Path to the existing component
import { Conversation } from '@prisma/client'; // Import type

export const meta: MetaFunction<typeof loader> = ({ data }) => {
  const conversationTitle = data?.conversation?.title || "Chat";
  return [ // Remix v2+ Meta Syntax
    { title: conversationTitle },
    { name: "description", content: `Conversation: ${conversationTitle}` },
  ];
};

export async function loader({ request, params }: LoaderFunctionArgs) {
  const userId = await requireUserId(request);
  const { chatId } = params;

  if (!chatId) {
    throw json({ message: 'Chat ID is required' }, { status: 400 });
  }

  const conversationId = parseInt(chatId, 10);
  if (isNaN(conversationId)) {
    throw json({ message: 'Invalid Chat ID format' }, { status: 400 });
  }

  const conversation = await prisma.conversation.findUnique({
    where: { id: conversationId },
    include: {
      messages: {
        orderBy: { createdAt: 'asc' },
        select: { id: true, role: true, content: true, createdAt: true, tool_call_id: true, tool_name: true },
      },
    },
  });

  if (!conversation) {
    throw json({ message: 'Conversation not found' }, { status: 404 });
  }

  if (conversation.userId !== userId) {
    throw json({ message: 'Access denied: Conversation does not belong to the current user' }, { status: 403 });
  }

  // We pass the whole conversation (including messages) to the component.
  // StreamingChatPage will need to be refactored to use this initial set of messages.
  return json({ conversation });
}

export default function ChatConversationRoute() {
  const { conversation } = useLoaderData<typeof loader>();
  const params = useParams(); // To get chatId again if needed, or it's in conversation.id

  // The StreamingChatPage component has been refactored.
  // It handles initial messages and convId.
  // The `refreshConversations` prop is no longer needed.
  // const refreshConversations = () => console.log("Placeholder: refreshConversations in c.$chatId.tsx"); // Removed

  return (
    <StreamingChatPage
      key={conversation.id} // Use conversation ID for the key
      convId={conversation.id}
      initialMessages={conversation.messages} // Pass initial messages
      // refreshConversations={refreshConversations} // Removed
    />
  );
}
