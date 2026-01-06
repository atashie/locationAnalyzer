import type { AnalysisResponse } from '../../types';

interface ResultsSummaryProps {
  result: AnalysisResponse | null;
}

export function ResultsSummary({ result }: ResultsSummaryProps) {
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
    </div>
  );
}

export default ResultsSummary;
