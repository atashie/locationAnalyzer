import { useState, useEffect } from 'react'
import { Map } from './components/Map/Map'
import { SearchForm } from './components/SearchForm/SearchForm'
import { ResultsSummary } from './components/ResultsSummary/ResultsSummary'
import { PremiumSearchPanel } from './components/PremiumSearchPanel/PremiumSearchPanel'
import { useAnalysis } from './hooks/useAnalysis'
import { api } from './api/client'
import type { AnalysisResponse, Criterion, POIFeature, PremiumLocation } from './types'

function App() {
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const analysis = useAnalysis()

  // POI explorer state
  const [poiTypes, setPoiTypes] = useState<string[]>([])
  const [selectedPOIType, setSelectedPOIType] = useState<string>('')
  const [pois, setPois] = useState<POIFeature[]>([])
  const [isLoadingPOIs, setIsLoadingPOIs] = useState(false)

  // Premium search state
  const [premiumLocations, setPremiumLocations] = useState<PremiumLocation[]>([])

  // Fetch POI types on mount
  useEffect(() => {
    api.getPOITypes()
      .then((response) => {
        setPoiTypes(response.poi_types.map((pt) => pt.name))
      })
      .catch((err) => {
        console.error('Failed to fetch POI types:', err)
      })
  }, [])

  const handleSearch = async (center: string, radiusMiles: number, criteria: Criterion[]) => {
    setError(null)
    // Clear POI and premium state when starting a new search
    setPois([])
    setSelectedPOIType('')
    setPremiumLocations([])

    try {
      const response = await analysis.mutateAsync({
        center,
        radius_miles: radiusMiles,
        criteria,
      })
      setResult(response)
    } catch (err) {
      console.error('Analysis failed:', err)
      const errorMessage = err instanceof Error ? err.message : 'Analysis failed. Please try again.'
      setError(errorMessage)
      setResult(null)
    }
  }

  const handlePOITypeSelect = async (poiType: string) => {
    setSelectedPOIType(poiType)

    if (!poiType || !result?.geojson) {
      setPois([])
      return
    }

    setIsLoadingPOIs(true)
    try {
      const response = await api.queryPOIs(result.geojson, poiType)
      setPois(response.pois)
    } catch (err) {
      console.error('POI query failed:', err)
      setPois([])
    } finally {
      setIsLoadingPOIs(false)
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

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <h3 className="text-sm font-medium text-red-800">Analysis Error</h3>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Results</h2>
              <ResultsSummary
                result={result}
                poiTypes={poiTypes}
                selectedPOIType={selectedPOIType}
                onPOITypeSelect={handlePOITypeSelect}
                pois={pois}
                isLoadingPOIs={isLoadingPOIs}
              />
            </div>
          </div>

          {/* Map */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white rounded-lg shadow h-[600px] overflow-hidden">
              <Map
                center={result ? [result.center_lat, result.center_lon] : undefined}
                geojson={result?.geojson}
                markerPosition={result ? [result.center_lat, result.center_lon] : undefined}
                markerLabel={result?.center}
                pois={pois}
                premiumLocations={premiumLocations}
              />
            </div>

            {/* Premium Search Panel */}
            <PremiumSearchPanel
              geojson={result?.geojson || null}
              onResultsLoaded={setPremiumLocations}
              onClear={() => setPremiumLocations([])}
            />
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
