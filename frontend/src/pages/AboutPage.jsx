import React from 'react';

function AboutPage() {
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6 text-zinc-800 dark:text-zinc-200">About EspressoBot</h1>
      
      <div className="prose dark:prose-invert max-w-none">
        <p className="text-lg mb-6">
          EspressoBot is your AI-powered assistant designed to help you with a variety of tasks, from answering questions to helping you manage your daily work. Here's what you can do with EspressoBot:
        </p>

        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-3 text-indigo-600 dark:text-indigo-400">🤖 General Assistance</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Ask general knowledge questions</li>
              <li>Get help with coding problems</li>
              <li>Generate creative writing or content ideas</li>
              <li>Get explanations on complex topics</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3 text-indigo-600 dark:text-indigo-400">📝 Task Management</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Create and manage your to-do lists</li>
              <li>Set reminders and deadlines</li>
              <li>Organize your daily schedule</li>
              <li>Track your progress on projects</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3 text-indigo-600 dark:text-indigo-400">💡 Tips for Best Results</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Be specific with your requests</li>
              <li>Provide context when needed</li>
              <li>Break down complex tasks into smaller steps</li>
              <li>Don't hesitate to ask for clarification</li>
            </ul>
          </section>

          <section className="bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg">
            <h3 className="text-lg font-semibold mb-2 text-blue-700 dark:text-blue-300">💬 Example Queries</h3>
            <ul className="space-y-2">
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"What's the weather like today?"</span>
              </li>
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"Help me write a Python function to sort a list"</span>
              </li>
              <li className="bg-white dark:bg-zinc-800 p-3 rounded border border-blue-200 dark:border-blue-800">
                <span className="font-mono text-sm text-blue-600 dark:text-blue-300">"Add a task to review project proposal by Friday"</span>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}

export default AboutPage;
