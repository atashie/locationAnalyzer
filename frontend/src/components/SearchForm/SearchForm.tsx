import { useState, useCallback } from 'react';
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
  type: 'poi',
  poi_type: '',
  location: '',
  mode: 'distance',
  value: 1,
});

export function SearchForm({ onSearch, isLoading = false }: SearchFormProps) {
  const [center, setCenter] = useState('Durham, NC');
  const [radius, setRadius] = useState(10);
  const [criteria, setCriteria] = useState<CriterionFormData[]>([]);

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const apiCriteria = convertToApiCriteria(criteria);
    onSearch(center, radius, apiCriteria);
  };

  // Count valid criteria
  const validCriteriaCount = criteria.filter((c) => {
    if (c.type === 'poi' && c.poi_type) return true;
    if (c.type === 'location' && c.location.trim()) return true;
    return false;
  }).length;

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
        />
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
            disabled={criteria.length >= 8 || poiTypesLoading}
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
              disabled={poiTypesLoading}
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

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-blue-600 text-white py-2.5 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Analyzing...
          </span>
        ) : (
          `Analyze Location${validCriteriaCount > 0 ? ` (${validCriteriaCount} criteria)` : ''}`
        )}
      </button>
    </form>
  );
}

export default SearchForm;
