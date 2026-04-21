// src/pages/Transactions.jsx
import { useEffect, useState } from 'react'
import { fetchTransactions } from '../api'
import PageHeader  from '../components/PageHeader'
import Loader      from '../components/Loader'
import ErrorBanner from '../components/ErrorBanner'

export default function Transactions() {
  const [rows,    setRows]    = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [search,  setSearch]  = useState('')
  const [start,   setStart]   = useState('')
  const [end,     setEnd]     = useState('')

  const load = () => {
    setLoading(true)
    const params = { limit: 200 }
    if (start) params.start_date = start
    if (end)   params.end_date   = end
    fetchTransactions(params)
      .then(d => setRows(d.transactions))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const filtered = rows.filter(r =>
    r.customer_name?.toLowerCase().includes(search.toLowerCase()) ||
    r.product_name?.toLowerCase().includes(search.toLowerCase()) ||
    r.category?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="p-8">
      <PageHeader
        title="Transactions"
        subtitle={`${rows.length} records loaded`}
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 w-56"
          placeholder="Search customer, product…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <input type="date" value={start} onChange={e => setStart(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <input type="date" value={end} onChange={e => setEnd(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <button onClick={load} className="btn-primary">Apply</button>
        <button onClick={() => { setStart(''); setEnd(''); setTimeout(load, 0) }} className="btn-secondary">Clear</button>
      </div>

      {loading && <Loader text="Loading transactions…" />}
      {error   && <ErrorBanner message={error} />}

      {!loading && !error && (
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {['ID','Date','Customer','Product','Category','Qty','Unit Price','Discount','Net Amount','Payment','Deal'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map(t => (
                  <tr key={t.transaction_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">{t.transaction_id}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{t.transaction_date}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{t.customer_name}</td>
                    <td className="px-4 py-3 text-gray-700">{t.product_name}</td>
                    <td className="px-4 py-3"><span className="badge-blue">{t.category}</span></td>
                    <td className="px-4 py-3 text-gray-500">{t.quantity}</td>
                    <td className="px-4 py-3 text-gray-500">${Number(t.unit_price).toFixed(2)}</td>
                    <td className="px-4 py-3 text-gray-500">{(t.discount * 100).toFixed(0)}%</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">${Number(t.net_amount).toFixed(2)}</td>
                    <td className="px-4 py-3 text-gray-500">{t.payment_method}</td>
                    <td className="px-4 py-3">
                      {t.deal_name !== 'None'
                        ? <span className="badge-green">{t.deal_name}</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filtered.length === 0 && (
            <p className="text-center text-gray-400 py-12 text-sm">No transactions found.</p>
          )}
        </div>
      )}
    </div>
  )
}
