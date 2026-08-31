import { heatIndexColor } from '../riskColors'

export default function KpiStrip({ decision, heatIndexC }) {
  const alerts = (decision && decision.transformer_alerts) || []
  const critical = alerts.filter(a => a.severity === 'critical').length
  const avgLoad = alerts.length
    ? Math.round(alerts.reduce((s, a) => s + (a.peak_pct_loaded || 0), 0) / alerts.length)
    : null

  return (
    <div className="kpi-strip">
      <div className="kpi-card">
        <div className="kpi-label">AT-RISK ASSETS</div>
        <div className="kpi-value" style={{ color: '#00e5ff' }}>{alerts.length}</div>
      </div>
      <div className="kpi-card">
        <div className="kpi-label">CRITICAL</div>
        <div className="kpi-value" style={{ color: '#ff1744' }}>{critical}</div>
      </div>
      <div className="kpi-card">
        <div className="kpi-label">AVG PEAK LOADING</div>
        <div className="kpi-value">{avgLoad != null ? `${avgLoad}%` : '—'}</div>
      </div>
      <div className="kpi-card">
        <div className="kpi-label">HEAT INDEX</div>
        <div className="kpi-value" style={{ color: heatIndexColor(heatIndexC) }}>
          {heatIndexC != null ? `${heatIndexC.toFixed(1)}°C` : '—'}
        </div>
      </div>
    </div>
  )
}
