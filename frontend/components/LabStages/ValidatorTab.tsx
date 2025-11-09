/**
 * Validator stage tab content
 */

'use client';

import type { ValidationResult } from '@/lib/types';

interface ValidatorTabProps {
  validationResult?: ValidationResult | null;
}

export function ValidatorTab({ validationResult }: ValidatorTabProps) {
  if (!validationResult) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="text-center py-12">
          <div className="text-gray-400 mb-2">
            <svg
              className="w-12 h-12 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <p className="text-gray-600">Validation results will appear here once available.</p>
          <p className="text-sm text-gray-500 mt-2">
            The validation process tests the lab in a simulated environment.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Validation Status */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Validation Status</h3>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              validationResult.success
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {validationResult.success ? 'Passed' : 'Failed'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <span className="text-sm text-gray-600">Exercise ID:</span>
            <span className="ml-2 font-mono text-sm text-gray-900">
              {validationResult.exercise_id}
            </span>
          </div>
          <div>
            <span className="text-sm text-gray-600">Build ID:</span>
            <span className="ml-2 font-mono text-sm text-gray-900">
              {validationResult.build_id}
            </span>
          </div>
          {validationResult.duration_seconds && (
            <div>
              <span className="text-sm text-gray-600">Duration:</span>
              <span className="ml-2 text-sm text-gray-900">
                {validationResult.duration_seconds}s
              </span>
            </div>
          )}
          {validationResult.summary?.passed_steps !== undefined &&
            validationResult.summary?.total_steps !== undefined && (
              <div>
                <span className="text-sm text-gray-600">Steps:</span>
                <span className="ml-2 text-sm text-gray-900">
                  {validationResult.summary.passed_steps} / {validationResult.summary.total_steps}{' '}
                  passed
                </span>
              </div>
            )}
        </div>
      </div>

      {/* Error Summary */}
      {validationResult.error_summary && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h4 className="text-sm font-semibold text-red-900 mb-2">Error Summary</h4>
          <pre className="text-sm text-red-800 whitespace-pre-wrap">
            {validationResult.error_summary}
          </pre>
        </div>
      )}

      {/* Artifact URLs */}
      {validationResult.artifact_urls && Object.keys(validationResult.artifact_urls).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">Artifacts</h4>
          <div className="space-y-2">
            {Object.entries(validationResult.artifact_urls).map(([name, url]) => (
              <div key={name} className="flex items-center justify-between">
                <span className="text-sm text-gray-700">{name}</span>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  View →
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
