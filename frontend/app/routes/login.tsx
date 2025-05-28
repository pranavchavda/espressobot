import { json, redirect, ActionFunctionArgs, LoaderFunctionArgs } from '@remix-run/node'; // Or appropriate Remix package
import { prisma } from '../lib/db.server'; // Corrected relative path
import { createUserSession, getUserId, verifyPassword } from '../lib/auth.server'; // Corrected relative path
import { User } from '@prisma/client'; // Import User type from Prisma
import LoginPageForm from '../../src/features/auth/LoginPage.jsx'; // Adjusted import path

// Placeholder for the actual Login Page component from your existing frontend
// We'll integrate this later. For now, a simple component is fine.
// import LoginPageComponent from '~/components/LoginPage'; // Example path

export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await getUserId(request);
  if (userId) {
    return redirect('/'); // If already logged in, redirect to homepage
  }
  return json({}); // No data needed for the login page itself on GET
}

export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const email = formData.get('email');
  const password = formData.get('password');
  const redirectTo = formData.get('redirectTo') || '/'; // Default redirect after login

  if (typeof email !== 'string' || !email.includes('@')) {
    return json({ errors: { email: 'Invalid email address', password: null } }, { status: 400 });
  }

  if (typeof password !== 'string' || password.length < 6) { // Basic password validation
    return json({ errors: { email: null, password: 'Password must be at least 6 characters' } }, { status: 400 });
  }

  if (typeof redirectTo !== 'string') {
    return json({ errors: { email: null, password: 'Invalid redirect path' } }, { status: 400 });
  }

  const user = await prisma.user.findUnique({
    where: { email: email.toLowerCase() }, // Case-insensitive email lookup
  });

  if (!user) {
    return json({ errors: { email: 'No user found with this email', password: null } }, { status: 401 });
  }

  const isPasswordValid = await verifyPassword(password, user.password_hash);
  if (!isPasswordValid) {
    return json({ errors: { email: null, password: 'Invalid password' } }, { status: 401 });
  }

  if (!user.is_whitelisted) {
    return json({ errors: { email: 'Access denied. User not whitelisted.', password: null } }, { status: 403 });
  }

  return createUserSession(user.id, redirectTo);
}

// Basic component structure - this will be replaced by your actual LoginPage.jsx
export default function LoginPage() {
  // This route component now renders the actual login form.
  // The LoginPageForm component uses useActionData and useNavigation internally.
  return <LoginPageForm />;
}
