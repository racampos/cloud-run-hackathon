/**
 * Home page - Lab Library
 */

import Link from 'next/link';
import { LabList } from '@/components/LabLibrary/LabList';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">NetGenius Instructor Copilot</h1>
              <p className="mt-1 text-sm text-gray-600">
                AI-Powered Networking Lab Generator
              </p>
            </div>
            <Link
              href="/create"
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm"
            >
              Create New Lab
            </Link>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">
            Lab Library
          </h2>
          <p className="text-gray-600">
            View and manage your generated networking labs
          </p>
        </div>

        <LabList />
      </main>
    </div>
  );
}
