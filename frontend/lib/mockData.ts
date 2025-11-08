/**
 * Mock data storage for development
 * This simulates the backend's in-memory lab storage
 */

import type { Lab } from './types';

// In-memory storage for mock labs
export const mockLabs: Record<string, Lab> = {};
