/**
 * Lab Guide tab content - shows markdown guide with optional validation banner
 */

'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ValidationResult } from '@/lib/types';

interface LabGuideTabProps {
  markdown: string;
  estimatedTime?: number;
  validationResult?: ValidationResult | null;
}

export function LabGuideTab({ markdown, estimatedTime, validationResult }: LabGuideTabProps) {
  return (
    <div className="space-y-6">
      {/* Validation Banner */}
      {validationResult && (
        <div
          className={`border rounded-lg p-4 ${
            validationResult.success
              ? 'bg-green-50 border-green-200'
              : 'bg-red-50 border-red-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {validationResult.success ? (
                <svg
                  className="w-6 h-6 text-green-600"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg
                  className="w-6 h-6 text-red-600"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              <div>
                <div
                  className={`font-semibold ${
                    validationResult.success ? 'text-green-900' : 'text-red-900'
                  }`}
                >
                  {validationResult.success
                    ? 'Validation Passed'
                    : 'Validation Issues Detected'}
                </div>
                <div
                  className={`text-sm ${
                    validationResult.success ? 'text-green-700' : 'text-red-700'
                  }`}
                >
                  {validationResult.success
                    ? 'This lab has been automatically validated and is ready to use.'
                    : 'This lab may need manual review before use.'}
                </div>
              </div>
            </div>
            {validationResult.summary?.passed_steps !== undefined &&
              validationResult.summary?.total_steps !== undefined && (
                <div
                  className={`text-sm font-medium ${
                    validationResult.success ? 'text-green-900' : 'text-red-900'
                  }`}
                >
                  {validationResult.summary.passed_steps} / {validationResult.summary.total_steps}{' '}
                  steps passed
                </div>
              )}
          </div>

          {/* Error summary (if failed) */}
          {!validationResult.success && validationResult.error_summary && (
            <div className="mt-3 pt-3 border-t border-red-200">
              <div className="text-sm font-semibold text-red-900 mb-1">Error Details:</div>
              <pre className="text-xs text-red-800 whitespace-pre-wrap bg-red-100 p-2 rounded">
                {validationResult.error_summary}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Lab Guide Content */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        {estimatedTime && (
          <div className="flex justify-end mb-4">
            <div className="flex gap-2 text-sm text-gray-600">
              <span>⏱️ Estimated Time: {estimatedTime} min</span>
            </div>
          </div>
        )}

        <div className="prose prose-base max-w-none prose-headings:font-bold prose-headings:text-gray-900 prose-h1:text-2xl prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4 prose-h2:border-b prose-h2:border-gray-300 prose-h2:pb-2 prose-h3:text-lg prose-h3:mt-6 prose-h3:mb-3 prose-h4:text-base prose-h4:mt-4 prose-h4:mb-2 prose-p:text-gray-800 prose-p:my-3 prose-li:text-gray-800 prose-code:text-gray-900 prose-strong:text-gray-900 prose-strong:font-semibold prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-ul:my-4 prose-ol:my-4 [&_*]:text-gray-800 [&_h1]:text-gray-900 [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mt-0 [&_h1]:mb-4 [&_h2]:text-gray-900 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:mt-8 [&_h2]:mb-4 [&_h2]:border-b [&_h2]:border-gray-300 [&_h2]:pb-2 [&_h3]:text-gray-900 [&_h3]:text-lg [&_h3]:font-bold [&_h3]:mt-6 [&_h3]:mb-3 [&_h4]:text-gray-900 [&_h4]:text-base [&_h4]:font-bold [&_h4]:mt-4 [&_h4]:mb-2 [&_strong]:text-gray-900 [&_strong]:font-semibold [&_code]:text-gray-900 [&_code]:bg-gray-100 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-sm [&_pre]:bg-gray-900 [&_pre]:text-gray-100 [&_pre]:p-4 [&_pre]:rounded [&_pre]:overflow-x-auto [&_pre_code]:bg-transparent [&_pre_code]:text-gray-100 [&_pre_code]:p-0 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:list-decimal [&_ol]:pl-6 [&_li]:my-1">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
