import { useEffect, useMemo, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer } from 'recharts'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { useCity } from '../CityContext'
import { api } from '../api'

const LINE_COLORS = ['#00e5ff', '#ff1744', '#ff6d00', '#ffd600', '#00e676', '#b388ff']

function normalizeRows(raw) {
  // Handles either a flat array of {transformer, timestamp, pct_loaded}
  // or a grouped shape { transformer: [ {timestamp, pct_loaded}, ... ] }
  if (Array.isArray(raw)) return raw
  if (raw && typeof raw === 'object') {
    const rows = []
    for (const [transformer, points] of Object.entries(raw)) {
      if (Array.isArray(points)) {
        for (const p of points) rows.push({ transformer, timestamp: p.timestamp, pct_loaded: p.pct_loaded })
      }
    }
    return rows
  }
  return []
}

export default function RiskTimeline() {
  const { activeCity } = useCity()
  const [decision, setDecision] = useState(null)
  const [raw, setRaw] = useState(null)
  const [selectedXfmrs, setSelectedXfmrs] = useState([])

  useEffect(() => {
    api.decision(activeCity).then(setDecision)
    api.riskTimeseries(activeCity).then((res) => {
      setRaw(res)
    })
  }, [activeCity])

  const rows = useMemo(() => normalizeRows(raw?.rows || raw?.data || raw?.timeseries || raw), [raw])
  const allTransformers = useMemo(() => [...new Set(rows.map(r => r.transformer))], [rows])

  useEffect(() => {
    if (decision?.load_shed_priority?.length && selectedXfmrs.length === 0) {
      setSelectedXfmrs(decision.load_shed_priority.slice(0, 5))
    }
  }, [decision])

  const chartData = useMemo(() => {
    const byTime = {}
    for (const r of rows) {
      if (!selectedXfmrs.includes(r.transformer)) continue
      const t = r.timestamp
      if (!byTime[t]) byTime[t] = { timestamp: t }
      byTime[t][r.transformer] = r.pct_loaded
    }
    return Object.values(byTime).sort((a, b) => (a.timestamp > b.timestamp ? 1 : -1))
  }, [rows, selectedXfmrs])

  const isLive = decision?.data_mode === 'live'

  return (
    <div className="page">
      <Header />
      <div className="section-header">
        <h1>Risk Timeline — {activeCity}</h1>
        <p>Full-day %loading across selected transformers, historical mode</p>
      </div>

      {isLive ? (
        <div className="panel">
          <div className="empty-state">
            This city is currently in <strong>live</strong> data mode — a live snapshot is one instant in time,
            not a full-day sweep, so the historical timeline isn't available. Historical mode data (e.g. a
            specific past date) is required for this chart.
          </div>
        </div>
      ) : (
        <>
          <div className="panel">
            <div className="panel-header"><span>SELECT TRANSFORMERS</span></div>
            <div className="xfmr-multiselect">
              {allTransformers.map(t => (
                <label key={t} className="xfmr-check">
                  <input
                    type="checkbox"
                    checked={selectedXfmrs.includes(t)}
                    onChange={(e) => {
                      setSelectedXfmrs(prev =>
                        e.target.checked ? [...prev, t] : prev.filter(x => x !== t)
                      )
                    }}
                  />
                  {t}
                </label>
              ))}
              {allTransformers.length === 0 && <div className="empty-state">No timeseries data loaded yet.</div>}
            </div>
          </div>

          <div className="panel">
            <ResponsiveContainer width="100%" height={420}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="timestamp" stroke="#7f8aa3" fontSize={10} />
                <YAxis stroke="#7f8aa3" fontSize={10} unit="%" />
                <Tooltip contentStyle={{ background: '#10151f', border: '1px solid rgba(255,255,255,0.1)' }} />
                <Legend />
                <ReferenceLine y={100} stroke="#ff1744" strokeDasharray="6 4" label={{ value: '100% threshold', fill: '#ff1744', fontSize: 11 }} />
                {selectedXfmrs.map((t, i) => (
                  <Line key={t} type="monotone" dataKey={t} stroke={LINE_COLORS[i % LINE_COLORS.length]} dot={false} strokeWidth={2} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      <Footer />
    </div>
  )
}
