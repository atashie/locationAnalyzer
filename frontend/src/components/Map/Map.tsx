import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, useMap, CircleMarker } from 'react-leaflet';
import type { LatLngExpression, LatLngBoundsExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { POIFeature, PremiumLocation } from '../../types';

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
  premiumLocations?: PremiumLocation[];
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
 * Simple POI Popup showing only OSM data (no TripAdvisor fetching).
 */
function POIPopup({ poi }: { poi: POIFeature }) {
  return (
    <div className="max-w-xs min-w-[200px]">
      <h3 className="font-bold text-sm mb-1">{poi.name}</h3>
      <p className="text-xs text-gray-500 mb-2">{poi.poi_type}</p>

      {poi.address && (
        <p className="text-xs text-gray-600 mb-1">📍 {poi.address}</p>
      )}
      {poi.opening_hours && (
        <p className="text-xs text-gray-600 mb-1">🕐 {poi.opening_hours}</p>
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

/**
 * Premium Location Popup with rich TripAdvisor data.
 */
function PremiumLocationPopup({ location }: { location: PremiumLocation }) {
  return (
    <div className="max-w-xs min-w-[240px]">
      {/* Header with name and rating */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-bold text-sm">{location.name}</h3>
          <p className="text-xs text-purple-600 font-medium capitalize">{location.category}</p>
        </div>
        {location.rating && (
          <div className="flex items-center gap-1 bg-purple-100 px-2 py-1 rounded">
            <span className="text-sm">⭐</span>
            <span className="text-sm font-bold text-purple-800">
              {location.rating.toFixed(1)}
            </span>
          </div>
        )}
      </div>

      {/* Rating details */}
      <div className="flex items-center gap-2 mb-2">
        {location.num_reviews && (
          <span className="text-xs text-gray-500">
            {location.num_reviews.toLocaleString()} reviews
          </span>
        )}
        {location.price_level && (
          <span className="text-xs text-green-600 font-medium">
            {location.price_level}
          </span>
        )}
      </div>

      {/* Ranking */}
      {location.ranking_string && (
        <p className="text-xs text-gray-600 mb-2 italic">
          {location.ranking_string}
        </p>
      )}

      {/* Cuisine */}
      {location.cuisine && location.cuisine.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {location.cuisine.slice(0, 4).map((c, i) => (
            <span
              key={i}
              className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      {/* Photos */}
      {location.photos && location.photos.length > 0 && (
        <div className="flex gap-1 mb-2 overflow-x-auto">
          {location.photos.slice(0, 3).map((url, i) => (
            <img
              key={i}
              src={url}
              alt={`${location.name} photo ${i + 1}`}
              className="w-20 h-20 object-cover rounded"
            />
          ))}
        </div>
      )}

      {/* Address and contact */}
      {location.address && (
        <p className="text-xs text-gray-600 mb-1">📍 {location.address}</p>
      )}
      {location.phone && (
        <p className="text-xs text-gray-600 mb-1">
          📞{' '}
          <a href={`tel:${location.phone}`} className="text-blue-600 hover:underline">
            {location.phone}
          </a>
        </p>
      )}

      {/* Links */}
      <div className="flex gap-3 mt-2">
        {location.web_url && (
          <a
            href={location.web_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-green-600 hover:underline font-medium"
          >
            TripAdvisor →
          </a>
        )}
        {location.website && (
          <a
            href={location.website.startsWith('http') ? location.website : `https://${location.website}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:underline"
          >
            Website →
          </a>
        )}
      </div>
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
  premiumLocations,
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

      {/* OSM POI markers (red) */}
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

      {/* Premium location markers (purple/gold) */}
      {premiumLocations && premiumLocations.map((location) => (
        <CircleMarker
          key={location.location_id}
          center={[location.lat, location.lon]}
          radius={10}
          pathOptions={{
            fillColor: '#9333ea',
            fillOpacity: 0.9,
            color: '#fbbf24',
            weight: 3,
          }}
        >
          <Popup>
            <PremiumLocationPopup location={location} />
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

export default Map;
