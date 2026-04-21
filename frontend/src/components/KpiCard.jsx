// src/components/KpiCard.jsx
export default function KpiCard({ label, value, sub, color = 'indigo' }) {
  const accent = {
    indigo:  'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber:   'bg-amber-50   text-amber-600',
    red:     'bg-red-50     text-red-600',
  }[color] || 'bg-indigo-50 text-indigo-600'

  return (
    <div className="card flex flex-col gap-1">
      <span className={`self-start text-xs font-medium px-2 py-0.5 rounded-full ${accent}`}>
        {label}
      </span>
      <span className="text-3xl font-semibold text-gray-900 mt-1">{value ?? '—'}</span>
      {sub && <span className="text-sm text-gray-400">{sub}</span>}
    </div>
  )
}
