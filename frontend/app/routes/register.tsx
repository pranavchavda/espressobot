import { json, redirect, ActionFunctionArgs, LoaderFunctionArgs } from '@remix-run/node'; // Or appropriate Remix package
import { prisma } from '../lib/db.server'; // Corrected relative path
import { createUserSession, getUserId, hashPassword } from '../lib/auth.server'; // Corrected relative path
import { User } from '@prisma/client'; // Import User type
import AuthFormComponent from '../../src/features/auth/LoginPage.jsx'; // Adjusted import path

// Placeholder for the actual Register Page component
// import RegisterPageComponent from '~/components/RegisterPage'; // Example path

export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await getUserId(request);
  if (userId) {
    return redirect('/'); // If already logged in, redirect to homepage
  }
  return json({});
}

export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const email = formData.get('email');
  const password = formData.get('password');
  const name = formData.get('name') || null; // Optional name

  if (typeof email !== 'string' || !email.includes('@')) {
    return json({ errors: { email: 'Invalid email address', password: null, name: null } }, { status: 400 });
  }

  if (typeof password !== 'string' || password.length < 6) {
    return json({ errors: { email: null, password: 'Password must be at least 6 characters', name: null } }, { status: 400 });
  }

  if (name !== null && typeof name !== 'string') {
    return json({ errors: { email: null, password: null, name: 'Invalid name' } }, { status: 400 });
  }
  
  const lowercaseEmail = email.toLowerCase();
  const existingUser = await prisma.user.findUnique({
    where: { email: lowercaseEmail },
  });

  if (existingUser) {
    return json({ errors: { email: 'A user already exists with this email', password: null, name: null } }, { status: 400 });
  }

  const hashedPassword = await hashPassword(password);
  
  // Determine whitelisting status
  const allowedEmailsStr = process.env.ALLOWED_EMAILS || '';
  const allowedEmails = allowedEmailsStr.split(',').map(e => e.trim().toLowerCase());
  const isWhitelisted = allowedEmails.includes(lowercaseEmail);

  try {
    const newUser = await prisma.user.create({
      data: {
        email: lowercaseEmail,
        password_hash: hashedPassword,
        name: name,
        is_whitelisted: isWhitelisted,
      },
    });

    // Option 1: Automatically log in the user after registration
    // return createUserSession(newUser.id, '/'); 

    // Option 2: Redirect to login page with a success message (or just return success)
    // For now, let's return a success message and let the user log in separately.
    // The frontend can then show this message and guide the user to login.
    return json({ success: true, message: 'Registration successful! Please login.', errors: null }, { status: 201 });

  } catch (error) {
    // Handle potential database errors (e.g., unique constraint violation if somehow missed)
    console.error("Registration error:", error);
    return json({ errors: { email: 'An unexpected error occurred during registration.', password: null, name: null } }, { status: 500 });
  }
}

// Basic component structure - this will be replaced or integrated
export default function RegisterPage() {
  // This route component now renders the actual registration form
  // by using the AuthFormComponent in 'register' mode.
  return <AuthFormComponent mode="register" />;
}
