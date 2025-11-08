/**
 * Individual lab card component
 */

'use client';

import Link from 'next/link';
import { StatusBadge } from '@/components/shared/StatusBadge';
import type { LabListItem } from '@/lib/types';

interface LabCardProps {
  lab: LabListItem;
}

export function LabCard({ lab }: LabCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Link href={`/labs/${lab.lab_id}`}>
      <div className="block p-6 bg-white border border-gray-200 rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer">
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-lg font-semibold text-gray-900 truncate flex-1 mr-3">
            {lab.title || 'Untitled Lab'}
          </h3>
          <StatusBadge status={lab.status} />
        </div>

        <div className="space-y-2">
          <p className="text-sm text-gray-600">
            Lab ID: <span className="font-mono text-xs">{lab.lab_id}</span>
          </p>
          <p className="text-xs text-gray-500">
            Created: {formatDate(lab.created_at)}
          </p>
        </div>

        <div className="mt-4 pt-4 border-t border-gray-100">
          <span className="text-sm text-blue-600 hover:text-blue-800 font-medium">
            View Details →
          </span>
        </div>
      </div>
    </Link>
  );
}
