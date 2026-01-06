import { useState } from 'react'
import { Map } from './components/Map/Map'
import { SearchForm } from './components/SearchForm/SearchForm'
import { ResultsSummary } from './components/ResultsSummary/ResultsSummary'
import { useAnalysis } from './hooks/useAnalysis'
import type { AnalysisResponse } from './types'

function App() {
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const analysis = useAnalysis()

  const handleSearch = async (center: string, radiusMiles: number) => {
    try {
      const response = await analysis.mutateAsync({
        center,
        radius_miles: radiusMiles,
        criteria: [], // TODO: Add criteria from form
      })
      setResult(response)
    } catch (error) {
      console.error('Analysis failed:', error)
      // TODO: Add proper error handling UI
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Distance Finder</h1>
          <p className="text-sm text-gray-500">
            Find locations based on proximity to amenities and places
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar - Search Form */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Search Parameters</h2>
              <SearchForm
                onSearch={handleSearch}
                isLoading={analysis.isPending}
              />
            </div>

            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Results</h2>
              <ResultsSummary result={result} />
            </div>
          </div>

          {/* Map */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow h-[600px] overflow-hidden">
              <Map
                center={result ? [result.center_lat, result.center_lon] : undefined}
                geojson={result?.geojson}
                markerPosition={result ? [result.center_lat, result.center_lon] : undefined}
                markerLabel={result?.center}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
          Distance Finder MVP - Powered by OpenStreetMap
        </div>
      </footer>
    </div>
  )
}

export default App
