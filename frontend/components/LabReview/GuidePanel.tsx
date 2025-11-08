/**
 * Lab guide display panel with markdown rendering
 */

'use client';

import ReactMarkdown from 'react-markdown';

interface GuidePanelProps {
  markdown: string;
  estimatedTime?: number;
}

export function GuidePanel({ markdown, estimatedTime }: GuidePanelProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Lab Guide</h3>
        {estimatedTime && (
          <div className="flex gap-2 text-sm text-gray-600">
            <span>⏱️ {estimatedTime} min</span>
          </div>
        )}
      </div>

      <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-800 prose-li:text-gray-800 prose-code:text-gray-900 prose-strong:text-gray-900 [&_h1]:text-gray-900 [&_h2]:text-gray-900 [&_h3]:text-gray-900 [&_p]:text-gray-800 [&_li]:text-gray-800 [&_ul]:text-gray-800 [&_ol]:text-gray-800 [&_code]:bg-gray-100 [&_code]:px-2 [&_code]:py-1 [&_code]:rounded [&_pre]:bg-gray-900 [&_pre]:text-gray-100 [&_pre>code]:bg-transparent [&_pre>code]:p-0">
        <ReactMarkdown>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
}
