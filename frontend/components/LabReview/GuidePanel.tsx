/**
 * Lab guide display panel with markdown rendering
 */

'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

      <div className="prose prose-base max-w-none prose-headings:font-bold prose-headings:text-gray-900 prose-h1:text-2xl prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4 prose-h2:border-b prose-h2:border-gray-300 prose-h2:pb-2 prose-h3:text-lg prose-h3:mt-6 prose-h3:mb-3 prose-h4:text-base prose-h4:mt-4 prose-h4:mb-2 prose-p:text-gray-800 prose-p:my-3 prose-li:text-gray-800 prose-code:text-gray-900 prose-strong:text-gray-900 prose-strong:font-semibold prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-ul:my-4 prose-ol:my-4 [&_*]:text-gray-800 [&_h1]:text-gray-900 [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mt-0 [&_h1]:mb-4 [&_h2]:text-gray-900 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:mt-8 [&_h2]:mb-4 [&_h2]:border-b [&_h2]:border-gray-300 [&_h2]:pb-2 [&_h3]:text-gray-900 [&_h3]:text-lg [&_h3]:font-bold [&_h3]:mt-6 [&_h3]:mb-3 [&_h4]:text-gray-900 [&_h4]:text-base [&_h4]:font-bold [&_h4]:mt-4 [&_h4]:mb-2 [&_strong]:text-gray-900 [&_strong]:font-semibold [&_code]:text-gray-900 [&_code]:bg-gray-100 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-sm [&_pre]:bg-gray-900 [&_pre]:text-gray-100 [&_pre]:p-4 [&_pre]:rounded [&_pre]:overflow-x-auto [&_pre_code]:bg-transparent [&_pre_code]:text-gray-100 [&_pre_code]:p-0 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:list-decimal [&_ol]:pl-6 [&_li]:my-1">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
}
