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

      <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-800 prose-li:text-gray-800 [&_h1]:text-gray-900 [&_h2]:text-gray-900 [&_h3]:text-gray-900 [&_p]:text-gray-800 [&_li]:text-gray-800 [&_ul]:text-gray-800 [&_ol]:text-gray-800">
        <h1 className="text-gray-900">{guide.title}</h1>

        {guide.objectives && guide.objectives.length > 0 && (
          <div>
            <h2 className="text-gray-900">Learning Objectives</h2>
            <ul className="text-gray-800">
              {guide.objectives.map((obj, i) => (
                <li key={i} className="text-gray-800">{obj}</li>
              ))}
            </ul>
          </div>
        )}

        {guide.prerequisites && guide.prerequisites.length > 0 && (
          <div>
            <h2 className="text-gray-900">Prerequisites</h2>
            <ul className="text-gray-800">
              {guide.prerequisites.map((prereq, i) => (
                <li key={i} className="text-gray-800">{prereq}</li>
              ))}
            </ul>
          </div>
        )}

        {guide.topology_description && (
          <div>
            <h2 className="text-gray-900">Network Topology</h2>
            <p className="text-gray-800">{guide.topology_description}</p>
          </div>
        )}

        {guide.initial_setup && guide.initial_setup.length > 0 && (
          <div>
            <h2 className="text-gray-900">Initial Setup</h2>
            <ol className="text-gray-800">
              {guide.initial_setup.map((step, stepIdx) => (
                <li key={stepIdx}>
                  {step.type === 'cmd' && (
                    <div>
                      <strong>Command:</strong>{' '}
                      <code className="bg-gray-100 px-2 py-1 rounded text-gray-900">
                        {step.value}
                      </code>
                      {step.description && (
                        <p className="text-sm text-gray-700 mt-1">
                          {step.description}
                        </p>
                      )}
                    </div>
                  )}
                  {step.type === 'verify' && (
                    <div>
                      <strong>Verify:</strong>{' '}
                      <code className="bg-blue-100 px-2 py-1 rounded text-gray-900">
                        {step.value}
                      </code>
                      {step.description && (
                        <p className="text-sm text-gray-700 mt-1">
                          {step.description}
                        </p>
                      )}
                    </div>
                  )}
                  {step.type === 'note' && (
                    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3">
                      <p className="text-sm text-gray-800">{step.value}</p>
                    </div>
                  )}
                  {step.type === 'output' && (
                    <div className="bg-gray-50 border-l-4 border-gray-400 p-3">
                      <strong className="text-gray-900">Expected Output:</strong>
                      <pre className="text-xs text-gray-800 mt-2 overflow-x-auto">
                        {step.value}
                      </pre>
                      {step.description && (
                        <p className="text-sm text-gray-700 mt-2">
                          {step.description}
                        </p>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}

        {guide.device_sections && guide.device_sections.length > 0 && guide.device_sections.map((device, idx) => (
          <div key={idx} className="mt-6">
            <h2 className="text-gray-900">Device: {device.device_name.toUpperCase()}</h2>
            <p className="text-sm text-gray-800">
              Platform: {device.platform}
              {device.role && ` | Role: ${device.role}`}
            </p>

            {device.ip_table && Object.keys(device.ip_table).length > 0 && (
              <div className="my-4">
                <h3 className="text-gray-900">IP Addressing</h3>
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

            <h3 className="text-gray-900">Configuration Steps</h3>
            <ol className="text-gray-800">
              {device.steps && device.steps.length > 0 && device.steps.map((step, stepIdx) => (
                <li key={stepIdx}>
                  {step.type === 'cmd' && (
                    <div>
                      <strong>Command:</strong>{' '}
                      <code className="bg-gray-100 px-2 py-1 rounded text-gray-900">
                        {step.value}
                      </code>
                      {step.description && (
                        <p className="text-sm text-gray-700 mt-1">
                          {step.description}
                        </p>
                      )}
                    </div>
                  )}
                  {step.type === 'verify' && (
                    <div>
                      <strong>Verify:</strong>{' '}
                      <code className="bg-blue-100 px-2 py-1 rounded text-gray-900">
                        {step.value}
                      </code>
                      {step.description && (
                        <p className="text-sm text-gray-700 mt-1">
                          {step.description}
                        </p>
                      )}
                    </div>
                  )}
                  {step.type === 'note' && (
                    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3">
                      <p className="text-sm text-gray-800">{step.value}</p>
                    </div>
                  )}
                  {step.type === 'output' && (
                    <div className="bg-gray-50 border-l-4 border-gray-400 p-3">
                      <strong className="text-gray-900">Expected Output:</strong>
                      <pre className="text-xs text-gray-800 mt-2 overflow-x-auto">
                        {step.value}
                      </pre>
                      {step.description && (
                        <p className="text-sm text-gray-700 mt-2">
                          {step.description}
                        </p>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </div>
        ))}

        {guide.final_verification && guide.final_verification.length > 0 && (
          <div>
            <h2 className="text-gray-900">Final Verification</h2>
            <ul className="text-gray-800">
              {guide.final_verification.map((step, i) => (
                <li key={i}>
                  <code className="bg-blue-100 px-2 py-1 rounded text-gray-900">
                    {step.value}
                  </code>
                  {step.description && (
                    <span className="ml-2 text-sm text-gray-700">
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
            <h2 className="text-gray-900">Troubleshooting Tips</h2>
            <ul className="text-gray-800">
              {guide.troubleshooting_tips.map((tip, i) => (
                <li key={i} className="text-gray-800">{tip}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
