export default function AlertBanner({ decision, heatAlert }) {
  if (!decision || decision.__ok === false) return null

  const hasCritical = (decision.transformer_alerts || []).some(a => a.severity === 'critical')
  const parts = []
  if (decision.headline) parts.push(decision.headline)
  if (heatAlert && heatAlert.has_active_heat_alert && heatAlert.alerts?.[0]) {
    parts.push(`NOAA: ${heatAlert.alerts[0].event} — ${heatAlert.alerts[0].headline}`)
  }
  if (decision.heat_alert_message) parts.push(decision.heat_alert_message)

  if (parts.length === 0) return null

  return (
    <div className={`alert-banner ${hasCritical ? 'critical' : 'warn'}`}>
      <span className="alert-icon">⚠</span>
      <span className="alert-text">{parts.join('  |  ')}</span>
    </div>
  )
}
