/**
 * Lab creation prompt input component
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCreateLab } from '@/lib/hooks';

export function PromptInput() {
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
    <div className="max-w-3xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label
            htmlFor="prompt"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Describe the lab you want to create
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

        <div className="flex items-center justify-between">
          <button
            type="submit"
            disabled={!prompt.trim() || createLab.isPending}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm disabled:bg-gray-400 disabled:cursor-not-allowed"
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
              'Generate Lab'
            )}
          </button>
        </div>

        {createLab.isError && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">
              Error: {(createLab.error as Error).message}
            </p>
          </div>
        )}
      </form>

      {/* Examples */}
      <div className="mt-12">
        <h3 className="text-sm font-medium text-gray-700 mb-3">
          Example prompts:
        </h3>
        <div className="space-y-2">
          {examples.map((example, index) => (
            <button
              key={index}
              onClick={() => setPrompt(example)}
              className="block w-full text-left px-4 py-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
