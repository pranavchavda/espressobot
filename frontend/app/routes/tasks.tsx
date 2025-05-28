import { json, LoaderFunctionArgs, MetaFunction } from '@remix-run/node';
import { useLoaderData } from '@remix-run/react';
import { requireUserId } from '../lib/auth.server';
// We will need to import Prisma or other services if fetching actual task data here later.
import TasksPage from '../../src/pages/TasksPage.jsx'; // Path to the existing component

export const meta: MetaFunction = () => {
  return [ // Remix v2+ Meta Syntax
    { title: "My Tasks" },
    { name: "description", content: "Manage your tasks." },
  ];
};

export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await requireUserId(request); // Ensures user is authenticated
  
  // Placeholder for actual task data loading.
  // In the future, this loader will fetch task lists, tasks, auth status for Google Tasks, etc.
  // For now, we pass minimal data or mock data if TasksPage requires it.
  const placeholderTaskData = {
    isGoogleAuthAuthorized: false, // This would come from a migrated google_tasks.is_authorized
    taskLists: [], // Placeholder
    tasks: [],     // Placeholder
  };

  return json({ userId, tasksData: placeholderTaskData });
}

export default function TasksRoute() {
  const { userId, tasksData } = useLoaderData<typeof loader>();

  // The TasksPage component will be refactored later to use Remix forms and actions,
  // and to consume data from this loader.
  // For now, we pass placeholder data. It might need specific props.
  return <TasksPage tasksData={tasksData} />;
}
