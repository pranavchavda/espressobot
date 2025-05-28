import { json, LoaderFunctionArgs } from '@remix-run/node';
import { prisma } from '../lib/db.server';
import { requireUserId } from '../lib/auth.server';

export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await requireUserId(request); // Ensures user is authenticated

  const conversations = await prisma.conversation.findMany({
    where: { userId: userId },
    orderBy: { createdAt: 'desc' }, // Order by creation date, descending
    select: { // Select only necessary fields
      id: true,
      title: true,
      createdAt: true,
      // filename: true, // Include if frontend needs it, was in original Flask model
    },
  });

  return json(conversations);
}

// This route might eventually have a UI to display conversations.
// For now, a placeholder component is fine if it's primarily for API use via useLoaderData.
// If it's truly API-only and part of a larger page, it might not need a default export
// or could be a resource route (e.g., .ts file).
// Given the path, Remix expects a default export.
export default function ConversationsIndexPage() {
  // const conversations = useLoaderData<typeof loader>();
  // Render UI for conversations list here
  return (
    <div>
      <p>Conversations API endpoint. Data is loaded via the loader.</p>
      {/* Example of how data might be used: */}
      {/* <pre>{JSON.stringify(conversations, null, 2)}</pre> */}
    </div>
  );
}
