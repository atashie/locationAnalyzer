import { useState } from 'react';

interface SearchFormProps {
  onSearch: (center: string, radiusMiles: number) => void;
  isLoading?: boolean;
}

export function SearchForm({ onSearch, isLoading = false }: SearchFormProps) {
  const [center, setCenter] = useState('Durham, NC');
  const [radius, setRadius] = useState(10);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(center, radius);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="center" className="block text-sm font-medium text-gray-700">
          Location
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

      {/* TODO: Add criteria builder here */}
      <div className="p-4 bg-gray-50 rounded-md">
        <p className="text-sm text-gray-500">
          Criteria builder coming soon...
        </p>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Analyzing...' : 'Analyze Location'}
      </button>
    </form>
  );
}

export default SearchForm;
