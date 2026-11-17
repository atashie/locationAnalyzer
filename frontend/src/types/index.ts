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

// Premium Search Types
//
// Premium search is a module with no provider behind it. The TripAdvisor
// Content API was retired in 2026 and its client was removed on 2026-11-17;
// an alternative API (Yelp Fusion, Foursquare, Google Places) plugs in on the
// backend. See docs/engineering-notes/reference-places-provider-needed.md.
//
// These four categories are TripAdvisor's taxonomy, kept so the dropdown and
// the wire format still work. They are provider-shaped ('geos' is not a kind
// of place) and should be revisited when a provider is chosen.

export type PlaceCategory = 'restaurants' | 'hotels' | 'attractions' | 'geos';

export const PLACE_SUBCATEGORIES: Record<PlaceCategory, string[]> = {
  restaurants: [
    'fine_dining', 'casual_dining', 'fast_food', 'cafes',
    'bakeries', 'bars', 'pizza', 'seafood', 'italian', 'asian'
  ],
  hotels: [
    'luxury', 'boutique', 'budget', 'resort', 'bed_and_breakfast'
  ],
  attractions: [
    'museums', 'parks', 'tours', 'nightlife', 'spas',
    'shopping', 'outdoor_activities', 'water_sports'
  ],
  geos: []
};

export interface PremiumSearchRequest {
  geojson: GeoJSON.FeatureCollection;
  category: PlaceCategory;
  subcategory?: string;
  max_locations: number;
}

export interface PremiumLocation {
  location_id: string;
  name: string;
  lat: number;
  lon: number;
  category: string;
  address?: string;
  rating?: number;
  num_reviews?: number;
  price_level?: string;
  ranking_string?: string;
  web_url?: string;
  photos: string[];
  cuisine?: string[];
  phone?: string;
  website?: string;
  description?: string;
}

export interface PremiumSearchResponse {
  success: boolean;
  provider: string;
  category: string;
  total_found: number;
  locations: PremiumLocation[];
  centroids_searched: number;
  api_calls_used: number;
  geojson: GeoJSON.FeatureCollection;
}
