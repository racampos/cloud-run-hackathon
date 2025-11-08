/**
 * React Query hooks for API interactions
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Lab, CreateLabRequest, LabListItem } from './types';
import * as api from './api';

/**
 * Hook to poll lab status with automatic refetch
 * Stops polling when lab reaches terminal state
 */
export function useLabPolling(labId: string | null) {
  return useQuery({
    queryKey: ['lab-status', labId],
    queryFn: () => api.getLabStatus(labId!),
    enabled: !!labId, // Only run if labId exists
    refetchInterval: (query) => {
      const data = query.state.data as Lab | undefined;
      // Stop polling if terminal state
      if (!data || data.status === 'completed' || data.status === 'failed') {
        return false;
      }
      return 3000; // Poll every 3 seconds
    },
    refetchOnWindowFocus: true,
    staleTime: 0, // Always consider data stale to enable polling
  });
}

/**
 * Hook to get full lab details
 */
export function useLab(labId: string | null) {
  return useQuery({
    queryKey: ['lab', labId],
    queryFn: () => api.getLab(labId!),
    enabled: !!labId,
  });
}

/**
 * Hook to list all labs
 */
export function useLabList() {
  return useQuery({
    queryKey: ['labs'],
    queryFn: api.listLabs,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  });
}

/**
 * Hook to create a new lab
 */
export function useCreateLab() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateLabRequest) => api.createLab(request),
    onSuccess: () => {
      // Invalidate labs list to show new lab
      queryClient.invalidateQueries({ queryKey: ['labs'] });
    },
  });
}

/**
 * Hook to submit feedback for RCA
 */
export function useSubmitFeedback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ labId, feedback }: { labId: string; feedback: string }) =>
      api.submitFeedback(labId, feedback),
    onSuccess: (_, variables) => {
      // Invalidate lab data to refetch with RCA results
      queryClient.invalidateQueries({ queryKey: ['lab-status', variables.labId] });
      queryClient.invalidateQueries({ queryKey: ['lab', variables.labId] });
    },
  });
}
