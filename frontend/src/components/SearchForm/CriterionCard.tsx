import type { CriterionFormData, CriterionType, TravelMode, POIType } from '../../types';

interface CriterionCardProps {
  criterion: CriterionFormData;
  index: number;
  poiTypes: POIType[];
  onChange: (id: string, updates: Partial<CriterionFormData>) => void;
  onRemove: (id: string) => void;
}

const TRAVEL_MODES: { value: TravelMode; label: string; unit: string }[] = [
  { value: 'distance', label: 'Distance', unit: 'miles' },
  { value: 'walk', label: 'Walking', unit: 'minutes' },
  { value: 'bike', label: 'Biking', unit: 'minutes' },
  { value: 'drive', label: 'Driving', unit: 'minutes' },
];

export function CriterionCard({
  criterion,
  index,
  poiTypes,
  onChange,
  onRemove,
}: CriterionCardProps) {
  const currentMode = TRAVEL_MODES.find((m) => m.value === criterion.mode);

  return (
    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 space-y-3">
      {/* Header with remove button */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">
          Criterion {index + 1}
        </span>
        <button
          type="button"
          onClick={() => onRemove(criterion.id)}
          className="text-gray-400 hover:text-red-500 transition-colors"
          aria-label="Remove criterion"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Type selector */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onChange(criterion.id, { type: 'poi' as CriterionType })}
          className={`flex-1 py-1.5 px-3 text-sm rounded-md transition-colors ${
            criterion.type === 'poi'
              ? 'bg-blue-600 text-white'
              : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
          }`}
        >
          Amenity Type
        </button>
        <button
          type="button"
          onClick={() => onChange(criterion.id, { type: 'location' as CriterionType })}
          className={`flex-1 py-1.5 px-3 text-sm rounded-md transition-colors ${
            criterion.type === 'location'
              ? 'bg-blue-600 text-white'
              : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
          }`}
        >
          Specific Place
        </button>
      </div>

      {/* POI Type or Location input */}
      {criterion.type === 'poi' ? (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Amenity Type
          </label>
          <select
            value={criterion.poi_type}
            onChange={(e) => onChange(criterion.id, { poi_type: e.target.value })}
            className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm px-3 py-2 border"
          >
            <option value="">Select an amenity...</option>
            {poiTypes.map((poi) => (
              <option key={poi.name} value={poi.name}>
                {poi.name}
              </option>
            ))}
          </select>
        </div>
      ) : (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Place or Address
          </label>
          <input
            type="text"
            value={criterion.location}
            onChange={(e) => onChange(criterion.id, { location: e.target.value })}
            placeholder="e.g., Duke University, Durham, NC"
            className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm px-3 py-2 border"
          />
        </div>
      )}

      {/* Mode and Value */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Measure by
          </label>
          <select
            value={criterion.mode}
            onChange={(e) => onChange(criterion.id, { mode: e.target.value as TravelMode })}
            className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm px-3 py-2 border"
          >
            {TRAVEL_MODES.map((mode) => (
              <option key={mode.value} value={mode.value}>
                {mode.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Max {currentMode?.unit || 'value'}
          </label>
          <input
            type="number"
            value={criterion.value}
            onChange={(e) => onChange(criterion.id, { value: Number(e.target.value) })}
            min={criterion.mode === 'distance' ? 0.1 : 1}
            max={criterion.mode === 'distance' ? 25 : 60}
            step={criterion.mode === 'distance' ? 0.1 : 1}
            className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm px-3 py-2 border"
          />
        </div>
      </div>

      {/* Summary line */}
      <div className="text-xs text-gray-500 pt-1 border-t border-gray-200">
        {criterion.type === 'poi' && criterion.poi_type ? (
          <>Within {criterion.value} {currentMode?.unit} {criterion.mode !== 'distance' ? `${criterion.mode}` : ''} of a <strong>{criterion.poi_type}</strong></>
        ) : criterion.type === 'location' && criterion.location ? (
          <>Within {criterion.value} {currentMode?.unit} {criterion.mode !== 'distance' ? `${criterion.mode}` : ''} of <strong>{criterion.location}</strong></>
        ) : (
          <span className="italic">Configure this criterion...</span>
        )}
      </div>
    </div>
  );
}

export default CriterionCard;
