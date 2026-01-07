import { useState } from 'react';
import type {
  TripAdvisorCategory,
  PremiumLocation,
  PremiumSearchResponse
} from '../../types';
import { TRIPADVISOR_SUBCATEGORIES } from '../../types';
import { api } from '../../api/client';

interface PremiumSearchPanelProps {
  geojson: GeoJSON.FeatureCollection | null;
  onResultsLoaded: (locations: PremiumLocation[]) => void;
  onClear: () => void;
}

export function PremiumSearchPanel({
  geojson,
  onResultsLoaded,
  onClear
}: PremiumSearchPanelProps) {
  const [isPremiumEnabled, setIsPremiumEnabled] = useState(false);
  const [provider, setProvider] = useState<'tripadvisor' | 'xyz'>('tripadvisor');
  const [category, setCategory] = useState<TripAdvisorCategory>('restaurants');
  const [subcategory, setSubcategory] = useState<string>('');
  const [maxLocations, setMaxLocations] = useState(10);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PremiumSearchResponse | null>(null);

  const subcategories = TRIPADVISOR_SUBCATEGORIES[category] || [];

  const handleCategoryChange = (newCategory: TripAdvisorCategory) => {
    setCategory(newCategory);
    setSubcategory(''); // Reset subcategory when category changes
  };

  const handleSearch = async () => {
    if (!geojson) {
      setError('Run an analysis first to get search area');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.premiumSearch({
        geojson,
        category,
        subcategory: subcategory || undefined,
        max_locations: maxLocations,
      });

      setResult(response);
      onResultsLoaded(response.locations);
    } catch (err) {
      console.error('Premium search failed:', err);
      const message = err instanceof Error ? err.message : 'Search failed';
      setError(message);
      onResultsLoaded([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearResults = () => {
    setResult(null);
    onClear();
  };

  const formatSubcategory = (sub: string) => {
    return sub.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Premium Search</h2>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={isPremiumEnabled}
            onChange={(e) => {
              setIsPremiumEnabled(e.target.checked);
              if (!e.target.checked) {
                handleClearResults();
              }
            }}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
          <span className="ms-3 text-sm font-medium text-gray-700">Premium</span>
        </label>
      </div>

      {isPremiumEnabled && (
        <div className="space-y-4">
          {/* Provider Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Provider
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setProvider('tripadvisor')}
                className={`px-3 py-2 text-sm rounded-md flex-1 transition-colors ${
                  provider === 'tripadvisor'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                TripAdvisor
              </button>
              <button
                disabled
                className="px-3 py-2 text-sm rounded-md flex-1 bg-gray-100 text-gray-400 cursor-not-allowed"
                title="Coming soon"
              >
                XYZ (Coming Soon)
              </button>
            </div>
          </div>

          {/* Category Dropdown */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => handleCategoryChange(e.target.value as TripAdvisorCategory)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            >
              <option value="restaurants">Restaurants</option>
              <option value="hotels">Hotels</option>
              <option value="attractions">Attractions</option>
              <option value="geos">Geographic Areas</option>
            </select>
          </div>

          {/* Subcategory Dropdown */}
          {subcategories.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subcategory (Optional)
              </label>
              <select
                value={subcategory}
                onChange={(e) => setSubcategory(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              >
                <option value="">All {category}</option>
                {subcategories.map((sub) => (
                  <option key={sub} value={sub}>
                    {formatSubcategory(sub)}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Max Locations Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Locations to Show
            </label>
            <input
              type="number"
              min={1}
              max={50}
              value={maxLocations}
              onChange={(e) => setMaxLocations(Math.min(50, Math.max(1, parseInt(e.target.value) || 10)))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Search Button */}
          <button
            onClick={handleSearch}
            disabled={isLoading || !geojson}
            className="w-full px-4 py-2.5 bg-purple-600 text-white rounded-md font-medium hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:bg-purple-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
          >
            {isLoading ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                Searching...
              </>
            ) : (
              'Run Premium Search'
            )}
          </button>

          {/* Results Summary */}
          {result && (
            <div className="mt-4 p-3 bg-purple-50 border border-purple-200 rounded-md">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-purple-800">
                  {result.total_found} location{result.total_found !== 1 ? 's' : ''} found
                </span>
                <button
                  onClick={handleClearResults}
                  className="text-xs text-purple-600 hover:underline"
                >
                  Clear
                </button>
              </div>
              <p className="text-xs text-purple-600">
                Searched {result.centroids_searched} area{result.centroids_searched !== 1 ? 's' : ''} |{' '}
                {result.api_calls_used} API call{result.api_calls_used !== 1 ? 's' : ''} used
              </p>
            </div>
          )}

          {/* API Usage Warning */}
          <p className="text-xs text-gray-500 italic">
            Premium search uses TripAdvisor API (5000 calls/month limit).
            Results are cached to reduce usage.
          </p>
        </div>
      )}

      {!isPremiumEnabled && (
        <p className="text-sm text-gray-500">
          Enable Premium to search TripAdvisor for detailed business information including ratings, reviews, and photos.
        </p>
      )}
    </div>
  );
}

export default PremiumSearchPanel;
