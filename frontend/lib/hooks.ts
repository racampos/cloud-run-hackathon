/**
 * React Query hooks for API interactions
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Lab, CreateLabRequest, LabListItem } from './types';
import * as api from './api';

/**
 * Hook to poll lab status with automatic refetch
 * Stops polling when lab reaches terminal state
 * Merges conversations to preserve optimistic updates
 */
export function useLabPolling(labId: string | null) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ['lab-status', labId],
    queryFn: async () => {
      const newData = await api.getLabStatus(labId!);

      // Get current data to merge conversations
      const currentData = queryClient.getQueryData(['lab-status', labId]) as Lab | undefined;

      if (currentData && currentData.conversation && newData.conversation) {
        // Merge conversations - keep local messages that aren't in the server response yet
        const serverMessageContents = new Set(
          newData.conversation.messages.map((m) => m.content)
        );

        const localOnlyMessages = currentData.conversation.messages.filter(
          (m) => !serverMessageContents.has(m.content)
        );

        // Combine: server messages first (already in correct order), then local-only messages
        // Don't sort by timestamp to avoid timezone issues - trust server order + append local
        const mergedMessages = [...newData.conversation.messages, ...localOnlyMessages];

        return {
          ...newData,
          conversation: {
            ...newData.conversation,
            messages: mergedMessages,
          },
        };
      }

      return newData;
    },
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

/**
 * Hook to send a message to the interactive Planner (OLD - deprecated)
 */
export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ labId, content }: { labId: string; content: string }) =>
      api.sendMessage(labId, content),
    onSuccess: (_, variables) => {
      // Invalidate lab data to refetch with updated conversation
      queryClient.invalidateQueries({ queryKey: ['lab-status', variables.labId] });
      queryClient.invalidateQueries({ queryKey: ['lab', variables.labId] });
    },
  });
}

/**
 * Hook to chat with Planner (NEW ARCHITECTURE)
 */
export function useChatWithPlanner() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ labId, message }: { labId: string; message: string }) =>
      api.chatWithPlanner(labId, message),
    onMutate: async ({ labId, message }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['lab-status', labId] });

      // Snapshot the previous value
      const previousLab = queryClient.getQueryData(['lab-status', labId]) as Lab | undefined;

      // Optimistically update to show user's message immediately
      if (previousLab) {
        queryClient.setQueryData(['lab-status', labId], {
          ...previousLab,
          conversation: {
            ...previousLab.conversation,
            messages: [
              ...previousLab.conversation.messages,
              {
                role: 'user' as const,
                content: message,
                timestamp: new Date().toISOString(),
              },
            ],
          },
        });
      }

      return { previousLab };
    },
    onSuccess: (data, variables) => {
      // Update with the assistant's response from the API
      const currentLab = queryClient.getQueryData(['lab-status', variables.labId]) as Lab | undefined;

      if (currentLab) {
        // Parse the actual response text
        // The backend might return exercise_spec as a string (the planner's message) or as an object
        let responseText = '';
        if (typeof data.exercise_spec === 'string') {
          // When done=false, exercise_spec contains the planner's message text
          responseText = data.exercise_spec;
        } else if (data.response && typeof data.response === 'string') {
          responseText = data.response;
        }

        // Only add assistant message if we have response text
        const updatedMessages = responseText
          ? [
              ...currentLab.conversation.messages,
              {
                role: 'assistant' as const,
                content: responseText,
                timestamp: new Date().toISOString(),
              },
            ]
          : currentLab.conversation.messages;

        queryClient.setQueryData(['lab-status', variables.labId], {
          ...currentLab,
          conversation: {
            ...currentLab.conversation,
            messages: updatedMessages,
          },
          progress: {
            ...currentLab.progress,
            // Only update exercise_spec if it's actually an object (not a string message)
            exercise_spec:
              data.done && typeof data.exercise_spec === 'object'
                ? data.exercise_spec
                : currentLab.progress.exercise_spec,
          },
          status: data.done ? 'planner_complete' : currentLab.status,
        });
      }

      // Don't invalidate immediately - let the existing 3-second polling sync up
      // This prevents the backend's delayed conversation update from overwriting our optimistic UI
      // The polling will eventually catch up with any server-side changes
    },
    onError: (err, variables, context) => {
      // Rollback to previous state on error
      if (context?.previousLab) {
        queryClient.setQueryData(['lab-status', variables.labId], context.previousLab);
      }
    },
  });
}
