import { json, LoaderFunctionArgs } from '@remix-run/node'; // Or appropriate Remix package
import { getCurrentUser } from '../lib/auth.server'; // Using the getCurrentUser utility

export async function loader({ request }: LoaderFunctionArgs) {
  const user = await getCurrentUser(request);

  if (user) {
    // Return only necessary, non-sensitive user fields
    const { id, email, name, is_whitelisted } = user;
    return json({ 
      isAuthenticated: true, 
      user: { id, email, name, is_whitelisted } 
    });
  } else {
    return json({ isAuthenticated: false, user: null });
  }
}

// This route is API-only and does not need a default export component
// that renders UI. Returning null is fine.
export default function AuthCheckApiRoute() {
  return null;
}
