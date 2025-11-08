/**
 * Lab detail page with progress tracking and review interface
 */

'use client';

import Link from 'next/link';
import { use } from 'react';
import { useLabPolling, useSendMessage } from '@/lib/hooks';
import { ProgressTracker } from '@/components/LabWizard/ProgressTracker';
import ConversationPanel from '@/components/LabWizard/ConversationPanel';
import { TopologyPanel } from '@/components/LabReview/TopologyPanel';
import { ConfigsPanel } from '@/components/LabReview/ConfigsPanel';
import { GuidePanel } from '@/components/LabReview/GuidePanel';
import { ValidationPanel } from '@/components/LabReview/ValidationPanel';
import { StatusBadge } from '@/components/shared/StatusBadge';

export default function LabDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const { data: lab, isLoading, error } = useLabPolling(resolvedParams.id);
  const sendMessage = useSendMessage();

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

  const isComplete = lab.status === 'completed' || lab.status === 'failed';

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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Progress tracker */}
          <div className="lg:col-span-1">
            <ProgressTracker
              status={lab.status}
              currentAgent={lab.current_agent}
            />

            {/* Exercise spec summary */}
            {exercise_spec && (
              <div className="mt-6 bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Exercise Spec
                </h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-600">Level:</span>
                    <span className="ml-2 font-medium text-gray-900">{exercise_spec.level}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Time:</span>
                    <span className="ml-2 font-medium text-gray-900">
                      {exercise_spec.constraints.time_minutes} min
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Devices:</span>
                    <span className="ml-2 font-medium text-gray-900">
                      {exercise_spec.constraints.devices}
                    </span>
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <span className="text-gray-600 block mb-2">Objectives:</span>
                    <ul className="list-disc list-inside space-y-1">
                      {exercise_spec.objectives.map((obj, i) => (
                        <li key={i} className="text-gray-800">
                          {obj}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right column - Conversation or Review panels */}
          <div className="lg:col-span-2 space-y-6">
            {/* Show conversation panel during Planner phase */}
            {(lab.status === 'planner_running' || lab.status === 'awaiting_user_input') && (
              <div className="h-[600px]">
                <ConversationPanel
                  conversation={lab.conversation}
                  onSendMessage={handleSendMessage}
                  isLoading={sendMessage.isPending}
                />
              </div>
            )}

            {/* Show message while other agents are in progress */}
            {!isComplete &&
              lab.status !== 'planner_running' &&
              lab.status !== 'awaiting_user_input' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    Lab generation in progress. Results will appear below as agents complete their work.
                  </p>
                </div>
              )}

            {/* Topology panel */}
            {design_output?.topology_yaml && (
              <TopologyPanel yaml={design_output.topology_yaml} />
            )}

            {/* Configs panel */}
            {design_output?.initial_configs && (
              <ConfigsPanel
                initialConfigs={design_output.initial_configs}
                targetConfigs={design_output.target_configs}
                platforms={design_output.platforms}
              />
            )}

            {/* Lab guide panel */}
            {draft_lab_guide_markdown && (
              <GuidePanel
                markdown={draft_lab_guide_markdown}
                estimatedTime={draft_lab_guide?.estimated_time_minutes}
              />
            )}

            {/* Validation panel */}
            {validation_result && <ValidationPanel result={validation_result} />}
          </div>
        </div>
      </main>
    </div>
  );
}
