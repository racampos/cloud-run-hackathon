/**
 * Device configurations panel with tabs
 */

'use client';

import { useState } from 'react';
import { CodeBlock } from '@/components/shared/CodeBlock';

interface ConfigsPanelProps {
  initialConfigs: Record<string, string[]>;
  targetConfigs: Record<string, string[]>;
  platforms: Record<string, string>;
}

export function ConfigsPanel({
  initialConfigs,
  targetConfigs,
  platforms,
}: ConfigsPanelProps) {
  const devices = Object.keys(initialConfigs);
  const [selectedDevice, setSelectedDevice] = useState(devices[0] || '');
  const [configType, setConfigType] = useState<'initial' | 'target'>('initial');

  if (devices.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Device Configurations
        </h3>
        <p className="text-gray-600">No configurations available yet</p>
      </div>
    );
  }

  const currentConfig =
    configType === 'initial'
      ? initialConfigs[selectedDevice]
      : targetConfigs[selectedDevice];

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Device Configurations
      </h3>

      {/* Device tabs */}
      <div className="flex gap-2 mb-4 border-b border-gray-200">
        {devices.map((device) => (
          <button
            key={device}
            onClick={() => setSelectedDevice(device)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              selectedDevice === device
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            {device.toUpperCase()}
            <span className="ml-2 text-xs text-gray-500">
              ({platforms[device]})
            </span>
          </button>
        ))}
      </div>

      {/* Config type tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setConfigType('initial')}
          className={`px-3 py-1 text-sm rounded-md transition-colors ${
            configType === 'initial'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Initial Config
        </button>
        <button
          onClick={() => setConfigType('target')}
          className={`px-3 py-1 text-sm rounded-md transition-colors ${
            configType === 'target'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Target Config
        </button>
      </div>

      {/* Config display */}
      <CodeBlock
        code={currentConfig?.join('\n') || '# No configuration'}
        language="cisco"
        maxHeight="400px"
      />
    </div>
  );
}
