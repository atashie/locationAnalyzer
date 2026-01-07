// API Types

export type TravelMode = 'walk' | 'bike' | 'drive' | 'distance';
export type CriterionType = 'poi' | 'location';

export interface Criterion {
  type: CriterionType;
  poi_type?: string;
  location?: string;
  mode: TravelMode;
  value: number;
}

export interface AnalysisRequest {
  center: string;
  radius_miles: number;
  criteria: Criterion[];
}

export interface CriterionResult {
  name: string;
  description: string;
  area_sq_miles: number;
}

export interface AnalysisResponse {
  success: boolean;
  center: string;
  center_lat: number;
  center_lon: number;
  initial_area_sq_miles: number;
  final_area_sq_miles: number;
  area_reduction_percent: number;
  criteria_applied: CriterionResult[];
  geojson: GeoJSON.FeatureCollection;
}

export interface LocationValidation {
  valid: boolean;
  query: string;
  lat?: number;
  lon?: number;
  display_name?: string;
  error_message?: string;
}

export interface POIType {
  name: string;
  tags: Record<string, string>;
}

export interface POITypesResponse {
  poi_types: POIType[];
}

export interface POIFeature {
  id: string;
  name: string;
  poi_type: string;
  lat: number;
  lon: number;
  address?: string;
  opening_hours?: string;
  phone?: string;
  website?: string;
}

export interface POIsResponse {
  success: boolean;
  poi_type: string;
  total_found: number;
  pois: POIFeature[];
  geojson: GeoJSON.FeatureCollection;
}

// UI State Types

export interface CriterionFormData {
  id: string;
  type: CriterionType;
  poi_type: string;
  location: string;
  mode: TravelMode;
  value: number;
  complexQuery: boolean;
}

// TripAdvisor Types

export interface TripAdvisorEnrichment {
  found: boolean;
  location_id?: string;
  rating?: number;
  num_reviews?: number;
  price_level?: string;
  ranking_string?: string;
  tripadvisor_url?: string;
  photos: string[];
  cuisine?: string[];
  error?: string;
}

export interface TripAdvisorUsage {
  enabled: boolean;
  monthly_limit: number;
  current_usage: number;
  limit_reached: boolean;
}
