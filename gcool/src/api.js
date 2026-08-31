const BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

async function safeFetch(path, opts) {
  try {
    const res = await fetch(`${BASE}${path}`, opts)
    if (res.status === 404) {
      return { __ok: false, __notFound: true, status: 404 }
    }
    if (!res.ok) {
      return { __ok: false, __notFound: false, status: res.status }
    }
    const data = await res.json()
    return { __ok: true, ...data }
  } catch (e) {
    return { __ok: false, __notFound: false, status: 0, __error: String(e) }
  }
}

export const api = {
  cities: () => safeFetch('/cities'),
  decision: (city) => safeFetch(`/decision?city=${city}`),
  liveRiskCached: (city) => safeFetch(`/live-risk-cached?city=${city}`),
  auditLog: (limit = 50) => safeFetch(`/audit-log?limit=${limit}`),
  heatAlerts: (city) => safeFetch(`/heat-alerts?city=${city}`),
  gridDemand: (city, hours = 24) => safeFetch(`/grid-demand?city=${city}&hours=${hours}`),
  riskSummary: (city) => safeFetch(`/risk-summary?city=${city}`),
  riskTimeseries: (city) => safeFetch(`/risk-timeseries?city=${city}`),
  envIntel: (city, temperatureC = 35) => safeFetch(`/env-intel?city=${city}&temperature_c=${temperatureC}`),
  envIntelAll: (temperatureC = 35) => safeFetch(`/env-intel-all?temperature_c=${temperatureC}`),
  heatmapTiles: (city, granularity = 100) => safeFetch(`/heatmap-tiles?city=${city}&granularity=${granularity}`),
  triggerRun: (city, date) => safeFetch(`/run?city=${city}${date ? `&date=${date}` : ''}`, { method: 'POST' }),
  runStatus: () => safeFetch('/run-status'),
  health: () => safeFetch('/health'),
}

export const FALLBACK_CITIES = [
  { id: 'phoenix_az', display_name: 'Phoenix, AZ', state: 'AZ', lat: 33.4484, lon: -112.0740, eia_ba_code: 'AZPS', eia_ba_name: 'Arizona Public Service' },
  { id: 'dallas_tx', display_name: 'Dallas, TX', state: 'TX', lat: 32.7767, lon: -96.7970, eia_ba_code: 'ERCO', eia_ba_name: 'ERCOT' },
  { id: 'vegas_nv', display_name: 'Las Vegas, NV', state: 'NV', lat: 36.1699, lon: -115.1398, eia_ba_code: 'NEVP', eia_ba_name: 'Nevada Power (NV Energy)' },
  { id: 'atlanta_ga', display_name: 'Atlanta, GA', state: 'GA', lat: 33.7490, lon: -84.3880, eia_ba_code: 'SOCO', eia_ba_name: 'Southern Company' },
  { id: 'sacramento_ca', display_name: 'Sacramento, CA', state: 'CA', lat: 38.5816, lon: -121.4944, eia_ba_code: 'CISO', eia_ba_name: 'California ISO' },
]
