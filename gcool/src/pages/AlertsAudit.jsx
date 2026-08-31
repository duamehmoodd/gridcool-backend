import { useEffect, useState } from 'react'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { useCity } from '../CityContext'
import { api } from '../api'
import { severityColor } from '../riskColors'

export default function AlertsAudit() {
  const { cities, activeCity } = useCity()
  const [alertsByCity, setAlertsByCity] = useState({})
  const [audit, setAudit] = useState(null)
  const [cityFilter, setCityFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  useEffect(() => {
    let cancelled = false
    Promise.all(cities.map(async c => [c.id, await api.heatAlerts(c.id)])).then(entries => {
      if (!cancelled) setAlertsByCity(Object.fromEntries(entries))
    })
    return () => { cancelled = true }
  }, [cities])

  useEffect(() => {
    api.auditLog(200).then(setAudit)
    const t = setInterval(() => api.auditLog(200).then(setAudit), 30000)
    return () => clearInterval(t)
  }, [])

  const entries = (audit?.entries || []).filter(e =>
    (cityFilter === 'all' || e.city === cityFilter) &&
    (statusFilter === 'all' || e.status === statusFilter)
  )

  return (
    <div className="page">
      <Header />
      <div className="section-header">
        <h1>Alerts & Audit</h1>
        <p>Live NOAA heat warnings per city, and the full auto-evaluation history</p>
      </div>

      <div className="panel">
        <div className="panel-header"><span>NOAA ALERTS</span></div>
        <div className="alert-card-grid">
          {cities.map(c => {
            const a = alertsByCity[c.id]
            const alert = a?.alerts?.[0]
            return (
              <div key={c.id} className={`noaa-card ${alert ? 'has-alert' : ''} ${c.id === activeCity ? 'active-city' : ''}`}>
                <div className="noaa-card-city">{c.display_name}</div>
                {alert ? (
                  <>
                    <div className="noaa-event" style={{ color: severityColor(alert.severity === 'Severe' ? 'critical' : 'high') }}>{alert.event}</div>
                    <div className="noaa-headline">{alert.headline}</div>
                    <div className="noaa-desc">{alert.description}</div>
                    <div className="noaa-dates">Effective: {alert.effective} · Expires: {alert.expires}</div>
                  </>
                ) : (
                  <div className="noaa-none">No active heat alert</div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header"><span>AUDIT LOG — FULL HISTORY</span></div>
        <div className="audit-filters">
          <select value={cityFilter} onChange={e => setCityFilter(e.target.value)}>
            <option value="all">All cities</option>
            {cities.map(c => <option key={c.id} value={c.id}>{c.display_name}</option>)}
          </select>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="all">All statuses</option>
            <option value="ok">OK</option>
            <option value="error">Error</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <table className="audit-table">
          <thead>
            <tr><th>Timestamp</th><th>City</th><th>Status</th><th>Heat Index</th><th>Multiplier</th><th>Top Transformer</th></tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr key={i}>
                <td>{e.logged_at ? new Date(e.logged_at).toLocaleString() : ''}</td>
                <td>{e.city}</td>
                <td className={e.status === 'ok' ? 'status-ok' : 'status-err'}>{e.status}</td>
                <td>{e.heat_index_c ?? '—'}</td>
                <td>{e.predicted_multiplier ?? '—'}</td>
                <td>{e.top_transformer ?? '—'}</td>
              </tr>
            ))}
            {entries.length === 0 && <tr><td colSpan={6} className="empty-state">No entries match this filter.</td></tr>}
          </tbody>
        </table>
      </div>

      <Footer />
    </div>
  )
}
