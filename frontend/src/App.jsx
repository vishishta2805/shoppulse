// src/App.jsx
import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard      from './pages/Dashboard'
import Customers      from './pages/Customers'
import ChurnPredict   from './pages/ChurnPredict'
import Transactions   from './pages/Transactions'

const NAV = [
  { to: '/',             label: 'Dashboard' },
  { to: '/customers',    label: 'Customers'  },
  { to: '/transactions', label: 'Transactions' },
  { to: '/churn',        label: 'Churn AI'   },
]

export default function App() {
  return (
    <div className="min-h-screen flex bg-gray-50">

      {/* ── Sidebar ── */}
      <aside className="w-60 shrink-0 bg-white border-r border-gray-100 flex flex-col">
        <div className="px-6 py-5 border-b border-gray-100">
          <span className="text-xl font-semibold text-indigo-600 tracking-tight">
            ShopPulse
          </span>
          <p className="text-xs text-gray-400 mt-0.5">Intelligence Platform</p>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-gray-100 text-xs text-gray-400">
          v1.0.0 · Built with FastAPI + React
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/"             element={<Dashboard />} />
          <Route path="/customers"    element={<Customers />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/churn"        element={<ChurnPredict />} />
        </Routes>
      </main>

    </div>
  )
}
