// src/pages/Customers.jsx
import { useEffect, useState } from 'react'
import { fetchCustomers, fetchRFM } from '../api'
import PageHeader  from '../components/PageHeader'
import Loader      from '../components/Loader'
import ErrorBanner from '../components/ErrorBanner'
import RiskBadge   from '../components/RiskBadge'

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [rfm,       setRfm]       = useState({})
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [search,    setSearch]    = useState('')

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchCustomers({ limit: 100 }), fetchRFM()])
      .then(([cData, rfmData]) => {
        setCustomers(cData.customers)
        // Build lookup: customer_id → rfm row
        const map = {}
        rfmData.forEach(r => { map[r.customer_id] = r })
        setRfm(map)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = customers.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.email.toLowerCase().includes(search.toLowerCase()) ||
    c.city?.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) return <div className="p-8"><Loader text="Loading customers…" /></div>
  if (error)   return <div className="p-8"><ErrorBanner message={error} /></div>

  return (
    <div className="p-8">
      <PageHeader
        title="Customers"
        subtitle={`${customers.length} total customers`}
        actions={
          <input
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 w-56"
            placeholder="Search name, email, city…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        }
      />

      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['ID','Name','Email','City','Age','Gender','Segment','Recency','Frequency','Spend'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map(c => {
                const r = rfm[c.customer_id]
                return (
                  <tr key={c.customer_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">{c.customer_id}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{c.name}</td>
                    <td className="px-4 py-3 text-gray-500">{c.email}</td>
                    <td className="px-4 py-3 text-gray-500">{c.city}</td>
                    <td className="px-4 py-3 text-gray-500">{c.age}</td>
                    <td className="px-4 py-3">
                      <span className="badge-blue">{c.gender}</span>
                    </td>
                    <td className="px-4 py-3">
                      {r ? <span className="badge-blue">{r.segment}</span> : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{r ? `${r.recency_days}d` : '—'}</td>
                    <td className="px-4 py-3 text-gray-500">{r?.frequency ?? '—'}</td>
                    <td className="px-4 py-3 font-medium">
                      {r ? `$${Number(r.monetary).toFixed(0)}` : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <p className="text-center text-gray-400 py-12 text-sm">No customers match your search.</p>
        )}
      </div>
    </div>
  )
}
