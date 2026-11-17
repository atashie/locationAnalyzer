import axios from 'axios';
import type {
  AnalysisRequest,
  AnalysisResponse,
  LocationValidation,
  POIsResponse,
  POITypesResponse,
  PremiumSearchRequest,
  PremiumSearchResponse,
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
   * Run premium search within the analysis polygon, using whichever places
   * provider the backend has configured.
   *
   * Throws an Error carrying the server's own explanation: a 503 means no
   * provider is configured, a 502 means the provider could not be reached.
   * Both are shown to the user verbatim, because the defect this replaces was
   * a failed lookup that looked exactly like an empty neighbourhood.
   */
  premiumSearch: async (request: PremiumSearchRequest): Promise<PremiumSearchResponse> => {
    try {
      const response = await apiClient.post<PremiumSearchResponse>('/premium-search', request);
      return response.data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string' && detail.length > 0) {
          throw new Error(detail);
        }
      }
      throw err;
    }
  },
};

export default api;
