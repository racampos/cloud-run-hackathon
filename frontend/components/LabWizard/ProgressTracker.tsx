/**
 * Progress tracker showing pipeline stages
 */

'use client';

import { StatusBadge } from '@/components/shared/StatusBadge';
import type { LabStatus } from '@/lib/types';

interface ProgressTrackerProps {
  status: LabStatus;
  currentAgent?: string | null;
}

const stages = [
  { key: 'planner', label: 'Planner', description: 'Extracting learning objectives' },
  { key: 'designer', label: 'Designer', description: 'Creating topology & configs' },
  { key: 'author', label: 'Author', description: 'Writing lab guide' },
  { key: 'validator', label: 'Validator', description: 'Running headless simulation' },
];

export function ProgressTracker({ status, currentAgent }: ProgressTrackerProps) {
  const getStageStatus = (stageKey: string): 'pending' | 'running' | 'complete' | 'current' => {
    if (status === 'completed' || status === 'failed') return 'complete';

    // Check if this specific stage is complete
    if (status === `${stageKey}_complete`) {
      return 'complete';
    }

    // Check if currently running
    if (currentAgent === stageKey || status === `${stageKey}_running`) {
      return 'running';
    }

    // Get stage indices for comparison
    const stageIndex = stages.findIndex((s) => s.key === stageKey);

    // Parse the current status to extract stage key
    const statusMatch = status.match(/^(planner|designer|author|validator|rca)_(running|complete)$/);
    if (statusMatch) {
      const statusStageKey = statusMatch[1];
      const statusPhase = statusMatch[2]; // 'running' or 'complete'
      const statusStageIndex = stages.findIndex((s) => s.key === statusStageKey);

      // If the previous stage just completed and this is the next stage, show as running
      if (statusPhase === 'complete' && statusStageIndex === stageIndex - 1) {
        return 'running';
      }

      // If status is for a later stage, this stage must be complete
      if (statusStageIndex > stageIndex) {
        return 'complete';
      }
    }

    // Check if stage is before current agent
    const currentIndex = stages.findIndex((s) => s.key === currentAgent);
    if (currentIndex !== -1 && stageIndex < currentIndex) {
      return 'complete';
    }

    return 'pending';
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        Pipeline Progress
      </h2>

      <div className="space-y-4">
        {stages.map((stage, index) => {
          const stageStatus = getStageStatus(stage.key);
          const isLast = index === stages.length - 1;

          return (
            <div key={stage.key} className="relative">
              <div className="flex items-start gap-4">
                {/* Status indicator */}
                <div className="flex flex-col items-center">
                  <div
                    className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                      stageStatus === 'complete'
                        ? 'bg-green-100 border-green-500'
                        : stageStatus === 'running'
                        ? 'bg-yellow-100 border-yellow-500 animate-pulse'
                        : 'bg-gray-100 border-gray-300'
                    }`}
                  >
                    {stageStatus === 'complete' ? (
                      <svg
                        className="w-5 h-5 text-green-600"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : stageStatus === 'running' ? (
                      <svg
                        className="animate-spin h-5 w-5 text-yellow-600"
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
                    ) : (
                      <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                    )}
                  </div>
                  {!isLast && (
                    <div
                      className={`w-0.5 h-12 mt-2 ${
                        stageStatus === 'complete' ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                    ></div>
                  )}
                </div>

                {/* Stage info */}
                <div className="flex-1 pt-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3
                      className={`font-medium ${
                        stageStatus === 'running'
                          ? 'text-yellow-900'
                          : stageStatus === 'complete'
                          ? 'text-green-900'
                          : 'text-gray-600'
                      }`}
                    >
                      {stage.label}
                    </h3>
                    {stageStatus === 'running' && (
                      <span className="text-xs text-yellow-700 font-medium">
                        In Progress...
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">{stage.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Overall status */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Overall Status:</span>
          <StatusBadge status={status} />
        </div>
      </div>
    </div>
  );
}
