/**
 * Lab library list component
 */

'use client';

import { useState } from 'react';
import { useLabList } from '@/lib/hooks';
import { LabCard } from './LabCard';
import type { LabStatus } from '@/lib/types';

export function LabList() {
  const { data: labs, isLoading, error } = useLabList();
  const [filter, setFilter] = useState<LabStatus | 'all'>('all');

  const filteredLabs = labs?.filter((lab) => {
    if (filter === 'all') return true;
    return lab.status === filter;
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error loading labs: {error.message}</p>
      </div>
    );
  }

  return (
    <div>
      {/* Filter tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        {[
          { value: 'all' as const, label: 'All' },
          { value: 'completed' as const, label: 'Completed' },
          { value: 'failed' as const, label: 'Failed' },
          { value: 'pending' as const, label: 'In Progress' },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filter === tab.value
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Lab grid */}
      {!filteredLabs || filteredLabs.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No labs found</p>
          <p className="text-sm">Create your first lab to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredLabs.map((lab) => (
            <LabCard key={lab.lab_id} lab={lab} />
          ))}
        </div>
      )}
    </div>
  );
}
