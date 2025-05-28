import { json, LoaderFunctionArgs, MetaFunction } from '@remix-run/node';
import { useLoaderData } from '@remix-run/react';
import { requireUserId } from '../lib/auth.server';
import { prisma } from '../lib/db.server';
import ProfilePage from '../../src/pages/ProfilePage.jsx'; // Path to the existing component

export const meta: MetaFunction = () => {
  return [ // Remix v2+ Meta Syntax
    { title: "User Profile" },
    { name: "description", content: "View and manage your user profile." },
  ];
};

export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await requireUserId(request); // Ensures user is authenticated
  
  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: {
      email: true,
      name: true,
      bio: true,
      // id: true, // Not typically needed by the ProfilePage component itself for display
    },
  });

  if (!user) {
    // This case should ideally be rare if requireUserId works and user is in DB
    throw json({ message: 'User not found' }, { status: 404 });
  }

  return json({ user });
}

export default function ProfileRoute() {
  const { user } = useLoaderData<typeof loader>();

  // The ProfilePage component will be refactored later to use Remix forms
  // and handle data submission to the /api/profile action.
  // For now, it might just display the data passed to it (if it accepts a 'user' prop)
  // or it might have its own internal data fetching (which we'll remove).
  // We pass the user data as a prop for now.
  return <ProfilePage user={user} />;
}
