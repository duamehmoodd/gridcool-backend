import { useState } from 'react'
import { severityColor } from '../riskColors'

const FILTERS = ['All', 'Critical', 'High', 'Elevated']

export default function RiskQueue({ decision, dataMode, selected, onSelect }) {
  const [filter, setFilter] = useState('All')
  const alerts = (decision && decision.transformer_alerts) || []
  const visible = filter === 'All' ? alerts : alerts.filter(a => a.severity === filter.toLowerCase())

  return (
    <div className="panel risk-queue">
      <div className="panel-header">
        <span>LIVE RISK QUEUE</span>
        <span className="pill">{alerts.length} FLAGGED</span>
      </div>

      <div className="filter-chips">
        {FILTERS.map(f => (
          <button key={f} className={`chip ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
      </div>

      <div className="queue-list">
        {visible.length === 0 && <div className="empty-state">No transformers match this filter.</div>}
        {visible.map((a) => (
          <div
            key={a.transformer}
            className={`queue-card ${selected === a.transformer ? 'selected' : ''}`}
            style={{ borderLeftColor: severityColor(a.severity) }}
            onClick={() => onSelect(a.transformer)}
          >
            <div className="queue-card-top">
              <span className="queue-id">{a.transformer}</span>
              <span className="queue-pct" style={{ color: severityColor(a.severity) }}>
                {a.peak_pct_loaded}%
              </span>
            </div>
            <div className="queue-sub">
              {dataMode === 'live' ? 'live snapshot' : a.peak_time} · DEMO
            </div>
            <div className={`severity-tag sev-${a.severity}`}>{a.severity?.toUpperCase()}</div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${Math.min(a.peak_pct_loaded, 200) / 2}%`, background: severityColor(a.severity) }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
