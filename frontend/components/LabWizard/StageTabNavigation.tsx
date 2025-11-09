/**
 * Tab navigation for lab stages
 */

'use client';

import type { LabStatus } from '@/lib/types';

export type StageTab = 'planner' | 'designer' | 'author' | 'validator';

interface StageTabNavigationProps {
  activeTab: StageTab;
  onTabChange: (tab: StageTab) => void;
  status: LabStatus;
}

const tabs: Array<{ key: StageTab; label: string }> = [
  { key: 'planner', label: 'Planner' },
  { key: 'designer', label: 'Designer' },
  { key: 'author', label: 'Author' },
  { key: 'validator', label: 'Validator' },
];

export function StageTabNavigation({ activeTab, onTabChange, status }: StageTabNavigationProps) {
  const isTabEnabled = (tabKey: StageTab): boolean => {
    // Planner is always enabled
    if (tabKey === 'planner') return true;

    // Designer enabled when designer_complete or later
    if (tabKey === 'designer') {
      return (
        status === 'designer_complete' ||
        status === 'author_running' ||
        status === 'author_complete' ||
        status === 'validator_running' ||
        status === 'validator_complete' ||
        status === 'completed' ||
        status === 'failed'
      );
    }

    // Author enabled when author_complete or later
    if (tabKey === 'author') {
      return (
        status === 'author_complete' ||
        status === 'validator_running' ||
        status === 'validator_complete' ||
        status === 'completed' ||
        status === 'failed'
      );
    }

    // Validator enabled when validator_complete or completed
    if (tabKey === 'validator') {
      return status === 'validator_complete' || status === 'completed' || status === 'failed';
    }

    return false;
  };

  const getTabStatus = (tabKey: StageTab): 'complete' | 'running' | 'pending' => {
    if (status === 'completed' || status === 'failed') return 'complete';

    // Check if this specific stage is complete
    if (status === `${tabKey}_complete`) {
      return 'complete';
    }

    // Check if currently running
    if (status === `${tabKey}_running`) {
      return 'running';
    }

    // Parse the current status to determine if a later stage is active
    const statusMatch = status.match(/^(planner|designer|author|validator)_(running|complete)$/);
    if (statusMatch) {
      const statusStageKey = statusMatch[1];
      const statusPhase = statusMatch[2];
      const tabIndex = tabs.findIndex((t) => t.key === tabKey);
      const statusIndex = tabs.findIndex((t) => t.key === statusStageKey);

      // If the previous stage just completed and this is the next stage, show as running
      if (statusPhase === 'complete' && statusIndex === tabIndex - 1) {
        return 'running';
      }

      // If status is for a later stage, this stage must be complete
      if (statusIndex > tabIndex) {
        return 'complete';
      }
    }

    return 'pending';
  };

  return (
    <div className="bg-white border-b border-gray-200">
      <nav className="flex items-center px-6 py-2" aria-label="Tabs">
        {tabs.map((tab, index) => {
          const enabled = isTabEnabled(tab.key);
          const isActive = activeTab === tab.key;
          const tabStatus = getTabStatus(tab.key);
          const isLast = index === tabs.length - 1;

          return (
            <div key={tab.key} className="flex items-center">
              <button
                onClick={() => enabled && onTabChange(tab.key)}
                disabled={!enabled}
                className={`
                  flex items-center gap-3 px-6 py-4 text-base font-medium border-b-4 transition-colors
                  ${
                    isActive
                      ? 'border-blue-500 text-blue-600'
                      : enabled
                      ? 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                      : 'border-transparent text-gray-400 cursor-not-allowed'
                  }
                `}
              >
                {/* Status indicator circle */}
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${
                    tabStatus === 'complete'
                      ? 'bg-green-100 border-green-500'
                      : tabStatus === 'running'
                      ? 'bg-yellow-100 border-yellow-500 animate-pulse'
                      : 'bg-gray-100 border-gray-300'
                  }`}
                >
                  {tabStatus === 'complete' ? (
                    <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : tabStatus === 'running' ? (
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
                {tab.label}
              </button>

              {/* Connecting line */}
              {!isLast && (
                <div className="w-12 h-1 mx-2">
                  <div
                    className={`h-full transition-colors ${
                      tabStatus === 'complete' ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                  ></div>
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </div>
  );
}
