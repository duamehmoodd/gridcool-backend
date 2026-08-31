import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { CityProvider } from './CityContext'
import Dashboard from './pages/Dashboard'
import HeatIntel from './pages/HeatIntel'
import RiskTimeline from './pages/RiskTimeline'
import GridDemandPage from './pages/GridDemandPage'
import AlertsAudit from './pages/AlertsAudit'

export default function App() {
  return (
    <CityProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/heat-intel" element={<HeatIntel />} />
          <Route path="/risk-timeline" element={<RiskTimeline />} />
          <Route path="/grid-demand" element={<GridDemandPage />} />
          <Route path="/alerts" element={<AlertsAudit />} />
        </Routes>
      </BrowserRouter>
    </CityProvider>
  )
}
