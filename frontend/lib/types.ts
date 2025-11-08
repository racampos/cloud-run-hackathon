/**
 * TypeScript types matching backend Pydantic schemas
 * Based on orchestrator/schemas/
 */

// ExerciseSpec - Output from Pedagogy Planner
export interface ExerciseSpec {
  title: string;
  objectives: string[];
  constraints: {
    devices?: number;
    time_minutes?: number;
    [key: string]: any;
  };
  level: string; // "CCNA", "CCNP", etc.
  prerequisites?: string[];
}

// DesignOutput - Output from Designer agent
export interface DesignOutput {
  topology_yaml: string;
  initial_configs: Record<string, string[]>; // device_name -> commands
  target_configs: Record<string, string[]>;  // device_name -> commands
  platforms: Record<string, string>;         // device_name -> platform type
  lint_results?: Record<string, any>;
}

// CommandStep - Individual step in lab guide
export interface CommandStep {
  type: 'cmd' | 'verify' | 'note' | 'output';
  value: string;
  description?: string;
}

// DeviceSection - Commands for a single device
export interface DeviceSection {
  device_name: string;
  platform: string;
  role?: string;
  ip_table?: Record<string, string>;
  steps: CommandStep[];
}

// DraftLabGuide - Output from Lab Guide Author
export interface DraftLabGuide {
  title: string;
  markdown?: string;
  objectives?: string[];
  prerequisites?: string[];
  topology_description?: string;
  initial_setup?: CommandStep[];
  device_sections: DeviceSection[];
  final_verification?: CommandStep[];
  troubleshooting_tips?: string[];
  estimated_time_minutes: number;
  lint_results?: Record<string, any>;
}

// ValidationResult - Output from Validator agent
export interface ValidationResult {
  success: boolean;
  exercise_id: string;
  build_id: string;
  artifact_urls?: Record<string, string>;
  error_summary?: string | null;
  duration_seconds?: number | null;
  summary?: {
    error?: string;
    passed_steps?: number;
    total_steps?: number;
    [key: string]: any;
  };
}

// PatchPlan - Output from RCA agent
export interface PatchPlan {
  analysis: string;
  root_cause_type: 'DESIGN' | 'INSTRUCTION' | 'OBJECTIVES' | 'UNKNOWN';
  target_agent: 'designer' | 'author' | 'planner';
  patch_instructions: string;
}

// Lab status types
export type LabStatus =
  | 'pending'
  | 'planner_running'
  | 'planner_complete'
  | 'designer_running'
  | 'designer_complete'
  | 'author_running'
  | 'author_complete'
  | 'validator_running'
  | 'validator_complete'
  | 'rca_running'
  | 'rca_complete'
  | 'completed'
  | 'failed';

// Lab - Full lab state with all outputs
export interface Lab {
  lab_id: string;
  status: LabStatus;
  current_agent?: string | null;
  progress: {
    exercise_spec?: ExerciseSpec;
    design_output?: DesignOutput;
    draft_lab_guide?: DraftLabGuide;
    validation_result?: ValidationResult;
    patch_plan?: PatchPlan;
  };
  created_at: string;
  updated_at: string;
  prompt: string;
  error?: string;
}

// API request/response types
export interface CreateLabRequest {
  prompt: string;
  dry_run?: boolean;
  enable_rca?: boolean;
}

export interface CreateLabResponse {
  lab_id: string;
  status: LabStatus;
}

export interface LabListItem {
  lab_id: string;
  title?: string;
  status: LabStatus;
  created_at: string;
}
