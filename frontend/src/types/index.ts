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

// UI State Types

export interface CriterionFormData {
  id: string;
  type: CriterionType;
  poi_type: string;
  location: string;
  mode: TravelMode;
  value: number;
}
