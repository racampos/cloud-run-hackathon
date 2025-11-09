/**
 * Always-on Planner chat panel with embedded progress indicator
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import type { Conversation, ExerciseSpec, LabStatus } from '@/lib/types';

interface PlannerChatPanelProps {
  conversation: Conversation;
  exerciseSpec?: ExerciseSpec | null;
  status: LabStatus;
  onSendMessage: (content: string) => void;
  isLoading?: boolean;
}

interface ProgressStage {
  key: string;
  label: string;
  status: 'pending' | 'running' | 'complete';
}

function getProgressStages(status: LabStatus): ProgressStage[] {
  const stages: ProgressStage[] = [
    { key: 'planner', label: 'Requirements gathered', status: 'pending' },
    { key: 'designer', label: 'Network designed', status: 'pending' },
    { key: 'author', label: 'Lab guide written', status: 'pending' },
    { key: 'validator', label: 'Validation complete', status: 'pending' },
  ];

  // Determine status for each stage
  if (status === 'completed' || status === 'failed') {
    return stages.map((s) => ({ ...s, status: 'complete' }));
  }

  if (status === 'planner_running') {
    stages[0].status = 'running';
  } else if (status === 'planner_complete' || status.includes('designer') || status.includes('author') || status.includes('validator')) {
    stages[0].status = 'complete';
  }

  if (status === 'designer_running') {
    stages[1].status = 'running';
  } else if (status.includes('author') || status.includes('validator') || status === 'completed') {
    stages[1].status = 'complete';
  }

  if (status === 'author_running') {
    stages[2].status = 'running';
  } else if (status === 'author_complete' || status.includes('validator') || status === 'completed') {
    stages[2].status = 'complete';
  }

  if (status === 'validator_running') {
    stages[3].status = 'running';
  } else if (status === 'validator_complete' || status === 'completed') {
    stages[3].status = 'complete';
  }

  return stages;
}

export function PlannerChatPanel({
  conversation,
  exerciseSpec,
  status,
  onSendMessage,
  isLoading,
}: PlannerChatPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const progressStages = getProgressStages(status);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation.messages, exerciseSpec]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  // Check if we should show the progress indicator
  const showProgress = status !== 'pending' && status !== 'planner_running';

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h3 className="text-lg font-semibold text-gray-900">Planner Assistant</h3>
        <p className="text-xs text-gray-600 mt-1">Always here to help</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {conversation.messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-4 py-3 ${
                message.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100'
              }`}
            >
              <div
                className={`text-xs font-medium mb-1 ${
                  message.role === 'user' ? 'text-blue-100' : 'text-gray-600'
                }`}
              >
                {message.role === 'user' ? 'You' : 'Planner'}
              </div>
              <div
                className={`whitespace-pre-wrap text-sm ${
                  message.role === 'user' ? 'text-white' : 'text-gray-900'
                }`}
              >
                {message.content}
              </div>
              <div
                className={`text-xs mt-1 ${
                  message.role === 'user' ? 'text-blue-200' : 'text-gray-500'
                }`}
              >
                {new Date(message.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {/* Exercise Spec Message (if available) */}
        {exerciseSpec && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-lg px-4 py-3 bg-green-50 border border-green-200">
              <div className="text-xs font-medium mb-2 text-green-800">
                ✓ Exercise Specification Ready
              </div>
              <div className="space-y-2 text-sm text-gray-900">
                {exerciseSpec.title && (
                  <div>
                    <span className="font-semibold">Title:</span> {exerciseSpec.title}
                  </div>
                )}
                {exerciseSpec.level && (
                  <div>
                    <span className="font-semibold">Level:</span> {exerciseSpec.level}
                  </div>
                )}
                {exerciseSpec.constraints?.time_minutes && (
                  <div>
                    <span className="font-semibold">Time:</span>{' '}
                    {exerciseSpec.constraints.time_minutes} minutes
                  </div>
                )}
                {exerciseSpec.constraints?.devices && (
                  <div>
                    <span className="font-semibold">Devices:</span>{' '}
                    {exerciseSpec.constraints.devices}
                  </div>
                )}
                {exerciseSpec.objectives && exerciseSpec.objectives.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-green-200">
                    <div className="font-semibold mb-1">Objectives:</div>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {exerciseSpec.objectives.map((obj, i) => (
                        <li key={i}>{obj}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Progress Indicator (embedded in chat) */}
        {showProgress && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-lg px-4 py-3 bg-blue-50 border border-blue-200">
              <div className="text-xs font-medium mb-3 text-blue-800">Generation Progress</div>
              <div className="space-y-2">
                {progressStages.map((stage) => (
                  <div key={stage.key} className="flex items-center gap-2">
                    <div
                      className={`flex items-center justify-center w-5 h-5 rounded-full border ${
                        stage.status === 'complete'
                          ? 'bg-green-100 border-green-500'
                          : stage.status === 'running'
                          ? 'bg-yellow-100 border-yellow-500'
                          : 'bg-gray-100 border-gray-300'
                      }`}
                    >
                      {stage.status === 'complete' ? (
                        <svg
                          className="w-3 h-3 text-green-600"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      ) : stage.status === 'running' ? (
                        <svg
                          className="animate-spin h-3 w-3 text-yellow-600"
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
                        <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                      )}
                    </div>
                    <span
                      className={`text-sm ${
                        stage.status === 'complete'
                          ? 'text-green-900 font-medium'
                          : stage.status === 'running'
                          ? 'text-yellow-900 font-medium'
                          : 'text-gray-500'
                      }`}
                    >
                      {stage.label}
                      {stage.status === 'running' && '...'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-3 max-w-[85%]">
              <div className="text-xs font-medium mb-1 text-gray-500">Planner</div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form - Always enabled */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <form onSubmit={handleSubmit} className="flex space-x-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask the Planner anything..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-900 placeholder:text-gray-400"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
