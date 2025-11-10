/**
 * Lab Validation tab - Shows device output transcripts from validation
 */

'use client';

import type { ValidationResult } from '@/lib/types';

interface LabValidationTabProps {
  validationResult: ValidationResult;
}

export function LabValidationTab({ validationResult }: LabValidationTabProps) {
  const { device_outputs, success, duration_seconds, summary } = validationResult;

  // Extract device name from filename (e.g., "R1_transcript.txt" -> "R1")
  const getDeviceName = (filename: string): string => {
    return filename.replace('_transcript.txt', '');
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Validation Summary */}
      <div className={`p-6 rounded-lg border-2 mb-6 ${
        success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
      }`}>
        <div className="flex items-center gap-3 mb-4">
          <div className={`text-3xl ${success ? 'text-green-600' : 'text-red-600'}`}>
            {success ? '✓' : '✗'}
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Validation {success ? 'Passed' : 'Failed'}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {duration_seconds && `Completed in ${duration_seconds.toFixed(1)}s`}
            </p>
          </div>
        </div>

        {summary && (
          <div className="grid grid-cols-2 gap-4 mt-4">
            {summary.passed_steps !== undefined && summary.total_steps !== undefined && (
              <div className="bg-white p-4 rounded border border-gray-200">
                <div className="text-sm text-gray-600">Steps Passed</div>
                <div className="text-2xl font-bold text-gray-900">
                  {summary.passed_steps} / {summary.total_steps}
                </div>
              </div>
            )}
            {summary.error && (
              <div className="col-span-2 bg-white p-4 rounded border border-red-200">
                <div className="text-sm text-red-600 font-medium">Error</div>
                <div className="text-sm text-gray-900 mt-1">{summary.error}</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Device Outputs */}
      {device_outputs && Object.keys(device_outputs).length > 0 ? (
        <div className="space-y-6">
          <h3 className="text-xl font-bold text-gray-900">Device Output Transcripts</h3>

          {Object.entries(device_outputs).map(([filename, transcript]) => {
            const deviceName = getDeviceName(filename);

            return (
              <div key={filename} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-800 px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-green-400 font-mono text-sm">●</div>
                    <h4 className="text-white font-semibold">{deviceName}</h4>
                    <span className="text-gray-400 text-sm font-mono">{filename}</span>
                  </div>
                </div>

                <div className="bg-gray-900 p-4 overflow-x-auto">
                  <pre className="text-sm font-mono text-green-400 whitespace-pre-wrap break-words">
                    {transcript}
                  </pre>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
          <div className="text-gray-400 mb-2">
            <svg
              className="w-16 h-16 mx-auto"
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
          <p className="text-gray-600">No device output transcripts available</p>
        </div>
      )}
    </div>
  );
}
