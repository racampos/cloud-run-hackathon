/**
 * Planner stage tab content
 */

'use client';

import ConversationPanel from '@/components/LabWizard/ConversationPanel';
import type { Conversation, ExerciseSpec } from '@/lib/types';

interface PlannerTabProps {
  conversation: Conversation;
  exerciseSpec?: ExerciseSpec | null;
  onSendMessage: (content: string) => void;
  isLoading?: boolean;
}

export function PlannerTab({
  conversation,
  exerciseSpec,
  onSendMessage,
  isLoading,
}: PlannerTabProps) {
  return (
    <div className="space-y-6">
      {/* Conversation Panel */}
      <div className="h-[600px]">
        <ConversationPanel
          conversation={conversation}
          onSendMessage={onSendMessage}
          isLoading={isLoading}
        />
      </div>

      {/* Exercise Spec Output */}
      {exerciseSpec && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Exercise Specification</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <span className="text-sm text-gray-600">Level:</span>
              <span className="ml-2 font-medium text-gray-900">{exerciseSpec.level}</span>
            </div>
            <div>
              <span className="text-sm text-gray-600">Time:</span>
              <span className="ml-2 font-medium text-gray-900">
                {exerciseSpec.constraints.time_minutes} min
              </span>
            </div>
            <div>
              <span className="text-sm text-gray-600">Devices:</span>
              <span className="ml-2 font-medium text-gray-900">
                {exerciseSpec.constraints.devices}
              </span>
            </div>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">Learning Objectives:</h4>
            <ul className="list-disc list-inside space-y-1">
              {exerciseSpec.objectives.map((obj, i) => (
                <li key={i} className="text-sm text-gray-800">
                  {obj}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
