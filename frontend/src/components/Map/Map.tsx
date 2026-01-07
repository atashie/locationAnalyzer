import { useEffect, useMemo, useState, useCallback } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, useMap, CircleMarker } from 'react-leaflet';
import type { LatLngExpression, LatLngBoundsExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { POIFeature, TripAdvisorEnrichment } from '../../types';
import { api } from '../../api/client';

// Fix for default marker icons in Leaflet with Vite
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

interface MapProps {
  center?: [number, number];
  zoom?: number;
  geojson?: GeoJSON.FeatureCollection;
  markerPosition?: [number, number];
  markerLabel?: string;
  pois?: POIFeature[];
}

const DEFAULT_CENTER: LatLngExpression = [35.994, -78.899]; // Durham, NC
const DEFAULT_ZOOM = 11;

const TILE_URL = import.meta.env.VITE_MAP_TILE_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

/**
 * Component to handle map view updates when center/bounds change.
 * MapContainer props are immutable after mount, so we use useMap() hook.
 */
function MapUpdater({
  center,
  geojson
}: {
  center?: [number, number];
  geojson?: GeoJSON.FeatureCollection;
}) {
  const map = useMap();

  useEffect(() => {
    if (geojson && geojson.features && geojson.features.length > 0) {
      // If we have GeoJSON, fit the map to its bounds
      try {
        const bbox = geojson.bbox as [number, number, number, number] | undefined;
        if (bbox && bbox.length === 4) {
          // bbox format: [minLon, minLat, maxLon, maxLat]
          const bounds: LatLngBoundsExpression = [
            [bbox[1], bbox[0]], // Southwest: [minLat, minLon]
            [bbox[3], bbox[2]], // Northeast: [maxLat, maxLon]
          ];
          map.fitBounds(bounds, { padding: [20, 20] });
        } else if (center) {
          map.setView(center, 11);
        }
      } catch (e) {
        console.warn('Could not fit bounds:', e);
        if (center) {
          map.setView(center, 11);
        }
      }
    } else if (center) {
      // No GeoJSON, just center on the point
      map.setView(center, 11);
    }
  }, [map, center, geojson]);

  return null;
}

/**
 * POI Popup component that fetches TripAdvisor data on open.
 */
function POIPopup({ poi }: { poi: POIFeature }) {
  const [tripAdvisor, setTripAdvisor] = useState<TripAdvisorEnrichment | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  const fetchTripAdvisor = useCallback(async () => {
    if (fetched || loading) return;
    setLoading(true);
    try {
      const data = await api.getTripAdvisorEnrichment(
        poi.name,
        poi.lat,
        poi.lon,
        poi.poi_type
      );
      setTripAdvisor(data);
    } catch (error) {
      console.error('Failed to fetch TripAdvisor data:', error);
      setTripAdvisor({ found: false, photos: [], error: 'Failed to load' });
    } finally {
      setLoading(false);
      setFetched(true);
    }
  }, [poi, fetched, loading]);

  // Fetch when popup opens (component mounts)
  useEffect(() => {
    fetchTripAdvisor();
  }, [fetchTripAdvisor]);

  return (
    <div className="max-w-xs min-w-[200px]">
      <h3 className="font-bold text-sm mb-1">{poi.name}</h3>
      <p className="text-xs text-gray-500 mb-2">{poi.poi_type}</p>

      {/* TripAdvisor Section */}
      {loading && (
        <p className="text-xs text-gray-400 italic mb-2">Loading TripAdvisor...</p>
      )}

      {tripAdvisor && tripAdvisor.found && (
        <div className="mb-2 p-2 bg-gray-50 rounded border border-gray-200">
          <div className="flex items-center gap-2 mb-1">
            {tripAdvisor.rating && (
              <span className="text-sm font-medium">
                ⭐ {tripAdvisor.rating.toFixed(1)}
              </span>
            )}
            {tripAdvisor.num_reviews && (
              <span className="text-xs text-gray-500">
                ({tripAdvisor.num_reviews.toLocaleString()} reviews)
              </span>
            )}
            {tripAdvisor.price_level && (
              <span className="text-xs text-green-600 font-medium">
                {tripAdvisor.price_level}
              </span>
            )}
          </div>
          {tripAdvisor.ranking_string && (
            <p className="text-xs text-gray-600 mb-1">{tripAdvisor.ranking_string}</p>
          )}
          {tripAdvisor.cuisine && tripAdvisor.cuisine.length > 0 && (
            <p className="text-xs text-gray-500 mb-1">
              {tripAdvisor.cuisine.slice(0, 3).join(', ')}
            </p>
          )}
          {tripAdvisor.photos && tripAdvisor.photos.length > 0 && (
            <div className="flex gap-1 mt-2 overflow-x-auto">
              {tripAdvisor.photos.slice(0, 2).map((url, i) => (
                <img
                  key={i}
                  src={url}
                  alt={`${poi.name} photo ${i + 1}`}
                  className="w-16 h-16 object-cover rounded"
                />
              ))}
            </div>
          )}
          {tripAdvisor.tripadvisor_url && (
            <a
              href={tripAdvisor.tripadvisor_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-green-600 hover:underline block mt-1"
            >
              View on TripAdvisor →
            </a>
          )}
        </div>
      )}

      {tripAdvisor && !tripAdvisor.found && !tripAdvisor.error && (
        <p className="text-xs text-gray-400 italic mb-2">No TripAdvisor data</p>
      )}

      {/* OSM Data Section */}
      {poi.address && (
        <p className="text-xs text-gray-600 mb-1">📍 {poi.address}</p>
      )}
      {poi.opening_hours && (
        <p className="text-xs text-gray-600 mb-1">
          🕐 {poi.opening_hours}
        </p>
      )}
      {poi.phone && (
        <p className="text-xs text-gray-600 mb-1">
          📞{' '}
          <a href={`tel:${poi.phone}`} className="text-blue-600 hover:underline">
            {poi.phone}
          </a>
        </p>
      )}
      {poi.website && (
        <p className="text-xs">
          🔗{' '}
          <a
            href={poi.website.startsWith('http') ? poi.website : `https://${poi.website}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            Website
          </a>
        </p>
      )}
    </div>
  );
}

export function Map({
  center = DEFAULT_CENTER as [number, number],
  zoom = DEFAULT_ZOOM,
  geojson,
  markerPosition,
  markerLabel,
  pois,
}: MapProps) {
  // Generate a unique key for GeoJSON to force re-render when data changes
  // This is necessary because react-leaflet's GeoJSON doesn't update on data prop changes
  const geojsonKey = useMemo(() => {
    if (!geojson) return 'no-data';
    // Create a hash based on the geojson content
    return `geojson-${JSON.stringify(geojson.bbox || '')}-${geojson.features?.length || 0}-${Date.now()}`;
  }, [geojson]);

  return (
    <MapContainer
      center={center}
      zoom={zoom}
      className="h-full w-full rounded-lg"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url={TILE_URL}
      />

      {/* This component handles map view updates */}
      <MapUpdater center={center} geojson={geojson} />

      {markerPosition && (
        <Marker position={markerPosition}>
          {markerLabel && <Popup>{markerLabel}</Popup>}
        </Marker>
      )}

      {geojson && geojson.features && geojson.features.length > 0 && (
        <GeoJSON
          key={geojsonKey}
          data={geojson}
          style={{
            fillColor: '#3b82f6',
            fillOpacity: 0.3,
            color: '#1d4ed8',
            weight: 2,
          }}
        />
      )}

      {/* POI markers */}
      {pois && pois.map((poi) => (
        <CircleMarker
          key={poi.id}
          center={[poi.lat, poi.lon]}
          radius={8}
          pathOptions={{
            fillColor: '#ef4444',
            fillOpacity: 0.8,
            color: '#b91c1c',
            weight: 2,
          }}
        >
          <Popup>
            <POIPopup poi={poi} />
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

export default Map;
