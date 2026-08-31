import { severityColor } from '../riskColors'

export default function AssetDetail({ selected, decision, dataMode, envIntel }) {
  const alert = (decision?.transformer_alerts || []).find(a => a.transformer === selected)

  if (!alert) {
    return (
      <div className="panel asset-detail">
        <div className="panel-header"><span>ASSET DETAIL</span></div>
        <div className="empty-state">Select a transformer from the Live Risk Queue to see details.</div>
      </div>
    )
  }

  const color = severityColor(alert.severity)

  return (
    <div className="panel asset-detail">
      <div className="panel-header"><span>ASSET DETAIL</span></div>
      <div className="asset-id">{alert.transformer}</div>
      <div className="demo-tag">⚠ DEMO / SIMULATED ASSET</div>

      <div className="asset-score" style={{ borderColor: color }}>
        <div className="asset-score-value" style={{ color }}>{alert.peak_pct_loaded}%</div>
        <div className="asset-score-label" style={{ color }}>{alert.severity?.toUpperCase()} RISK</div>
        <div className="asset-score-sub">of rated capacity</div>
      </div>

      <div className="detail-section">
        <div className="detail-title">TIMING</div>
        <div className="detail-row"><span>Peak time</span><span>{dataMode === 'live' ? 'live snapshot' : (alert.peak_time || '—')}</span></div>
        <div className="detail-row"><span>Hours over threshold</span><span>{dataMode === 'live' ? 'n/a (live mode)' : (alert.hours_over_threshold ?? '—')}</span></div>
        <div className="detail-row"><span>Data mode</span><span className={dataMode === 'live' ? 'mode-live' : 'mode-hist'}>{dataMode}</span></div>
      </div>

      {envIntel && envIntel.status === 'ok' && (
        <div className="detail-section">
          <div className="detail-title">HEAT INTELLIGENCE <span className="pill-mini">FORTYGUARD</span></div>
          <div className="detail-row"><span>Heat Index</span><span>{envIntel.heat_index_c?.toFixed?.(1)}°C</span></div>
          <div className="detail-row"><span>Predicted Multiplier</span><span>{decision?.data_mode === 'live' ? '' : ''}{envIntel.predicted_multiplier ? `${envIntel.predicted_multiplier}x` : ''}</span></div>
          <div className="detail-row"><span>Wet Bulb</span><span>{envIntel.wet_bulb_c?.toFixed?.(1)}°C</span></div>
          <div className="detail-row"><span>Humidity</span><span>{envIntel.humidity_pct}%</span></div>
        </div>
      )}

      <div className="detail-section">
        <div className="detail-title">ALERT MESSAGE</div>
        <div className="alert-message">{alert.message}</div>
      </div>
    </div>
  )
}
