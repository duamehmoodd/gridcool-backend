import { createContext, useContext, useEffect, useState } from 'react'
import { api, FALLBACK_CITIES } from './api'

const CityContext = createContext(null)

export function CityProvider({ children }) {
  const [cities, setCities] = useState(FALLBACK_CITIES)
  const [activeCity, setActiveCity] = useState(FALLBACK_CITIES[0].id)

  useEffect(() => {
    api.cities().then((res) => {
      if (res.__ok && Array.isArray(res.cities) && res.cities.length > 0) {
        setCities(res.cities)
      }
    })
  }, [])

  const activeCityMeta = cities.find((c) => c.id === activeCity) || cities[0]

  return (
    <CityContext.Provider value={{ cities, activeCity, setActiveCity, activeCityMeta }}>
      {children}
    </CityContext.Provider>
  )
}

export function useCity() {
  const ctx = useContext(CityContext)
  if (!ctx) throw new Error('useCity must be used within CityProvider')
  return ctx
}
