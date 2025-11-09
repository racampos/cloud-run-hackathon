/**
 * Lab Design tab content - shows topology and configurations
 */

'use client';

import type { DesignOutput } from '@/lib/types';

interface LabDesignTabProps {
  designOutput: DesignOutput;
}

export function LabDesignTab({ designOutput }: LabDesignTabProps) {
  const devices = Object.keys(designOutput.platforms);

  return (
    <div className="space-y-6">
      {/* Topology */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Network Topology</h3>
        <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto text-sm">
          {designOutput.topology_yaml}
        </pre>
      </div>

      {/* Devices Overview */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Devices</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {devices.map((device) => (
            <div key={device} className="border border-gray-200 rounded-lg p-4">
              <div className="font-medium text-gray-900">{device}</div>
              <div className="text-sm text-gray-600 mt-1">
                Platform: <span className="text-gray-900">{designOutput.platforms[device]}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Initial Configurations */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Initial Configurations</h3>
        <div className="space-y-4">
          {devices.map((device) => (
            <div key={device}>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">{device}</h4>
              <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto text-sm">
                {designOutput.initial_configs[device]?.join('\n') || 'No initial configuration'}
              </pre>
            </div>
          ))}
        </div>
      </div>

      {/* Target Configurations */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Target Configurations</h3>
        <div className="space-y-4">
          {devices.map((device) => (
            <div key={device}>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">{device}</h4>
              <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto text-sm">
                {designOutput.target_configs[device]?.join('\n') || 'No target configuration'}
              </pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
