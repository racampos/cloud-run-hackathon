/**
 * Validation results panel
 */

'use client';

import type { ValidationResult } from '@/lib/types';

interface ValidationPanelProps {
  result: ValidationResult;
}

export function ValidationPanel({ result }: ValidationPanelProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Validation Results
      </h3>

      <div className="space-y-4">
        {/* Status */}
        <div className="flex items-center gap-3">
          {result.success ? (
            <div className="flex items-center gap-2 text-green-700">
              <svg
                className="w-6 h-6"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="font-semibold">Validation Passed</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-red-700">
              <svg
                className="w-6 h-6"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="font-semibold">Validation Failed</span>
            </div>
          )}
        </div>

        {/* Execution details */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Exercise ID:</span>
            <p className="font-mono text-xs mt-1">{result.exercise_id}</p>
          </div>
          <div>
            <span className="text-gray-600">Build ID:</span>
            <p className="font-mono text-xs mt-1">{result.build_id}</p>
          </div>
          {result.duration_seconds && (
            <div>
              <span className="text-gray-600">Duration:</span>
              <p className="font-medium mt-1">
                {result.duration_seconds.toFixed(1)}s
              </p>
            </div>
          )}
          {result.summary?.passed_steps !== undefined && (
            <div>
              <span className="text-gray-600">Steps Passed:</span>
              <p className="font-medium mt-1">
                {result.summary.passed_steps} / {result.summary.total_steps}
              </p>
            </div>
          )}
        </div>

        {/* Error summary */}
        {result.error_summary && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="text-sm font-semibold text-red-900 mb-2">
              Error Details
            </h4>
            <p className="text-sm text-red-800 whitespace-pre-wrap">
              {result.error_summary}
            </p>
          </div>
        )}

        {/* Artifact links */}
        {result.artifact_urls && Object.keys(result.artifact_urls).length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">
              Artifacts
            </h4>
            <div className="space-y-2">
              {Object.entries(result.artifact_urls).map(([name, url]) => (
                <a
                  key={name}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  {name.replace(/_/g, ' ')}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
