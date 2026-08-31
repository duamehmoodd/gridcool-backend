import { useState } from 'react'
import { GeoJSON, MapContainer, TileLayer } from 'react-leaflet'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { useCity } from '../CityContext'
import { api } from '../api'
import { usePolling } from '../usePolling'
import { heatIndexColor, heatIndexLabel, aqiColor, cToF } from '../riskColors'

function tileColor(temp, min, max) {
  if (temp == null || min == null || max == null || max === min) return '#ffd600'
  const t = (temp - min) / (max - min)
  if (t < 0.33) return '#ffd600'
  if (t < 0.66) return '#ff6d00'
  return '#ff1744'
}

export default function HeatIntel() {
  const { cities, activeCity, setActiveCity } = useCity()
  const { data: intelAll } = usePolling(() => api.envIntelAll(35), [], 60000)
  const { data: heatmap, loading: heatmapLoading } = usePolling(
    () => api.heatmapTiles(activeCity, 100), [activeCity], 120000
  )

  const activeMeta = cities.find(c => c.id === activeCity) || cities[0]
  const stats = heatmap?.stats_data?.temperature_stats

  return (
    <div className="page">
      <Header />
      <div className="section-header">
        <h1>Heat Intelligence</h1>
        <p>Real-time thermal, air quality, and solar data for all monitored US grid cities</p>
        <span className="badge badge-live">FortyGuard API — Live</span>
      </div>

      <div className="heat-card-grid">
        {(intelAll?.cities || []).map((c) => {
          if (!c || c.status !== 'ok') return null
          const meta = cities.find(m => m.id === c.city)
          return (
            <div
              key={c.city}
              className={`heat-card ${activeCity === c.city ? 'selected' : ''}`}
              onClick={() => setActiveCity(c.city)}
            >
              <div className="heat-card-top">
                <div>
                  <div className="heat-card-city">{c.city_name || meta?.display_name}</div>
                  <div className="heat-card-ba">{meta?.eia_ba_name}</div>
                </div>
                <div className="danger-badge" style={{ background: heatIndexColor(c.heat_index_c) }}>
                  {heatIndexLabel(c.heat_index_c)}
                </div>
              </div>

              <div className="heat-index-big" style={{ color: heatIndexColor(c.heat_index_c) }}>
                {c.heat_index_c?.toFixed(1)}°C
                <span className="heat-index-f"> / {cToF(c.heat_index_c)}°F</span>
              </div>

              <div className="heat-mini-grid">
                <div><span>Humidity</span><strong>{c.humidity_pct}%</strong></div>
                <div><span>Wet Bulb</span><strong>{c.wet_bulb_c?.toFixed(1)}°C</strong></div>
                <div><span>Solar GHI</span><strong>{c.solar_ghi?.toFixed(0)} W/m²</strong></div>
                <div><span>Apparent</span><strong>{c.apparent_temp_c?.toFixed(1)}°C</strong></div>
              </div>

              <div className="aqi-slider">
                <div className="aqi-track" />
                <div
                  className="aqi-dot"
                  style={{ left: `${Math.min(c.aqi || 0, 200) / 2}%`, background: aqiColor(c.aqi) }}
                  title={`AQI ${c.aqi}`}
                />
              </div>
              <div className="heat-card-caption">FortyGuard API · Live · {new Date().toLocaleTimeString()}</div>
            </div>
          )
        })}
      </div>

      <div className="panel heatmap-panel">
        <div className="panel-header">
          <span>HEATMAP OVERLAY — {activeMeta?.display_name}</span>
          <span className="pill-mini">FortyGuard · latest available (~72hr processing lag)</span>
        </div>
        <div className="map-wrap" style={{ height: 420 }}>
          <MapContainer center={[activeMeta.lat, activeMeta.lon]} zoom={10} style={{ height: '100%', width: '100%' }} key={activeCity}>
            <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {heatmap?.status === 'ok' && heatmap.map_data && (
              <GeoJSON
                data={heatmap.map_data}
                style={(feature) => ({
                  fillColor: tileColor(feature.properties.average_temperature, stats?.minimum, stats?.maximum),
                  fillOpacity: 0.55,
                  weight: 0.5,
                  color: 'rgba(255,255,255,0.2)',
                })}
              />
            )}
          </MapContainer>
        </div>
        {heatmapLoading && <div className="empty-state">Loading heatmap tiles…</div>}
        {heatmap && heatmap.status !== 'ok' && <div className="empty-state">Heatmap unavailable for this city right now.</div>}
        <div className="legend-row">
          <span className="legend-dot" style={{ background: '#ffd600' }} /> Lower
          <span className="legend-dot" style={{ background: '#ff6d00' }} /> Mid
          <span className="legend-dot" style={{ background: '#ff1744' }} /> Higher
          {stats && <span className="legend-note">Range: {stats.minimum?.toFixed(1)}°C – {stats.maximum?.toFixed(1)}°C</span>}
        </div>
      </div>

      <Footer />
    </div>
  )
}
