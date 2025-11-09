/**
 * Simplified tab navigation for lab content (Lab Design + Lab Guide)
 */

'use client';

import type { LabStatus } from '@/lib/types';

export type ContentTab = 'design' | 'guide';

interface ContentTabNavigationProps {
  activeTab: ContentTab;
  onTabChange: (tab: ContentTab) => void;
  status: LabStatus;
  hasDesign: boolean;
  hasGuide: boolean;
}

const tabs: Array<{ key: ContentTab; label: string }> = [
  { key: 'design', label: 'Lab Design' },
  { key: 'guide', label: 'Lab Guide' },
];

export function ContentTabNavigation({
  activeTab,
  onTabChange,
  status,
  hasDesign,
  hasGuide,
}: ContentTabNavigationProps) {
  const isTabEnabled = (tabKey: ContentTab): boolean => {
    if (tabKey === 'design') {
      return hasDesign;
    }
    if (tabKey === 'guide') {
      return hasGuide;
    }
    return false;
  };

  return (
    <div className="bg-white border-b border-gray-200">
      <nav className="flex space-x-1 px-6" aria-label="Content Tabs">
        {tabs.map((tab) => {
          const enabled = isTabEnabled(tab.key);
          const isActive = activeTab === tab.key;

          return (
            <button
              key={tab.key}
              onClick={() => enabled && onTabChange(tab.key)}
              disabled={!enabled}
              className={`
                px-6 py-3 text-base font-medium border-b-4 transition-colors
                ${
                  isActive
                    ? 'border-blue-500 text-blue-600'
                    : enabled
                    ? 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                    : 'border-transparent text-gray-400 cursor-not-allowed'
                }
              `}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
