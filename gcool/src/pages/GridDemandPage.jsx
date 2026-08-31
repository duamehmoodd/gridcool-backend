import { useEffect, useMemo, useState } from 'react'
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { useCity } from '../CityContext'
import { api } from '../api'

function normalizeRows(raw) {
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

export default function GridDemandPage() {
  const { activeCity } = useCity()
  const [demand, setDemand] = useState(null)
  const [timeseries, setTimeseries] = useState(null)

  useEffect(() => {
    api.gridDemand(activeCity, 24).then(setDemand)
    api.riskTimeseries(activeCity).then(setTimeseries)
  }, [activeCity])

  const rows = useMemo(() => normalizeRows(timeseries?.rows || timeseries?.data || timeseries), [timeseries])

  const worstAgg = useMemo(() => {
    const byTime = {}
    for (const r of rows) {
      const t = r.timestamp
      if (!byTime[t]) byTime[t] = []
      byTime[t].push(r.pct_loaded)
    }
    return Object.entries(byTime).map(([timestamp, vals]) => ({
      timestamp, worst_pct: Math.max(...vals),
    })).sort((a, b) => (a.timestamp > b.timestamp ? 1 : -1))
  }, [rows])

  const demandRows = demand?.status === 'ok' ? demand.demand_mwh.map(d => ({
    period: d.period, mwh: Number(d.value_mwh),
  })) : []

  const combined = useMemo(() => {
    const map = {}
    for (const d of demandRows) {
      const key = d.period.slice(-2)
      map[key] = { time: key, mwh: d.mwh }
    }
    for (const w of worstAgg) {
      const key = (w.timestamp || '').slice(11, 13) || w.timestamp
      if (!map[key]) map[key] = { time: key }
      map[key].worst_pct = w.worst_pct
    }
    return Object.values(map).sort((a, b) => (a.time > b.time ? 1 : -1))
  }, [demandRows, worstAgg])

  const peakDemand = demandRows.length ? demandRows.reduce((m, d) => (d.mwh > m.mwh ? d : m), demandRows[0]) : null
  const peakRisk = worstAgg.length ? worstAgg.reduce((m, w) => (w.worst_pct > m.worst_pct ? w : m), worstAgg[0]) : null

  return (
    <div className="page">
      <Header />
      <div className="section-header">
        <h1>Grid Demand & Correlation — {activeCity}</h1>
        <p>EIA regional demand overlaid with worst-case transformer loading across the same day</p>
      </div>

      <div className="panel">
        <ResponsiveContainer width="100%" height={420}>
          <ComposedChart data={combined}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="time" stroke="#7f8aa3" fontSize={10} />
            <YAxis yAxisId="left" stroke="#00e5ff" fontSize={10} label={{ value: 'MWh', angle: -90, position: 'insideLeft', fill: '#00e5ff' }} />
            <YAxis yAxisId="right" orientation="right" stroke="#ff6d00" fontSize={10} unit="%" label={{ value: '% loaded', angle: 90, position: 'insideRight', fill: '#ff6d00' }} />
            <Tooltip contentStyle={{ background: '#10151f', border: '1px solid rgba(255,255,255,0.1)' }} />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="mwh" name="Grid Demand (MWh)" stroke="#00e5ff" dot={false} strokeWidth={2} />
            <Line yAxisId="right" type="monotone" dataKey="worst_pct" name="Worst Transformer %Loaded" stroke="#ff6d00" dot={false} strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="panel insight-panel">
        {peakDemand && peakRisk ? (
          <p>
            Grid demand peaked at <strong>{peakDemand.mwh.toLocaleString()} MWh</strong> around{' '}
            <strong>{peakDemand.period.slice(-2)}:00</strong>, coinciding with a worst-case transformer loading of{' '}
            <strong>{peakRisk.worst_pct.toFixed(1)}%</strong> around{' '}
            <strong>{(peakRisk.timestamp || '').slice(11, 16)}</strong>.
          </p>
        ) : (
          <p className="empty-state">Not enough data yet to compute a correlation insight for this city.</p>
        )}
      </div>

      <Footer />
    </div>
  )
}
