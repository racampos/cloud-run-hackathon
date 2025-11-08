/**
 * API client for NetGenius Orchestrator
 * Currently using mock data - will connect to real backend later
 */

import type {
  Lab,
  CreateLabRequest,
  CreateLabResponse,
  LabListItem,
  LabStatus,
} from './types';
import { mockLabs } from './mockData';

// Configuration
const USE_MOCK_DATA = true; // Set to false when backend API is ready
const API_BASE_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8080';

// Simulate network delay for realistic UX
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Create a new lab from instructor prompt
 */
export async function createLab(request: CreateLabRequest): Promise<CreateLabResponse> {
  if (USE_MOCK_DATA) {
    await delay(500);
    const labId = `lab_${Date.now()}`;

    // Initialize mock lab
    mockLabs[labId] = {
      lab_id: labId,
      status: 'pending',
      current_agent: null,
      progress: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      prompt: request.prompt,
    };

    // Simulate pipeline progression
    simulatePipelineProgress(labId, request.dry_run || false);

    return { lab_id: labId, status: 'pending' };
  }

  // Real API call (when backend is ready)
  const response = await fetch(`${API_BASE_URL}/api/labs/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to create lab: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get lab status and current progress
 */
export async function getLabStatus(labId: string): Promise<Lab> {
  if (USE_MOCK_DATA) {
    await delay(200);
    const lab = mockLabs[labId];
    if (!lab) {
      throw new Error('Lab not found');
    }
    return lab;
  }

  // Real API call
  const response = await fetch(`${API_BASE_URL}/api/labs/${labId}/status`);

  if (!response.ok) {
    throw new Error(`Failed to get lab status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get full lab details
 */
export async function getLab(labId: string): Promise<Lab> {
  if (USE_MOCK_DATA) {
    await delay(200);
    const lab = mockLabs[labId];
    if (!lab) {
      throw new Error('Lab not found');
    }
    return lab;
  }

  // Real API call
  const response = await fetch(`${API_BASE_URL}/api/labs/${labId}`);

  if (!response.ok) {
    throw new Error(`Failed to get lab: ${response.statusText}`);
  }

  return response.json();
}

/**
 * List all labs
 */
export async function listLabs(): Promise<LabListItem[]> {
  if (USE_MOCK_DATA) {
    await delay(300);
    return Object.values(mockLabs).map((lab) => ({
      lab_id: lab.lab_id,
      title: lab.progress.exercise_spec?.title || lab.prompt.substring(0, 50) + '...',
      status: lab.status,
      created_at: lab.created_at,
    }));
  }

  // Real API call
  const response = await fetch(`${API_BASE_URL}/api/labs`);

  if (!response.ok) {
    throw new Error(`Failed to list labs: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Submit feedback for a failed lab (for RCA)
 */
export async function submitFeedback(
  labId: string,
  feedback: string
): Promise<void> {
  if (USE_MOCK_DATA) {
    await delay(500);
    console.log('Mock feedback submitted:', { labId, feedback });
    return;
  }

  // Real API call
  const response = await fetch(`${API_BASE_URL}/api/labs/${labId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback_text: feedback }),
  });

  if (!response.ok) {
    throw new Error(`Failed to submit feedback: ${response.statusText}`);
  }
}

/**
 * Simulate pipeline progression for mock data
 * Updates the lab status through different stages
 */
function simulatePipelineProgress(labId: string, dryRun: boolean) {
  const stages: Array<{ status: LabStatus; agent: string | null; delay: number }> = [
    { status: 'planner_running', agent: 'planner', delay: 2000 },
    { status: 'planner_complete', agent: null, delay: 500 },
    { status: 'designer_running', agent: 'designer', delay: 3000 },
    { status: 'designer_complete', agent: null, delay: 500 },
    { status: 'author_running', agent: 'author', delay: 4000 },
    { status: 'author_complete', agent: null, delay: 500 },
  ];

  if (!dryRun) {
    stages.push(
      { status: 'validator_running', agent: 'validator', delay: 5000 },
      { status: 'validator_complete', agent: null, delay: 500 }
    );
  }

  stages.push({ status: 'completed', agent: null, delay: 500 });

  let cumulativeDelay = 0;

  stages.forEach(({ status, agent, delay: stageDelay }) => {
    cumulativeDelay += stageDelay;
    setTimeout(() => {
      const lab = mockLabs[labId];
      if (lab) {
        lab.status = status;
        lab.current_agent = agent;
        lab.updated_at = new Date().toISOString();

        // Add mock outputs as stages complete
        if (status === 'planner_complete') {
          lab.progress.exercise_spec = {
            title: 'Static Routing Lab',
            objectives: [
              'Configure basic IP addressing',
              'Implement static routes',
              'Verify connectivity with ping',
            ],
            constraints: { devices: 2, time_minutes: 30 },
            level: 'CCNA',
            prerequisites: ['Basic CLI navigation', 'IP addressing fundamentals'],
          };
        }

        if (status === 'designer_complete') {
          lab.progress.design_output = {
            topology_yaml: `devices:
  r1:
    type: router
    platform: cisco_2911
  r2:
    type: router
    platform: cisco_2911
links:
  - endpoints: [r1:GigabitEthernet0/0, r2:GigabitEthernet0/0]`,
            initial_configs: {
              r1: ['configure terminal', 'hostname R1', 'end'],
              r2: ['configure terminal', 'hostname R2', 'end'],
            },
            target_configs: {
              r1: [
                'interface GigabitEthernet0/0',
                'ip address 10.0.0.1 255.255.255.0',
                'no shutdown',
                'exit',
                'ip route 10.0.1.0 255.255.255.0 10.0.0.2',
              ],
              r2: [
                'interface GigabitEthernet0/0',
                'ip address 10.0.0.2 255.255.255.0',
                'no shutdown',
                'exit',
                'ip route 10.0.2.0 255.255.255.0 10.0.0.1',
              ],
            },
            platforms: { r1: 'cisco_2911', r2: 'cisco_2911' },
          };
        }

        if (status === 'author_complete') {
          lab.progress.draft_lab_guide = {
            title: 'Static Routing Lab',
            objectives: lab.progress.exercise_spec?.objectives || [],
            prerequisites: lab.progress.exercise_spec?.prerequisites || [],
            topology_description: 'Two routers connected via GigabitEthernet interfaces',
            device_sections: [
              {
                device_name: 'r1',
                platform: 'cisco_2911',
                role: 'Edge Router',
                ip_table: { 'GigabitEthernet0/0': '10.0.0.1/24' },
                steps: [
                  { type: 'cmd', value: 'configure terminal', description: 'Enter config mode' },
                  { type: 'cmd', value: 'interface GigabitEthernet0/0' },
                  { type: 'cmd', value: 'ip address 10.0.0.1 255.255.255.0' },
                  { type: 'cmd', value: 'no shutdown' },
                  { type: 'verify', value: 'show ip interface brief' },
                ],
              },
              {
                device_name: 'r2',
                platform: 'cisco_2911',
                role: 'Core Router',
                ip_table: { 'GigabitEthernet0/0': '10.0.0.2/24' },
                steps: [
                  { type: 'cmd', value: 'configure terminal', description: 'Enter config mode' },
                  { type: 'cmd', value: 'interface GigabitEthernet0/0' },
                  { type: 'cmd', value: 'ip address 10.0.0.2 255.255.255.0' },
                  { type: 'cmd', value: 'no shutdown' },
                  { type: 'verify', value: 'show ip interface brief' },
                ],
              },
            ],
            estimated_time_minutes: 30,
          };
        }

        if (status === 'validator_complete') {
          lab.progress.validation_result = {
            success: true,
            exercise_id: labId,
            build_id: `build_${Date.now()}`,
            duration_seconds: 45.2,
            summary: {
              passed_steps: 10,
              total_steps: 10,
            },
          };
        }
      }
    }, cumulativeDelay);
  });
}
