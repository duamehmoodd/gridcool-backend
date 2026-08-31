export default function AuditLogMini({ entries }) {
  const list = entries || []

  return (
    <div className="panel audit-mini">
      <div className="panel-header">
        <span>AUDIT LOG</span>
        <span className="pill-mini">AUTO-EVALUATOR</span>
      </div>
      {list.length === 0 && <div className="empty-state">No evaluation cycles logged yet.</div>}
      {list.slice(0, 10).map((e, i) => (
        <div className="audit-row" key={i}>
          <span className="audit-city">{e.city}</span>
          <span className="audit-meta">
            {e.status === 'ok'
              ? `${e.heat_index_c}°C · ${e.top_transformer || '—'}`
              : `error: ${e.note}`}
          </span>
          <span className="audit-time">{e.logged_at ? new Date(e.logged_at).toLocaleTimeString() : ''}</span>
        </div>
      ))}
    </div>
  )
}
