import { LoaderFunctionArgs, json } from '@remix-run/node';
import { useLoaderData } from '@remix-run/react';
import { requireUserId } from '../lib/auth.server'; // To protect the route
import StreamingChatPage from '../../src/features/chat/StreamingChatPage.jsx'; // Path to the existing component

// Loader to ensure user is authenticated before accessing the chat page.
// It can also pass initial data needed by StreamingChatPage if any.
export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await requireUserId(request); // Protects the route
  // For now, just returning userId. Later, we might load initial chat context or selected convId.
  return json({ userId });
}

export default function IndexRoute() {
  const { userId } = useLoaderData<typeof loader>();

  // The StreamingChatPage component might need props like convId, refreshConversations.
  // These will be wired up in a subsequent step when StreamingChatPage itself is refactored.
  // For now, we render it simply.
  // The old App.jsx used to pass `selectedChat` as `convId` and `fetchConversations` as `refreshConversations`.
  // We'll need to manage `selectedChat` state within the Remix structure, possibly in root.tsx or here.
  
  // Placeholder for selectedChat state - this will need proper state management in Remix
  const selectedChatId = null; // Or get from URL params, or a global state solution for Remix

  // refreshConversations prop is no longer needed as navigation handles list updates.
  // const refreshConversations = () => console.log("Placeholder: refreshConversations called");

  return (
    <StreamingChatPage
      key={selectedChatId === null ? "new_chat_instance_key" : selectedChatId}
      convId={selectedChatId}
      // refreshConversations={refreshConversations} // Removed
      // userId={userId} // StreamingChatPage might need userId directly or via context
    />
  );
}
