export const COLORS = {
  cyan: '#00e5ff',
  red: '#ff1744',
  orange: '#ff6d00',
  yellow: '#ffd600',
  green: '#00e676',
}

export function severityColor(severity) {
  switch ((severity || '').toLowerCase()) {
    case 'critical': return COLORS.red
    case 'high': return COLORS.orange
    case 'elevated': return COLORS.yellow
    default: return COLORS.green
  }
}

export function heatIndexColor(c) {
  if (c == null) return COLORS.cyan
  if (c >= 41) return COLORS.red
  if (c >= 35) return COLORS.orange
  if (c >= 27) return COLORS.yellow
  return COLORS.green
}

export function heatIndexLabel(c) {
  if (c == null) return 'Unknown'
  if (c >= 41) return 'Danger'
  if (c >= 35) return 'Extreme Caution'
  if (c >= 27) return 'Caution'
  return 'Normal'
}

export function aqiColor(aqi) {
  if (aqi == null) return COLORS.cyan
  if (aqi >= 150) return COLORS.red
  if (aqi >= 100) return COLORS.orange
  if (aqi >= 50) return COLORS.yellow
  return COLORS.green
}

export function cToF(c) {
  if (c == null) return null
  return Math.round((c * 9) / 5 + 32)
}

export function cityWorstSeverity(decision) {
  if (!decision || !decision.transformer_alerts || decision.transformer_alerts.length === 0) return 'none'
  const order = { critical: 3, high: 2, elevated: 1 }
  let worst = 'elevated'
  let worstScore = 0
  for (const a of decision.transformer_alerts) {
    const s = order[a.severity] || 0
    if (s > worstScore) { worstScore = s; worst = a.severity }
  }
  return worst
}
