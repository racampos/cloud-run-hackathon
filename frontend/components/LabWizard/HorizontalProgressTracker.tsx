/**
 * Horizontal progress tracker showing pipeline stages
 */

'use client';

import type { LabStatus } from '@/lib/types';

interface HorizontalProgressTrackerProps {
  status: LabStatus;
  currentAgent?: string | null;
}

const stages = [
  { key: 'planner', label: 'Planner' },
  { key: 'designer', label: 'Designer' },
  { key: 'author', label: 'Author' },
  { key: 'validator', label: 'Validator' },
];

export function HorizontalProgressTracker({ status, currentAgent }: HorizontalProgressTrackerProps) {
  const getStageStatus = (stageKey: string): 'pending' | 'running' | 'complete' => {
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
      <div className="flex items-center justify-between">
        {stages.map((stage, index) => {
          const stageStatus = getStageStatus(stage.key);
          const isLast = index === stages.length - 1;

          return (
            <div key={stage.key} className="flex items-center flex-1">
              {/* Stage indicator */}
              <div className="flex flex-col items-center">
                <div
                  className={`flex items-center justify-center w-12 h-12 rounded-full border-2 ${
                    stageStatus === 'complete'
                      ? 'bg-green-100 border-green-500'
                      : stageStatus === 'running'
                      ? 'bg-yellow-100 border-yellow-500 animate-pulse'
                      : 'bg-gray-100 border-gray-300'
                  }`}
                >
                  {stageStatus === 'complete' ? (
                    <svg
                      className="w-6 h-6 text-green-600"
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
                      className="animate-spin h-6 w-6 text-yellow-600"
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
                    <div className="w-4 h-4 bg-gray-400 rounded-full"></div>
                  )}
                </div>
                <span
                  className={`mt-2 text-sm font-medium ${
                    stageStatus === 'running'
                      ? 'text-yellow-900'
                      : stageStatus === 'complete'
                      ? 'text-green-900'
                      : 'text-gray-600'
                  }`}
                >
                  {stage.label}
                </span>
              </div>

              {/* Connecting line */}
              {!isLast && (
                <div className="flex-1 h-0.5 mx-4 bg-gray-300">
                  <div
                    className={`h-full transition-all ${
                      stageStatus === 'complete' ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                    style={{ width: stageStatus === 'complete' ? '100%' : '0%' }}
                  ></div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
