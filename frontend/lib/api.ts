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
  SendMessageRequest,
  SendMessageResponse,
} from './types';
import { mockLabs } from './mockData';

// Configuration
const USE_MOCK_DATA = false; // Set to false when backend API is ready
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

    // Initialize mock lab with conversation
    const initialMessage = {
      role: 'user' as const,
      content: request.prompt,
      timestamp: new Date().toISOString(),
    };

    mockLabs[labId] = {
      lab_id: labId,
      status: 'planner_running',
      current_agent: 'planner',
      conversation: {
        messages: [initialMessage],
        awaiting_user_input: false,
      },
      progress: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      prompt: request.prompt,
    };

    // Simulate initial Planner response
    setTimeout(() => {
      simulatePlannerResponse(labId);
    }, 2000);

    return { lab_id: labId, status: 'planner_running' };
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
 * Send a message to the interactive Planner agent (OLD - deprecated)
 */
export async function sendMessage(
  labId: string,
  content: string
): Promise<SendMessageResponse> {
  if (USE_MOCK_DATA) {
    await delay(800);
    const lab = mockLabs[labId];
    if (!lab) {
      throw new Error('Lab not found');
    }

    // Add user message
    const userMessage = {
      role: 'user' as const,
      content,
      timestamp: new Date().toISOString(),
    };
    lab.conversation.messages.push(userMessage);
    lab.conversation.awaiting_user_input = false;
    lab.status = 'planner_running';
    lab.current_agent = 'planner';
    lab.updated_at = new Date().toISOString();

    // Simulate Planner response after delay
    setTimeout(() => {
      simulatePlannerResponse(labId);
    }, 2000);

    return {
      lab_id: labId,
      status: lab.status,
      conversation: lab.conversation,
      progress: {
        exercise_spec: lab.progress.exercise_spec,
      },
    };
  }

  // Real API call
  const response = await fetch(`${API_BASE_URL}/api/labs/${labId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content } as SendMessageRequest),
  });

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Chat with Planner agent (NEW ARCHITECTURE)
 */
export async function chatWithPlanner(
  labId: string,
  message: string
): Promise<ChatResponse> {
  if (USE_MOCK_DATA) {
    await delay(800);
    const lab = mockLabs[labId];
    if (!lab) {
      throw new Error('Lab not found');
    }

    // Add user message to conversation
    const userMessage = {
      role: 'user' as const,
      content: message,
      timestamp: new Date().toISOString(),
    };
    lab.conversation.messages.push(userMessage);

    // Simulate Planner response
    const plannerResponse =
      'Thank you! I have all the information I need to create your lab.';
    const assistantMessage = {
      role: 'assistant' as const,
      content: plannerResponse,
      timestamp: new Date().toISOString(),
    };
    lab.conversation.messages.push(assistantMessage);

    // Mark as complete and trigger generation
    lab.status = 'planner_complete';
    lab.current_agent = null;

    // Simulate generation starting
    setTimeout(() => {
      if (lab.status === 'planner_complete') {
        simulateRestOfPipeline(labId);
      }
    }, 1000);

    return {
      done: true,
      response: plannerResponse,
      exercise_spec: lab.progress.exercise_spec,
      generation_started: true,
    };
  }

  // Real API call
  const response = await fetch(`${API_BASE_URL}/api/labs/${labId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error(`Failed to chat with Planner: ${response.statusText}`);
  }

  return response.json();
}


/**
 * Simulate Planner agent response with questions or completion
 */
function simulatePlannerResponse(labId: string) {
  const lab = mockLabs[labId];
  if (!lab) return;

  const messageCount = lab.conversation.messages.length;

  // First response: Ask a clarifying question
  if (messageCount === 2) {
    const assistantMessage = {
      role: 'assistant' as const,
      content:
        "Thanks for that prompt! I'd like to clarify a few things:\n\n" +
        "1. What difficulty level should this lab target? (CCNA, CCNP, CCIE)\n" +
        "2. How many devices would you like in the topology?\n" +
        "3. Should this lab include verification steps?\n\n" +
        "Please provide your answers so I can create the perfect lab for your needs.",
      timestamp: new Date().toISOString(),
    };
    lab.conversation.messages.push(assistantMessage);
    lab.conversation.awaiting_user_input = true;
    lab.status = 'awaiting_user_input';
    lab.current_agent = 'planner';
    lab.updated_at = new Date().toISOString();
    return;
  }

  // Second response: Complete the exercise spec
  if (messageCount === 4) {
    const assistantMessage = {
      role: 'assistant' as const,
      content:
        "Perfect! I have all the information I need. Creating your exercise specification now...",
      timestamp: new Date().toISOString(),
    };
    lab.conversation.messages.push(assistantMessage);
    lab.conversation.awaiting_user_input = false;
    lab.status = 'planner_complete';
    lab.current_agent = null;
    lab.updated_at = new Date().toISOString();

    // Add exercise spec
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

    // Continue with rest of pipeline
    setTimeout(() => {
      simulateRestOfPipeline(labId);
    }, 500);
  }
}

/**
 * Continue pipeline after Planner completes
 */
function simulateRestOfPipeline(labId: string) {
  const stages: Array<{ status: LabStatus; agent: string | null; delay: number }> = [
    { status: 'designer_running', agent: 'designer', delay: 3000 },
    { status: 'designer_complete', agent: null, delay: 500 },
    { status: 'author_running', agent: 'author', delay: 4000 },
    { status: 'author_complete', agent: null, delay: 500 },
    { status: 'validator_running', agent: 'validator', delay: 5000 },
    { status: 'validator_complete', agent: null, delay: 500 },
    { status: 'completed', agent: null, delay: 500 },
  ];

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
