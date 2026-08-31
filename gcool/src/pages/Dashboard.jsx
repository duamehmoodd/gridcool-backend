import { useEffect, useState } from 'react'
import { useCity } from '../CityContext'
import { api } from '../api'
import { usePolling } from '../usePolling'
import Header from '../components/Header'
import AlertBanner from '../components/AlertBanner'
import KpiStrip from '../components/KpiStrip'
import RiskQueue from '../components/RiskQueue'
import FleetMap from '../components/FleetMap'
import AssetDetail from '../components/AssetDetail'
import AuditLogMini from '../components/AuditLogMini'
import GridDemandChart from '../components/GridDemandChart'
import Footer from '../components/Footer'

export default function Dashboard() {
  const { cities, activeCity } = useCity()
  const [selected, setSelected] = useState(null)
  const [cityDecisions, setCityDecisions] = useState({})

  const { data: decision, loading: decisionLoading } = usePolling(
    () => api.decision(activeCity), [activeCity], 30000
  )
  const { data: heatAlert } = usePolling(() => api.heatAlerts(activeCity), [activeCity], 60000)
  const { data: demand } = usePolling(() => api.gridDemand(activeCity), [activeCity], 60000)
  const { data: liveCache } = usePolling(() => api.liveRiskCached(activeCity), [activeCity], 30000)
  const { data: audit } = usePolling(() => api.auditLog(20), [activeCity], 30000)
  const { data: envIntel } = usePolling(
    () => api.envIntel(activeCity, liveCache?.heat_index_c || 35),
    [activeCity, liveCache?.heat_index_c], 60000
  )

  // Keep all 5 cities' decisions refreshed for map coloring
  useEffect(() => {
    let cancelled = false
    async function loadAll() {
      const entries = await Promise.all(cities.map(async (c) => [c.id, await api.decision(c.id)]))
      if (!cancelled) setCityDecisions(Object.fromEntries(entries))
    }
    loadAll()
    const t = setInterval(loadAll, 45000)
    return () => { cancelled = true; clearInterval(t) }
  }, [cities])

  useEffect(() => { setSelected(null) }, [activeCity])

  const dataMode = decision?.data_mode
  const heatIndexC = liveCache?.heat_index_c ?? null

  return (
    <div className="page">
      <Header dataMode={dataMode} lastUpdated={new Date().toLocaleTimeString()} onRefresh={() => window.location.reload()} />
      <AlertBanner decision={decision} heatAlert={heatAlert} />
      <KpiStrip decision={decision} heatIndexC={heatIndexC} />

      <div className="dashboard-grid">
        <RiskQueue decision={decision} dataMode={dataMode} selected={selected} onSelect={setSelected} />

        <div className="center-col">
          <FleetMap cityDecisions={cityDecisions} />
          <GridDemandChart demand={demand} city={activeCity} />
        </div>

        <div className="right-col">
          <AssetDetail selected={selected} decision={decision} dataMode={dataMode} envIntel={envIntel} />
          <AuditLogMini entries={audit?.entries} />
        </div>
      </div>

      {decisionLoading && !decision && <div className="loading-overlay">Loading risk data…</div>}
      <Footer />
    </div>
  )
}
