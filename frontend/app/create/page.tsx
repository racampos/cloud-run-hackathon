/**
 * Lab creation page (NEW ARCHITECTURE)
 * Creates lab and redirects to detail page for Planner interaction
 */

'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCreateLab } from '@/lib/hooks';

export default function CreateLabPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const createLab = useCreateLab();

  const examples = [
    'Create a lab to teach passwords in a Cisco router. Include enable, console and vty passwords, and password encryption. 20-minute lab.',
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

      // Navigate to lab detail page where Planner conversation will happen
      router.push(`/labs/${result.lab_id}`);
    } catch (error) {
      console.error('Failed to create lab:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
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
                Describe your lab requirements to get started
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-2xl w-full">
          <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-8">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                <svg
                  className="w-8 h-8 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Start with Your Lab Idea
              </h2>
              <p className="text-gray-600">
                The Planner will collaborate with you to refine requirements
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label
                  htmlFor="prompt"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Describe your lab
                </label>
                <textarea
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={6}
                  className="block w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="Example: Create a CCNA-level lab teaching static routing with 2 routers. Include basic IP addressing and ping verification. Estimated time: 30 minutes."
                  disabled={createLab.isPending}
                />
              </div>

              <button
                type="submit"
                disabled={!prompt.trim() || createLab.isPending}
                className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {createLab.isPending ? (
                  <span className="flex items-center justify-center gap-2">
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
                  'Start Collaboration with Planner'
                )}
              </button>

              {createLab.isError && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">
                    Error: {(createLab.error as Error).message}
                  </p>
                </div>
              )}
            </form>

            {/* Examples */}
            <div className="mt-8 pt-8 border-t border-gray-200">
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Example prompts:
              </h3>
              <div className="space-y-2">
                {examples.map((example, index) => (
                  <button
                    key={index}
                    onClick={() => setPrompt(example)}
                    disabled={createLab.isPending}
                    className="block w-full text-left px-4 py-3 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg text-sm text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="text-blue-600 mr-2">💡</span>
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <p className="mt-6 text-center text-sm text-gray-500">
            After creating, you'll chat with the Planner to refine your requirements
          </p>
        </div>
      </main>
    </div>
  );
}
