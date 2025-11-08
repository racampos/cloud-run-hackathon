/**
 * Lab guide display panel with markdown rendering
 */

'use client';

import ReactMarkdown from 'react-markdown';
import type { DraftLabGuide } from '@/lib/types';

interface GuidePanelProps {
  guide: DraftLabGuide;
}

export function GuidePanel({ guide }: GuidePanelProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Lab Guide</h3>
        <div className="flex gap-2 text-sm text-gray-600">
          <span>⏱️ {guide.estimated_time_minutes} min</span>
        </div>
      </div>

      <div className="prose prose-sm max-w-none">
        <h1>{guide.title}</h1>

        {guide.objectives && guide.objectives.length > 0 && (
          <div>
            <h2>Learning Objectives</h2>
            <ul>
              {guide.objectives.map((obj, i) => (
                <li key={i}>{obj}</li>
              ))}
            </ul>
          </div>
        )}

        {guide.prerequisites && guide.prerequisites.length > 0 && (
          <div>
            <h2>Prerequisites</h2>
            <ul>
              {guide.prerequisites.map((prereq, i) => (
                <li key={i}>{prereq}</li>
              ))}
            </ul>
          </div>
        )}

        {guide.topology_description && (
          <div>
            <h2>Network Topology</h2>
            <p>{guide.topology_description}</p>
          </div>
        )}

        {guide.device_sections && guide.device_sections.length > 0 && guide.device_sections.map((device, idx) => (
          <div key={idx} className="mt-6">
            <h2>Device: {device.device_name.toUpperCase()}</h2>
            <p className="text-sm text-gray-600">
              Platform: {device.platform}
              {device.role && ` | Role: ${device.role}`}
            </p>

            {device.ip_table && Object.keys(device.ip_table).length > 0 && (
              <div className="my-4">
                <h3>IP Addressing</h3>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Interface
                      </th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        IP Address
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {Object.entries(device.ip_table).map(([intf, ip]) => (
                      <tr key={intf}>
                        <td className="px-4 py-2 text-sm">{intf}</td>
                        <td className="px-4 py-2 text-sm font-mono">{ip}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <h3>Configuration Steps</h3>
            <ol>
              {device.steps && device.steps.length > 0 && device.steps.map((step, stepIdx) => (
                <li key={stepIdx}>
                  {step.type === 'cmd' && (
                    <div>
                      <strong>Command:</strong>{' '}
                      <code className="bg-gray-100 px-2 py-1 rounded">
                        {step.value}
                      </code>
                      {step.description && (
                        <p className="text-sm text-gray-600 mt-1">
                          {step.description}
                        </p>
                      )}
                    </div>
                  )}
                  {step.type === 'verify' && (
                    <div>
                      <strong>Verify:</strong>{' '}
                      <code className="bg-blue-100 px-2 py-1 rounded">
                        {step.value}
                      </code>
                      {step.description && (
                        <p className="text-sm text-gray-600 mt-1">
                          {step.description}
                        </p>
                      )}
                    </div>
                  )}
                  {step.type === 'note' && (
                    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3">
                      <p className="text-sm">{step.value}</p>
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </div>
        ))}

        {guide.final_verification && guide.final_verification.length > 0 && (
          <div>
            <h2>Final Verification</h2>
            <ul>
              {guide.final_verification.map((step, i) => (
                <li key={i}>
                  <code className="bg-blue-100 px-2 py-1 rounded">
                    {step.value}
                  </code>
                  {step.description && (
                    <span className="ml-2 text-sm text-gray-600">
                      {step.description}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {guide.troubleshooting_tips && guide.troubleshooting_tips.length > 0 && (
          <div>
            <h2>Troubleshooting Tips</h2>
            <ul>
              {guide.troubleshooting_tips.map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
