import { json, ActionFunctionArgs, LoaderFunctionArgs } from '@remix-run/node'; // Or appropriate Remix package
import { prisma } from '../lib/db.server';
import { requireUserId } from '../lib/auth.server';
import { User } from '@prisma/client';

// Loader to get user profile
export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await requireUserId(request); // Ensures user is authenticated
  
  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: { // Select only the fields needed for the profile
      email: true,
      name: true,
      bio: true,
      // id: true, // Optionally include id if needed by frontend
      // created_at: true, // Optionally include created_at
    },
  });

  if (!user) {
    // This should ideally not happen if requireUserId works correctly and DB is consistent
    throw json({ message: 'User not found' }, { status: 404 });
  }

  return json(user);
}

// Action to update user profile
export async function action({ request }: ActionFunctionArgs) {
  const userId = await requireUserId(request); // Ensures user is authenticated

  if (request.method !== 'PUT') {
    return json({ message: 'Method not allowed' }, { status: 405 });
  }

  const formData = await request.formData();
  const name = formData.get('name');
  const bio = formData.get('bio');

  const dataToUpdate: { name?: string; bio?: string } = {};

  if (name !== null) {
    if (typeof name !== 'string') {
      return json({ errors: { name: 'Invalid name', bio: null } }, { status: 400 });
    }
    dataToUpdate.name = name;
  }

  if (bio !== null) {
    if (typeof bio !== 'string') {
      return json({ errors: { name: null, bio: 'Invalid bio' } }, { status: 400 });
    }
    dataToUpdate.bio = bio;
  }

  if (Object.keys(dataToUpdate).length === 0) {
    return json({ message: 'No fields to update' }, { status: 400 });
  }

  try {
    const updatedUser = await prisma.user.update({
      where: { id: userId },
      data: dataToUpdate,
      select: { // Return the updated profile data
        email: true,
        name: true,
        bio: true,
      },
    });
    return json({ message: 'Profile updated successfully', user: updatedUser }, { status: 200 });
  } catch (error) {
    console.error("Profile update error:", error);
    return json({ message: 'Failed to update profile' }, { status: 500 });
  }
}

// This route is API-only and does not need a default export component
// or can export a null component.
// If Remix requires a default export for all route files,
// a simple null component or a minimal message can be provided.
export default function ProfileApiRoute() {
  return null; // Or a simple message like <p>Profile API Endpoint</p>
}
