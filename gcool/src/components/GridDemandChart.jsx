import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function GridDemandChart({ demand, city }) {
  if (!demand || demand.status !== 'ok' || !demand.demand_mwh?.length) {
    return (
      <div className="panel demand-mini">
        <div className="panel-header"><span>GRID DEMAND</span></div>
        <div className="empty-state">Demand data unavailable (city: {city}{demand?.ba_code ? `, ba: ${demand.ba_code}` : ''})</div>
      </div>
    )
  }

  const rows = demand.demand_mwh.map(d => ({
    period: d.period?.slice(-2) + ':00',
    mwh: Number(d.value_mwh),
  }))

  return (
    <div className="panel demand-mini">
      <div className="panel-header">
        <span>GRID DEMAND</span>
        <span className="pill-mini">{demand.ba_name || demand.ba_code}</span>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="period" stroke="#7f8aa3" fontSize={10} />
          <YAxis stroke="#7f8aa3" fontSize={10} />
          <Tooltip contentStyle={{ background: '#10151f', border: '1px solid rgba(255,255,255,0.1)' }} />
          <Line type="monotone" dataKey="mwh" stroke="#00e5ff" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
