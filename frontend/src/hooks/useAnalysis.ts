import { useMutation, useQuery } from '@tanstack/react-query';
import api from '../api/client';
import type { AnalysisRequest } from '../types';

/**
 * Hook for fetching available POI types
 */
export function usePOITypes() {
  return useQuery({
    queryKey: ['poi-types'],
    queryFn: api.getPOITypes,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
}

/**
 * Hook for validating/geocoding a location
 */
export function useValidateLocation(query: string, enabled = false) {
  return useQuery({
    queryKey: ['validate-location', query],
    queryFn: () => api.validateLocation(query),
    enabled: enabled && query.length >= 2,
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
}

/**
 * Hook for running location analysis
 */
export function useAnalysis() {
  return useMutation({
    mutationFn: (request: AnalysisRequest) => api.analyze(request),
  });
}

/**
 * Hook for health check
 */
export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.healthCheck,
    staleTime: 1000 * 30, // Check every 30 seconds
  });
}
