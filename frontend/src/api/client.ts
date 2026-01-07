import axios from 'axios';
import type {
  AnalysisRequest,
  AnalysisResponse,
  LocationValidation,
  POIsResponse,
  POITypesResponse,
  PremiumSearchRequest,
  PremiumSearchResponse,
  TripAdvisorEnrichment,
  TripAdvisorUsage,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  /**
   * Run multi-criteria location analysis
   */
  analyze: async (request: AnalysisRequest): Promise<AnalysisResponse> => {
    const response = await apiClient.post<AnalysisResponse>('/analyze', request);
    return response.data;
  },

  /**
   * Validate and geocode a location string
   */
  validateLocation: async (query: string): Promise<LocationValidation> => {
    const response = await apiClient.get<LocationValidation>('/validate-location', {
      params: { q: query },
    });
    return response.data;
  },

  /**
   * Get available POI types
   */
  getPOITypes: async (): Promise<POITypesResponse> => {
    const response = await apiClient.get<POITypesResponse>('/poi-types');
    return response.data;
  },

  /**
   * Health check
   */
  healthCheck: async (): Promise<{ status: string }> => {
    const response = await apiClient.get<{ status: string }>('/health');
    return response.data;
  },

  /**
   * Query POIs within a polygon
   */
  queryPOIs: async (
    polygon: GeoJSON.FeatureCollection,
    poiType: string
  ): Promise<POIsResponse> => {
    const response = await apiClient.post<POIsResponse>('/pois', {
      polygon: polygon,
      poi_type: poiType,
    });
    return response.data;
  },

  /**
   * Get TripAdvisor enrichment data for a POI
   */
  getTripAdvisorEnrichment: async (
    name: string,
    lat: number,
    lon: number,
    poiType: string = 'Restaurant'
  ): Promise<TripAdvisorEnrichment> => {
    const response = await apiClient.get<TripAdvisorEnrichment>('/poi/tripadvisor', {
      params: { name, lat, lon, poi_type: poiType },
    });
    return response.data;
  },

  /**
   * Get TripAdvisor API usage statistics
   */
  getTripAdvisorUsage: async (): Promise<TripAdvisorUsage> => {
    const response = await apiClient.get<TripAdvisorUsage>('/tripadvisor/usage');
    return response.data;
  },

  /**
   * Run premium search using TripAdvisor within analysis polygon
   */
  premiumSearch: async (request: PremiumSearchRequest): Promise<PremiumSearchResponse> => {
    const response = await apiClient.post<PremiumSearchResponse>('/premium-search', request);
    return response.data;
  },
};

export default api;
