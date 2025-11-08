/**
 * Status badge component for displaying lab/agent status
 */

import type { LabStatus } from '@/lib/types';

interface StatusBadgeProps {
  status: LabStatus;
  className?: string;
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const getStatusStyle = () => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'pending':
        return 'bg-gray-100 text-gray-800 border-gray-300';
      case 'planner_running':
      case 'designer_running':
      case 'author_running':
      case 'validator_running':
      case 'rca_running':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300 animate-pulse';
      case 'planner_complete':
      case 'designer_complete':
      case 'author_complete':
      case 'validator_complete':
      case 'rca_complete':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getStatusLabel = () => {
    return status
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusStyle()} ${className}`}
    >
      {getStatusLabel()}
    </span>
  );
}
