/**
 * Lab detail page with 2-panel layout (NEW ARCHITECTURE)
 * Left: Content tabs (Lab Design + Lab Guide)
 * Right: Always-on Planner chat
 */

'use client';

import Link from 'next/link';
import { use, useState, useEffect } from 'react';
import { useLabPolling, useChatWithPlanner } from '@/lib/hooks';
import { PlannerChatPanel } from '@/components/Planner/PlannerChatPanel';
import { ContentTabNavigation, type ContentTab } from '@/components/Content/ContentTabNavigation';
import { LabDesignTab } from '@/components/Content/LabDesignTab';
import { LabGuideTab } from '@/components/Content/LabGuideTab';
import { StatusBadge } from '@/components/shared/StatusBadge';

export default function LabDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const { data: lab, isLoading, error } = useLabPolling(resolvedParams.id);
  const chatWithPlanner = useChatWithPlanner();

  const [activeTab, setActiveTab] = useState<ContentTab>('design');
  const [lastSeenUpdateTimestamp, setLastSeenUpdateTimestamp] = useState<string | null>(null);

  // Auto-switch tabs when content becomes available
  useEffect(() => {
    if (lab) {
      // Switch to design tab when design output is available
      if (lab.progress.design_output && !lab.progress.draft_lab_guide_markdown) {
        setActiveTab('design');
      }
      // Switch to guide tab when lab guide is available
      else if (lab.progress.draft_lab_guide_markdown) {
        setActiveTab('guide');
      }
    }
  }, [lab?.progress.design_output, lab?.progress.draft_lab_guide_markdown]);

  // Handle latest_planner_update injection
  useEffect(() => {
    if (lab?.latest_planner_update) {
      const updateTimestamp = lab.latest_planner_update.timestamp;

      // Only inject if this is a new update
      if (updateTimestamp !== lastSeenUpdateTimestamp) {
        // Add the progress message to the conversation
        const progressMessage = {
          role: 'assistant' as const,
          content: lab.latest_planner_update.message,
          timestamp: updateTimestamp,
        };

        // The message will be shown through the conversation
        // We just need to track that we've seen it
        setLastSeenUpdateTimestamp(updateTimestamp);
      }
    }
  }, [lab?.latest_planner_update, lastSeenUpdateTimestamp]);

  const handleSendMessage = (message: string) => {
    chatWithPlanner.mutate({ labId: resolvedParams.id, message });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading lab...</p>
        </div>
      </div>
    );
  }

  if (error || !lab) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">Error: {error?.message || 'Lab not found'}</p>
          <Link
            href="/"
            className="mt-4 inline-block text-blue-600 hover:text-blue-800"
          >
            ← Back to Library
          </Link>
        </div>
      </div>
    );
  }

  const { exercise_spec, design_output, draft_lab_guide, draft_lab_guide_markdown, validation_result } =
    lab.progress;

  const hasDesign = !!design_output;
  const hasGuide = !!draft_lab_guide_markdown;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-gray-600 hover:text-gray-900 transition-colors"
              >
                ← Back to Library
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {exercise_spec?.title || 'Lab Details'}
                </h1>
                <p className="mt-1 text-sm text-gray-600">
                  Lab ID: {lab.lab_id}
                </p>
              </div>
            </div>
            <StatusBadge status={lab.status} className="text-base px-4 py-2" />
          </div>
        </div>
      </header>

      {/* Main content - 2 panel layout */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel - Content Area (2/3) */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Content Tab Navigation */}
          <ContentTabNavigation
            activeTab={activeTab}
            onTabChange={setActiveTab}
            status={lab.status}
            hasDesign={hasDesign}
            hasGuide={hasGuide}
          />

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
            {activeTab === 'design' && (
              <>
                {design_output ? (
                  <LabDesignTab designOutput={design_output} />
                ) : (
                  <div className="bg-white border border-gray-200 rounded-lg p-12">
                    <div className="text-center">
                      <div className="text-gray-400 mb-4">
                        <svg
                          className="w-16 h-16 mx-auto animate-spin"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          />
                        </svg>
                      </div>
                      <p className="text-gray-600 text-lg">Designing network topology and configurations...</p>
                      <p className="text-sm text-gray-500 mt-2">
                        The Planner will update you on progress →
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}

            {activeTab === 'guide' && (
              <>
                {draft_lab_guide_markdown ? (
                  <LabGuideTab
                    markdown={draft_lab_guide_markdown}
                    estimatedTime={draft_lab_guide?.estimated_time_minutes}
                    validationResult={validation_result}
                  />
                ) : (
                  <div className="bg-white border border-gray-200 rounded-lg p-12">
                    <div className="text-center">
                      <div className="text-gray-400 mb-4">
                        <svg
                          className="w-16 h-16 mx-auto animate-spin"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          />
                        </svg>
                      </div>
                      <p className="text-gray-600 text-lg">Writing lab guide...</p>
                      <p className="text-sm text-gray-500 mt-2">
                        The Planner will update you on progress →
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Right Panel - Planner Chat (1/3) */}
        <div className="w-1/3 flex flex-col border-l border-gray-200 bg-white">
          <PlannerChatPanel
            conversation={lab.conversation}
            exerciseSpec={exercise_spec}
            status={lab.status}
            onSendMessage={handleSendMessage}
            isLoading={chatWithPlanner.isPending}
          />
        </div>
      </main>
    </div>
  );
}
