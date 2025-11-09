/**
 * Lab creation page - styled to look like Planner tab
 */

'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCreateLab } from '@/lib/hooks';
import { StatusBadge } from '@/components/shared/StatusBadge';

export default function CreateLabPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const createLab = useCreateLab();

  const examples = [
    'Create a CCNA static routing lab with 2 routers and basic connectivity',
    'Build a lab teaching OSPF adjacency with 3 routers in a triangle topology',
    'Design a VLAN configuration lab for 2 switches and 4 PCs',
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!prompt.trim()) return;

    try {
      const result = await createLab.mutateAsync({
        prompt: prompt.trim(),
        dry_run: false,
        enable_rca: true,
      });

      // Navigate to lab detail page
      router.push(`/labs/${result.lab_id}`);
    } catch (error) {
      console.error('Failed to create lab:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-gray-600 hover:text-gray-900 transition-colors"
              >
                ← Back to Library
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Create New Lab</h1>
                <p className="mt-1 text-sm text-gray-600">
                  Describe your lab and collaborate with the AI Planner
                </p>
              </div>
            </div>
            <StatusBadge status="pending" className="text-base px-4 py-2" />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          {/* Tab Navigation (disabled) */}
          <div className="bg-white border-b border-gray-200">
            <nav className="flex items-center px-6 py-2" aria-label="Tabs">
              <div className="flex items-center">
                <div className="flex items-center gap-3 px-6 py-4 text-base font-medium border-b-4 border-blue-500 text-blue-600">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full border-2 bg-gray-100 border-gray-300">
                    <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                  </div>
                  Planner
                </div>
                <div className="w-12 h-1 mx-2">
                  <div className="h-full bg-gray-300"></div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="flex items-center gap-3 px-6 py-4 text-base font-medium border-b-4 border-transparent text-gray-400 cursor-not-allowed">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full border-2 bg-gray-100 border-gray-300">
                    <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                  </div>
                  Designer
                </div>
                <div className="w-12 h-1 mx-2">
                  <div className="h-full bg-gray-300"></div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="flex items-center gap-3 px-6 py-4 text-base font-medium border-b-4 border-transparent text-gray-400 cursor-not-allowed">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full border-2 bg-gray-100 border-gray-300">
                    <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                  </div>
                  Author
                </div>
                <div className="w-12 h-1 mx-2">
                  <div className="h-full bg-gray-300"></div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="flex items-center gap-3 px-6 py-4 text-base font-medium border-b-4 border-transparent text-gray-400 cursor-not-allowed">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full border-2 bg-gray-100 border-gray-300">
                    <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                  </div>
                  Validator
                </div>
              </div>
            </nav>
          </div>

          {/* Planner Tab Content */}
          <div className="flex flex-col bg-white rounded-lg border border-gray-200 shadow-sm" style={{ height: '600px' }}>
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-semibold text-gray-900">
                Planner Conversation
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Describe your lab requirements to get started
              </p>
            </div>

            {/* Welcome message */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="flex justify-start mb-4">
                <div className="max-w-[80%] rounded-lg px-4 py-3 bg-gray-100">
                  <div className="text-xs font-medium mb-1 text-gray-600">
                    Planner Agent
                  </div>
                  <div className="whitespace-pre-wrap text-sm text-gray-900">
                    Welcome! I'm the Planner Agent. I'll help you design your networking lab.
                    {'\n\n'}
                    Please describe the lab you'd like to create. Include details like:
                    {'\n'}- Topic and difficulty level (e.g., "CCNA static routing")
                    {'\n'}- Number and types of devices
                    {'\n'}- Learning objectives
                    {'\n'}- Estimated time for completion
                  </div>
                </div>
              </div>

              {/* Example prompts */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">Try these examples:</p>
                {examples.map((example, index) => (
                  <button
                    key={index}
                    onClick={() => setPrompt(example)}
                    disabled={createLab.isPending}
                    className="block w-full text-left px-4 py-3 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg text-sm text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    💡 {example}
                  </button>
                ))}
              </div>
            </div>

            {/* Input Form */}
            <div className="p-4 border-t border-gray-200 bg-gray-50">
              {createLab.isError && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">
                    Error: {(createLab.error as Error).message}
                  </p>
                </div>
              )}
              <form onSubmit={handleSubmit} className="flex space-x-2">
                <input
                  type="text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Type your lab description..."
                  disabled={createLab.isPending}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-900 placeholder:text-gray-400"
                />
                <button
                  type="submit"
                  disabled={!prompt.trim() || createLab.isPending}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {createLab.isPending ? (
                    <span className="flex items-center gap-2">
                      <svg
                        className="animate-spin h-5 w-5"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Creating...
                    </span>
                  ) : (
                    'Start Lab'
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
