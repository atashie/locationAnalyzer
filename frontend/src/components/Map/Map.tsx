import { MapContainer, TileLayer, GeoJSON, Marker, Popup } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';

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
}

const DEFAULT_CENTER: LatLngExpression = [35.994, -78.899]; // Durham, NC
const DEFAULT_ZOOM = 11;

const TILE_URL = import.meta.env.VITE_MAP_TILE_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

export function Map({
  center = DEFAULT_CENTER as [number, number],
  zoom = DEFAULT_ZOOM,
  geojson,
  markerPosition,
  markerLabel,
}: MapProps) {
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

      {markerPosition && (
        <Marker position={markerPosition}>
          {markerLabel && <Popup>{markerLabel}</Popup>}
        </Marker>
      )}

      {geojson && (
        <GeoJSON
          data={geojson}
          style={{
            fillColor: '#3b82f6',
            fillOpacity: 0.3,
            color: '#1d4ed8',
            weight: 2,
          }}
        />
      )}
    </MapContainer>
  );
}

export default Map;
