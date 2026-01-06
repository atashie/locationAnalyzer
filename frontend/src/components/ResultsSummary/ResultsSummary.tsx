import type { AnalysisResponse, POIFeature } from '../../types';

interface ResultsSummaryProps {
  result: AnalysisResponse | null;
  poiTypes?: string[];
  selectedPOIType?: string;
  onPOITypeSelect?: (type: string) => void;
  pois?: POIFeature[];
  isLoadingPOIs?: boolean;
}

export function ResultsSummary({
  result,
  poiTypes = [],
  selectedPOIType = '',
  onPOITypeSelect,
  pois,
  isLoadingPOIs = false,
}: ResultsSummaryProps) {
  if (!result) {
    return (
      <div className="p-4 bg-gray-50 rounded-md">
        <p className="text-sm text-gray-500">
          Run an analysis to see results
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 p-3 rounded-md">
          <p className="text-xs text-blue-600 uppercase font-medium">Final Area</p>
          <p className="text-2xl font-bold text-blue-900">
            {result.final_area_sq_miles.toFixed(1)} mi²
          </p>
        </div>
        <div className="bg-green-50 p-3 rounded-md">
          <p className="text-xs text-green-600 uppercase font-medium">Reduction</p>
          <p className="text-2xl font-bold text-green-900">
            {result.area_reduction_percent.toFixed(0)}%
          </p>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Applied Criteria</h3>
        <ul className="space-y-2">
          {result.criteria_applied.map((criterion, index) => (
            <li
              key={index}
              className="flex justify-between items-center p-2 bg-gray-50 rounded"
            >
              <span className="text-sm font-medium">{criterion.name}</span>
              <span className="text-xs text-gray-500">{criterion.description}</span>
            </li>
          ))}
        </ul>
      </div>

      {result.criteria_applied.length === 0 && (
        <p className="text-sm text-gray-500">
          No criteria applied. Add criteria to narrow down the search area.
        </p>
      )}

      {/* POI Explorer Section */}
      {poiTypes.length > 0 && onPOITypeSelect && (
        <div className="border-t pt-4 mt-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            Explore Businesses in This Area
          </h3>
          <select
            value={selectedPOIType}
            onChange={(e) => onPOITypeSelect(e.target.value)}
            disabled={isLoadingPOIs}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            <option value="">Select a category...</option>
            {poiTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>

          {isLoadingPOIs && (
            <div className="mt-3 flex items-center gap-2 text-sm text-gray-600">
              <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              <span>Searching for businesses...</span>
            </div>
          )}

          {pois && pois.length > 0 && !isLoadingPOIs && (
            <div className="mt-3">
              <p className="text-sm font-medium text-gray-700 mb-2">
                {pois.length} {selectedPOIType} found
              </p>
              <ul className="max-h-48 overflow-y-auto space-y-1 border rounded-md">
                {pois.map((poi) => (
                  <li
                    key={poi.id}
                    className="px-3 py-2 text-sm border-b last:border-b-0 hover:bg-gray-50"
                  >
                    <div className="font-medium">{poi.name}</div>
                    {poi.address && (
                      <div className="text-xs text-gray-500">{poi.address}</div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {pois && pois.length === 0 && selectedPOIType && !isLoadingPOIs && (
            <p className="mt-3 text-sm text-gray-500">
              No {selectedPOIType} found in this area.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default ResultsSummary;
