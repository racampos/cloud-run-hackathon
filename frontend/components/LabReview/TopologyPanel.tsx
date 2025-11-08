/**
 * Topology YAML display panel
 */

'use client';

import { CodeBlock } from '@/components/shared/CodeBlock';

interface TopologyPanelProps {
  yaml: string;
}

export function TopologyPanel({ yaml }: TopologyPanelProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Network Topology
      </h3>
      <CodeBlock code={yaml} language="yaml" maxHeight="500px" />
    </div>
  );
}
