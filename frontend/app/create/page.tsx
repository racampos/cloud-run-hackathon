/**
 * Lab creation page
 */

import Link from 'next/link';
import { PromptInput } from '@/components/LabWizard/PromptInput';

export default function CreateLabPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              ← Back to Library
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Create New Lab
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Describe your lab requirements and let AI generate it for you
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <PromptInput />
      </main>
    </div>
  );
}
