import { useState, useCallback, useMemo } from 'react';
import { CriterionCard } from './CriterionCard';
import { usePOITypes } from '../../hooks/useAnalysis';
import type { CriterionFormData, Criterion } from '../../types';

interface SearchFormProps {
  onSearch: (center: string, radiusMiles: number, criteria: Criterion[]) => void;
  isLoading?: boolean;
}

// Generate unique IDs for criteria
let criterionIdCounter = 0;
const generateId = () => `criterion-${++criterionIdCounter}`;

// Default values for new criteria
const createDefaultCriterion = (): CriterionFormData => ({
  id: generateId(),
  type: 'location',
  poi_type: '',
  location: '',
  mode: 'distance',
  value: 1,
  complexQuery: false,
});

// High-density POI types that result in slow queries
const HIGH_DENSITY_POI_TYPES = [
  'Bus Stop',
  'Restaurant',
  'Coffee Shop',
  'Bar',
  'Gas Station',
];

// Estimate query time based on criteria and radius
function estimateQueryTime(
  criteria: CriterionFormData[],
  radiusMiles: number
): { seconds: number; warning: string | null } {
  // Base time for geocoding center
  let baseTime = 2;

  // Count POI criteria (these are slow when uncached)
  const poiCriteria = criteria.filter(c => c.type === 'poi' && c.poi_type);
  const locationCriteria = criteria.filter(c => c.type === 'location' && c.location.trim());

  // Location criteria are fast (single geocode each)
  baseTime += locationCriteria.length * 1;

  // POI criteria are slow - estimate based on density and radius
  let slowWarning: string | null = null;

  for (const criterion of poiCriteria) {
    const isHighDensity = HIGH_DENSITY_POI_TYPES.includes(criterion.poi_type);
    const radiusFactor = Math.pow(radiusMiles / 5, 1.5); // Larger radius = much slower

    if (isHighDensity) {
      // High-density POIs can take 30-120+ seconds
      baseTime += 30 * radiusFactor;
      slowWarning = `"${criterion.poi_type}" has many locations - this may take 1-3 minutes`;
    } else {
      // Regular POIs typically take 5-30 seconds
      baseTime += 10 * radiusFactor;
    }
  }

  // Multiple POI criteria compound the time
  if (poiCriteria.length > 2) {
    slowWarning = `${poiCriteria.length} amenity criteria - this may take several minutes`;
  }

  // Large radius warning
  if (radiusMiles > 15 && poiCriteria.length > 0) {
    slowWarning = `Large search radius (${radiusMiles} mi) with amenity criteria - consider reducing radius`;
  }

  return { seconds: Math.round(baseTime), warning: slowWarning };
}

export function SearchForm({ onSearch, isLoading = false }: SearchFormProps) {
  const [center, setCenter] = useState('Durham, NC');
  const [radius, setRadius] = useState(10);
  const [criteria, setCriteria] = useState<CriterionFormData[]>([]);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Fetch POI types from backend
  const { data: poiTypesData, isLoading: poiTypesLoading } = usePOITypes();
  const poiTypes = poiTypesData?.poi_types || [];

  // Add new criterion
  const handleAddCriterion = useCallback(() => {
    if (criteria.length >= 8) return; // Max 8 criteria
    setCriteria((prev) => [...prev, createDefaultCriterion()]);
  }, [criteria.length]);

  // Update criterion
  const handleUpdateCriterion = useCallback((id: string, updates: Partial<CriterionFormData>) => {
    setCriteria((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...updates } : c))
    );
  }, []);

  // Remove criterion
  const handleRemoveCriterion = useCallback((id: string) => {
    setCriteria((prev) => prev.filter((c) => c.id !== id));
  }, []);

  // Convert form data to API format
  const convertToApiCriteria = (formCriteria: CriterionFormData[]): Criterion[] => {
    return formCriteria
      .filter((c) => {
        // Only include valid criteria
        if (c.type === 'poi' && !c.poi_type) return false;
        if (c.type === 'location' && !c.location.trim()) return false;
        return true;
      })
      .map((c) => ({
        type: c.type,
        poi_type: c.type === 'poi' ? c.poi_type : undefined,
        location: c.type === 'location' ? c.location : undefined,
        mode: c.mode,
        value: c.value,
      }));
  };

  // Elapsed time counter
  const startElapsedTimer = useCallback(() => {
    setElapsedTime(0);
    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);
    return interval;
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const apiCriteria = convertToApiCriteria(criteria);
    const timer = startElapsedTimer();

    // Store timer reference to clear later
    (window as unknown as { _analysisTimer?: ReturnType<typeof setInterval> })._analysisTimer = timer;

    onSearch(center, radius, apiCriteria);
  };

  // Clean up timer when loading stops
  useMemo(() => {
    if (!isLoading) {
      const timer = (window as unknown as { _analysisTimer?: ReturnType<typeof setInterval> })._analysisTimer;
      if (timer) {
        clearInterval(timer);
        delete (window as unknown as { _analysisTimer?: ReturnType<typeof setInterval> })._analysisTimer;
      }
    }
  }, [isLoading]);

  // Count valid criteria
  const validCriteriaCount = criteria.filter((c) => {
    if (c.type === 'poi' && c.poi_type) return true;
    if (c.type === 'location' && c.location.trim()) return true;
    return false;
  }).length;

  // Estimate time and get warnings
  const { seconds: estimatedSeconds, warning } = useMemo(
    () => estimateQueryTime(criteria, radius),
    [criteria, radius]
  );

  // Format time display
  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Center Location */}
      <div>
        <label htmlFor="center" className="block text-sm font-medium text-gray-700">
          Search Center
        </label>
        <input
          type="text"
          id="center"
          value={center}
          onChange={(e) => setCenter(e.target.value)}
          placeholder="City, State or Address"
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 px-3 py-2 border"
          disabled={isLoading}
        />
      </div>

      {/* Search Radius */}
      <div>
        <label htmlFor="radius" className="block text-sm font-medium text-gray-700">
          Search Radius (miles)
        </label>
        <input
          type="number"
          id="radius"
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
          min={1}
          max={25}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 px-3 py-2 border"
          disabled={isLoading}
        />
        {radius > 15 && (
          <p className="text-xs text-amber-600 mt-1">
            Larger radius may result in slower queries
          </p>
        )}
      </div>

      {/* Criteria Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-gray-700">
            Proximity Criteria
            {criteria.length > 0 && (
              <span className="ml-2 text-xs text-gray-500">
                ({validCriteriaCount} of {criteria.length} valid)
              </span>
            )}
          </label>
          <button
            type="button"
            onClick={handleAddCriterion}
            disabled={criteria.length >= 8 || poiTypesLoading || isLoading}
            className="text-sm text-blue-600 hover:text-blue-700 disabled:text-gray-400 disabled:cursor-not-allowed flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Criterion
          </button>
        </div>

        {/* Criteria List */}
        {criteria.length === 0 ? (
          <div className="p-4 bg-gray-50 rounded-md text-center">
            <p className="text-sm text-gray-500 mb-2">
              No criteria added yet
            </p>
            <button
              type="button"
              onClick={handleAddCriterion}
              disabled={poiTypesLoading || isLoading}
              className="text-sm text-blue-600 hover:text-blue-700 underline"
            >
              {poiTypesLoading ? 'Loading...' : 'Add your first criterion'}
            </button>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {criteria.map((criterion, index) => (
              <CriterionCard
                key={criterion.id}
                criterion={criterion}
                index={index}
                poiTypes={poiTypes}
                onChange={handleUpdateCriterion}
                onRemove={handleRemoveCriterion}
              />
            ))}
          </div>
        )}

        {/* Criteria limit warning */}
        {criteria.length >= 8 && (
          <p className="text-xs text-amber-600">
            Maximum of 8 criteria reached
          </p>
        )}
      </div>

      {/* Performance Warning */}
      {warning && !isLoading && (
        <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-amber-800">Slow Query Warning</p>
              <p className="text-xs text-amber-700 mt-0.5">{warning}</p>
              <p className="text-xs text-amber-600 mt-1">
                Tip: Use "Specific Place" criteria when possible - they're much faster than amenity searches
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Estimated Time (when not loading) */}
      {validCriteriaCount > 0 && !isLoading && (
        <div className="text-xs text-gray-500 text-center">
          Estimated time: {formatTime(estimatedSeconds)}
          {estimatedSeconds > 30 && ' (first run may be slower)'}
        </div>
      )}

      {/* Submit Button with Loading State */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-blue-600 text-white py-2.5 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
      >
        {isLoading ? (
          <span className="flex flex-col items-center justify-center gap-1">
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing... ({formatTime(elapsedTime)})
            </span>
            <span className="text-xs opacity-75">
              {elapsedTime > 30 ? 'Querying OpenStreetMap - please wait...' : 'Processing criteria...'}
            </span>
          </span>
        ) : (
          `Analyze Location${validCriteriaCount > 0 ? ` (${validCriteriaCount} criteria)` : ''}`
        )}
      </button>

      {/* Loading Progress Info */}
      {isLoading && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-blue-800">Analysis in Progress</p>
              <p className="text-xs text-blue-700 mt-0.5">
                {elapsedTime < 10 && 'Geocoding location...'}
                {elapsedTime >= 10 && elapsedTime < 30 && 'Querying points of interest...'}
                {elapsedTime >= 30 && elapsedTime < 60 && 'Processing large dataset - almost there...'}
                {elapsedTime >= 60 && 'This is taking longer than usual. Complex queries may take several minutes.'}
              </p>
            </div>
          </div>
        </div>
      )}
    </form>
  );
}

export default SearchForm;
