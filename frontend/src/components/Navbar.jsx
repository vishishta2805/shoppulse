import { NavLink } from 'react-router-dom'

const links = [
  { to: '/',          label: 'Dashboard' },
  { to: '/customers', label: 'Customers' },
  { to: '/churn',     label: 'Churn Prediction' },
]

export default function Navbar() {
  return (
    <nav className="h-16 bg-white border-b border-gray-200 flex items-center px-6 gap-8 sticky top-0 z-30">
      <span className="font-bold text-indigo-600 text-lg tracking-tight mr-4">
        ShopPulse
      </span>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `text-sm font-medium transition-colors ${
              isActive
                ? 'text-indigo-600 border-b-2 border-indigo-600 pb-0.5'
                : 'text-gray-500 hover:text-gray-900'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
