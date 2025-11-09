/**
 * Lab detail page with tabbed stage interface
 */

'use client';

import Link from 'next/link';
import { use, useState, useEffect } from 'react';
import { useLabPolling, useSendMessage } from '@/lib/hooks';
import { StageTabNavigation, type StageTab } from '@/components/LabWizard/StageTabNavigation';
import { PlannerTab } from '@/components/LabStages/PlannerTab';
import { DesignerTab } from '@/components/LabStages/DesignerTab';
import { AuthorTab } from '@/components/LabStages/AuthorTab';
import { ValidatorTab } from '@/components/LabStages/ValidatorTab';
import { StatusBadge } from '@/components/shared/StatusBadge';
import type { LabStatus } from '@/lib/types';

// Helper to determine which tab should be active based on status
function getDefaultActiveTab(status: LabStatus): StageTab {
  if (status === 'completed' || status === 'failed' || status === 'validator_complete') {
    return 'validator';
  }
  if (status === 'validator_running' || status === 'author_complete') {
    return 'author';
  }
  if (status === 'author_running' || status === 'designer_complete') {
    return 'designer';
  }
  return 'planner';
}

export default function LabDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const { data: lab, isLoading, error } = useLabPolling(resolvedParams.id);
  const sendMessage = useSendMessage();

  const [activeTab, setActiveTab] = useState<StageTab>('planner');

  // Auto-switch to newly enabled tabs
  useEffect(() => {
    if (lab) {
      const newDefaultTab = getDefaultActiveTab(lab.status);
      setActiveTab(newDefaultTab);
    }
  }, [lab?.status]);

  const handleSendMessage = (content: string) => {
    sendMessage.mutate({ labId: resolvedParams.id, content });
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
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

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          {/* Tab Navigation */}
          <StageTabNavigation
            activeTab={activeTab}
            onTabChange={setActiveTab}
            status={lab.status}
          />

          {/* Tab Content */}
          <div className="min-h-[600px]">
            {activeTab === 'planner' && (
              <PlannerTab
                conversation={lab.conversation}
                exerciseSpec={exercise_spec}
                onSendMessage={handleSendMessage}
                isLoading={sendMessage.isPending}
              />
            )}

            {activeTab === 'designer' && design_output && (
              <DesignerTab designOutput={design_output} />
            )}

            {activeTab === 'designer' && !design_output && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <div className="text-center py-12">
                  <div className="text-gray-400 mb-2">
                    <svg
                      className="w-12 h-12 mx-auto animate-spin"
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
                  <p className="text-gray-600">Designing network topology and configurations...</p>
                </div>
              </div>
            )}

            {activeTab === 'author' && draft_lab_guide_markdown && (
              <AuthorTab
                markdown={draft_lab_guide_markdown}
                estimatedTime={draft_lab_guide?.estimated_time_minutes}
              />
            )}

            {activeTab === 'author' && !draft_lab_guide_markdown && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <div className="text-center py-12">
                  <div className="text-gray-400 mb-2">
                    <svg
                      className="w-12 h-12 mx-auto animate-spin"
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
                  <p className="text-gray-600">Writing lab guide...</p>
                </div>
              </div>
            )}

            {activeTab === 'validator' && (
              <ValidatorTab validationResult={validation_result} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
