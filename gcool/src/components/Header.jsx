import { NavLink } from 'react-router-dom'
import { useCity } from '../CityContext'

export default function Header({ dataMode, lastUpdated, onRefresh }) {
  const { cities, activeCity, setActiveCity } = useCity()

  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-mark">⚡</div>
        <div>
          <div className="brand-title">GridCool USA</div>
          <div className="brand-sub">ENERGY GRID RISK INTELLIGENCE</div>
        </div>
      </div>

      <nav className="city-tabs">
        {cities.map((c) => (
          <button
            key={c.id}
            className={`city-tab ${activeCity === c.id ? 'active' : ''}`}
            onClick={() => setActiveCity(c.id)}
          >
            {c.display_name}
          </button>
        ))}
      </nav>

      <div className="page-nav">
        <NavLink to="/" end className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Dashboard</NavLink>
        <NavLink to="/heat-intel" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Heat Intel</NavLink>
        <NavLink to="/risk-timeline" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Risk Timeline</NavLink>
        <NavLink to="/grid-demand" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Grid Demand</NavLink>
        <NavLink to="/alerts" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Alerts & Audit</NavLink>
      </div>

      <div className="status-cluster">
        {dataMode && (
          <span className={`badge ${dataMode === 'live' ? 'badge-live' : 'badge-hist'}`}>
            {dataMode === 'live' ? '● LIVE' : 'HISTORICAL'}
          </span>
        )}
        {lastUpdated && <span className="updated-text">Updated {lastUpdated}</span>}
        {onRefresh && <button className="refresh-btn" onClick={onRefresh}>⟳ Refresh</button>}
      </div>
    </header>
  )
}
