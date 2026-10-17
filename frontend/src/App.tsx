import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import { FeedPage } from './pages/FeedPage'
import { HomePage } from './pages/HomePage'
import { MapPage } from './pages/MapPage'
import { NewReportPage } from './pages/NewReportPage'

export default function App() {
  return (
    <BrowserRouter>
      <header className="topbar">
        <Link to="/" className="logo">
          graty<span className="accent">PL</span>
          <span className="demo-tag">demo</span>
        </Link>
        <nav>
          <NavLink to="/" end>
            O projekcie
          </NavLink>
          <NavLink to="/posty">Posty</NavLink>
          <NavLink to="/mapa">Mapa</NavLink>
          <NavLink to="/zglos" className="nav-cta">
            Zgłoś grata
          </NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/posty" element={<FeedPage />} />
          <Route path="/mapa" element={<MapPage />} />
          <Route path="/zglos" element={<NewReportPage />} />
          <Route path="*" element={<p className="page empty">Nie ma takiej strony.</p>} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
