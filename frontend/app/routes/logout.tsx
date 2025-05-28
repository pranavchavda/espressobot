import { ActionFunctionArgs, redirect, LoaderFunctionArgs } from '@remix-run/node'; // Or appropriate Remix package
import { logout as performLogout, getUserId } from '../lib/auth.server'; // Corrected relative path

// Action function to handle the logout request (typically via POST)
export async function action({ request }: ActionFunctionArgs) {
  return performLogout(request);
}

// Loader function to redirect if someone tries to GET this route
// Or, if they are not logged in, no need to "logout" again, redirect to login.
export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await getUserId(request);
  if (!userId) {
    return redirect('/login'); // If not logged in, redirect to login
  }
  // If logged in and they GET this page, perhaps redirect to home,
  // or just let it be a page that does nothing on GET (action expects POST).
  // For simplicity, redirecting to home if logged in.
  return redirect('/');
}

// Remix convention often expects a default export for a route module,
// even if it only has an action/loader and doesn't render a page.
// This component will likely never be rendered if the loader always redirects.
export default function LogoutPage() {
  return (
    <div>
      <h1>Logging out...</h1>
      <p>You should be redirected shortly. If not, please click the link below.</p>
      <form method="post" action="/logout">
        <button type="submit">Logout</button>
      </form>
      <p><a href="/">Go to Homepage</a></p>
    </div>
  );
}
