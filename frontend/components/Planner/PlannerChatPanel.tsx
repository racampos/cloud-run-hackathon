/**
 * Always-on Planner chat panel with embedded progress indicator
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Conversation, ExerciseSpec, LabStatus } from '@/lib/types';

interface PlannerChatPanelProps {
  conversation: Conversation;
  exerciseSpec?: ExerciseSpec | null;
  status: LabStatus;
  onSendMessage: (content: string) => void;
  isLoading?: boolean;
  progressUpdates?: Array<{
    timestamp: string;
    message: string;
  }>;
}

export function PlannerChatPanel({
  conversation,
  exerciseSpec,
  status,
  onSendMessage,
  isLoading,
  progressUpdates = [],
}: PlannerChatPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Track which messages are progress updates by timestamp
  const progressUpdateTimestamps = new Set<string>();
  progressUpdates.forEach((update) => {
    progressUpdateTimestamps.add(update.timestamp);
  });

  // Merge progress updates into message stream
  const allMessages = [...conversation.messages];

  // Add all progress updates that aren't already in the conversation
  progressUpdates.forEach((update) => {
    const isAlreadyInConversation = conversation.messages.some(
      (msg) => msg.timestamp === update.timestamp
    );

    if (!isAlreadyInConversation) {
      allMessages.push({
        role: 'assistant' as const,
        content: update.message,
        timestamp: update.timestamp,
      });
    }
  });

  // Sort by timestamp to maintain chronological order
  // Note: This may have issues with the initial message if backend sends inconsistent timezones
  allMessages.sort((a, b) =>
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation.messages, exerciseSpec, progressUpdates]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  // Check if message is exercise spec JSON
  const isExerciseSpecMessage = (content: string) => {
    return content.includes('"title":') && content.includes('"objectives":');
  };

  // Check if message is a progress update
  const isProgressMessage = (content: string) => {
    return content.includes('✓') || content.includes('⏳') ||
           content.toLowerCase().includes('designing') ||
           content.toLowerCase().includes('writing') ||
           content.toLowerCase().includes('validating');
  };

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h3 className="text-lg font-semibold text-gray-900">Planner Assistant</h3>
        <p className="text-xs text-gray-600 mt-1">Always here to help</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {allMessages.map((message, index) => {
          // Render exercise spec as formatted bubble - but only if we have the actual spec data
          if (message.role === 'assistant' && isExerciseSpecMessage(message.content)) {
            // Try to parse the spec from message content first
            let spec = null;
            try {
              spec = JSON.parse(message.content);
            } catch {
              // If parsing fails, use the prop if available
              spec = exerciseSpec;
            }

            // Only render detailed bubble if we have spec data
            if (spec && spec.title) {
              return (
                <div key={index} className="flex justify-start">
                  <div className="max-w-[85%] rounded-lg px-4 py-3 bg-green-50 border border-green-200">
                    <div className="text-xs font-medium mb-2 text-green-800">
                      ✓ Exercise Specification Ready
                    </div>
                    <div className="space-y-2 text-sm text-gray-900">
                      {spec.title && (
                        <div>
                          <span className="font-semibold">Title:</span> {spec.title}
                        </div>
                      )}
                      {spec.level && (
                        <div>
                          <span className="font-semibold">Level:</span> {spec.level}
                        </div>
                      )}
                      {spec.constraints?.time_minutes && (
                        <div>
                          <span className="font-semibold">Time:</span>{' '}
                          {spec.constraints.time_minutes} minutes
                        </div>
                      )}
                      {spec.constraints?.devices && (
                        <div>
                          <span className="font-semibold">Devices:</span>{' '}
                          {spec.constraints.devices}
                        </div>
                      )}
                      {spec.objectives && spec.objectives.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-green-200">
                          <div className="font-semibold mb-1">Objectives:</div>
                          <ul className="list-disc list-inside space-y-1 text-sm">
                            {spec.objectives.map((obj: string, i: number) => (
                              <li key={i}>{obj}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                    <div className="text-xs mt-2 text-green-600">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              );
            }

            // If no spec data, skip this message (it will be filtered out)
            return null;
          }

          // Render progress updates as blue bubbles (check by timestamp first, then by content)
          const isProgressUpdate = progressUpdateTimestamps.has(message.timestamp) ||
                                  (message.role === 'assistant' && isProgressMessage(message.content));

          if (isProgressUpdate) {
            return (
              <div key={index} className="flex justify-start">
                <div className="max-w-[85%] rounded-lg px-4 py-3 bg-blue-50 border border-blue-200">
                  <div className="text-xs font-medium mb-1 text-blue-800">Progress Update</div>
                  <div className="text-base font-medium text-gray-900">
                    {message.content}
                  </div>
                  <div className="text-xs mt-1 text-blue-600">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            );
          }

          // Render regular messages
          return (
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
                  className={`text-sm ${
                    message.role === 'user' ? 'text-white whitespace-pre-wrap' : 'text-gray-900'
                  }`}
                >
                  {message.role === 'user' ? (
                    message.content
                  ) : (
                    <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-900 prose-strong:text-gray-900 prose-code:text-gray-900 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-ul:text-gray-900 prose-li:text-gray-900">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}
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
          );
        })}

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
