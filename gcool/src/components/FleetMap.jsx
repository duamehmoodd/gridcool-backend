import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { useCity } from '../CityContext'
import { severityColor, cityWorstSeverity } from '../riskColors'

export default function FleetMap({ cityDecisions }) {
  const { cities, activeCity, setActiveCity } = useCity()

  return (
    <div className="panel fleet-map-panel">
      <div className="panel-header">
        <span>FLEET MAP</span>
        <span className="pill">{cities.length} CITIES</span>
      </div>
      <div className="map-wrap">
        <MapContainer center={[39.5, -98.35]} zoom={4} scrollWheelZoom={true} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            className="dark-tiles"
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {cities.map((c) => {
            const decision = cityDecisions?.[c.id]
            const worst = cityWorstSeverity(decision)
            const color = worst === 'none' ? '#00e676' : severityColor(worst)
            const isActive = activeCity === c.id
            return (
              <CircleMarker
                key={c.id}
                center={[c.lat, c.lon]}
                radius={isActive ? 12 : 9}
                pathOptions={{ color: '#fff', weight: isActive ? 2 : 1, fillColor: color, fillOpacity: 0.9 }}
                eventHandlers={{ click: () => setActiveCity(c.id) }}
              >
                <Popup>
                  <strong>{c.display_name}</strong><br />
                  {decision && decision.headline ? decision.headline : 'Loading risk data…'}
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>
    </div>
  )
}
