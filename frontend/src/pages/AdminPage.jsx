import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@common/button';
import { Heading } from '@common/heading';
import { Database, FileText, Brain, Settings, ChevronLeft } from 'lucide-react';

export default function AdminPage() {
  const navigate = useNavigate();

  const adminFeatures = [
    {
      title: 'Memory Management',
      description: 'View, search, and manage user memories',
      icon: Database,
      path: '/admin/memory',
      color: 'text-blue-600'
    },
    {
      title: 'Prompt Library',
      description: 'Manage system prompt fragments for RAG',
      icon: FileText,
      path: '/admin/prompt-library',
      color: 'text-green-600'
    },
    {
      title: 'Agent Analytics',
      description: 'View agent performance and usage stats',
      icon: Brain,
      path: '/admin/analytics',
      color: 'text-purple-600',
      disabled: true
    },
    {
      title: 'System Settings',
      description: 'Configure system-wide settings',
      icon: Settings,
      path: '/admin/settings',
      color: 'text-orange-600',
      disabled: true
    }
  ];

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-6">
        <Button
          outline
          onClick={() => navigate('/')}
          className="mb-4"
        >
          <ChevronLeft className="h-4 w-4 mr-2" />
          Back to Chat
        </Button>
        <Heading level={1}>Admin Dashboard</Heading>
        <p className="text-zinc-600 dark:text-zinc-400 mt-2">
          Manage EspressoBot system components and settings
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {adminFeatures.map((feature) => (
          <div
            key={feature.path}
            className={`bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 cursor-pointer transition-all hover:shadow-lg ${
              feature.disabled ? 'opacity-60 cursor-not-allowed' : ''
            }`}
            onClick={() => !feature.disabled && navigate(feature.path)}
          >
            <div className="flex items-center gap-3 mb-3">
              <feature.icon className={`h-6 w-6 ${feature.color}`} />
              <Heading level={3}>{feature.title}</Heading>
              {feature.disabled && (
                <span className="text-sm font-normal text-zinc-500 ml-auto">
                  Coming Soon
                </span>
              )}
            </div>
            <p className="text-zinc-600 dark:text-zinc-400">{feature.description}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 p-4 bg-zinc-100 dark:bg-zinc-800 rounded-lg">
        <Heading level={3} className="mb-2">Quick Stats</Heading>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-zinc-600 dark:text-zinc-400">Total Memories:</span>
            <span className="ml-2 font-medium">Loading...</span>
          </div>
          <div>
            <span className="text-zinc-600 dark:text-zinc-400">Prompt Fragments:</span>
            <span className="ml-2 font-medium">Loading...</span>
          </div>
          <div>
            <span className="text-zinc-600 dark:text-zinc-400">Active Agents:</span>
            <span className="ml-2 font-medium">3</span>
          </div>
        </div>
      </div>
    </div>
  );
}