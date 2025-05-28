// No loader needed for a static "About" page usually.
// If it needed data, a loader function would go here.
// Example:
// import { json, LoaderFunctionArgs } from '@remix-run/node';
// export async function loader({ request }: LoaderFunctionArgs) { /* ... */ }

import AboutPage from '../../src/pages/AboutPage.jsx'; // Path to the existing component

export default function AboutRoute() {
  // const data = useLoaderData<typeof loader>(); // If loader was present
  return <AboutPage />;
}

// Optional: Add a MetaFunction for page title, description, etc.
import { MetaFunction } from '@remix-run/node';
export const meta: MetaFunction = () => {
  return [ // Remix v2+ Meta Syntax
    { title: "About EspressoBot" },
    { name: "description", content: "Learn more about the EspressoBot application." },
  ];
};
