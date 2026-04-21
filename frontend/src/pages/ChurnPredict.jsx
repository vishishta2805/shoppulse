// src/pages/ChurnPredict.jsx
import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Cell
} from 'recharts'
import { predictChurn, fetchAllChurn, runBatchChurn } from '../api'
import PageHeader  from '../components/PageHeader'
import Loader      from '../components/Loader'
import ErrorBanner from '../components/ErrorBanner'
import RiskBadge   from '../components/RiskBadge'

const RISK_COLORS = { Low: '#10b981', Medium: '#f59e0b', High: '#ef4444' }

export default function ChurnPredict() {
  // Single prediction form
  const [form,    setForm]    = useState({ recency_days: '', frequency: '', monetary: '' })
  const [result,  setResult]  = useState(null)
  const [fLoading, setFLoad]  = useState(false)
  const [fError,  setFError]  = useState(null)

  // Batch predictions table
  const [preds,   setPreds]   = useState([])
  const [pLoading, setPLoad]  = useState(true)
  const [pError,  setPError]  = useState(null)
  const [running, setRunning] = useState(false)

  useEffect(() => { loadPredictions() }, [])

  const loadPredictions = () => {
    setPLoad(true)
    fetchAllChurn()
      .then(setPreds)
      .catch(e => setPError(e.message))
      .finally(() => setPLoad(false))
  }

  const handleSubmit = async () => {
    const { recency_days, frequency, monetary } = form
    if (!recency_days || !frequency || !monetary) {
      setFError('Please fill in all three fields.')
      return
    }
    setFLoad(true); setFError(null); setResult(null)
    try {
      const res = await predictChurn({
        recency_days: parseFloat(recency_days),
        frequency:    parseFloat(frequency),
        monetary:     parseFloat(monetary),
      })
      setResult(res)
    } catch (e) {
      setFError(e.message)
    } finally {
      setFLoad(false)
    }
  }

  const handleBatch = async () => {
    setRunning(true)
    try {
      await runBatchChurn()
      await loadPredictions()
    } catch (e) {
      setPError(e.message)
    } finally {
      setRunning(false)
    }
  }

  // Build chart data from predictions
  const riskCounts = preds.reduce((acc, p) => {
    acc[p.risk_category] = (acc[p.risk_category] || 0) + 1
    return acc
  }, {})
  const chartData = Object.entries(riskCounts).map(([k, v]) => ({ name: k, count: v }))

  return (
    <div className="p-8">
      <PageHeader
        title="Churn Prediction"
        subtitle="ML-powered customer risk scoring using RFM features"
        actions={
          <button onClick={handleBatch} disabled={running} className="btn-primary">
            {running ? 'Running…' : 'Run Batch Predictions'}
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">

        {/* ── Single Prediction Form ── */}
        <div className="card">
          <h2 className="text-base font-medium text-gray-800 mb-4">Predict Single Customer</h2>
          <div className="space-y-3">
            {[
              { key: 'recency_days', label: 'Recency (days since last purchase)', placeholder: 'e.g. 45' },
              { key: 'frequency',    label: 'Frequency (number of orders)',        placeholder: 'e.g. 5'  },
              { key: 'monetary',     label: 'Monetary (total spend, USD)',          placeholder: 'e.g. 320'},
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
                <input
                  type="number" min="0" placeholder={placeholder}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </div>
            ))}

            {fError && <ErrorBanner message={fError} />}

            <button onClick={handleSubmit} disabled={fLoading} className="btn-primary w-full mt-2">
              {fLoading ? 'Predicting…' : 'Predict Churn'}
            </button>
          </div>

          {/* Result */}
          {result && (
            <div className="mt-5 rounded-xl border border-gray-100 bg-gray-50 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Churn Probability</span>
                <span className="text-xl font-semibold text-gray-900">
                  {(result.churn_probability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Risk Category</span>
                <RiskBadge risk={result.risk_category} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Churn Predicted</span>
                <span className={`font-medium text-sm ${result.churn_label ? 'text-red-600' : 'text-emerald-600'}`}>
                  {result.churn_label ? 'Yes — likely to churn' : 'No — likely to retain'}
                </span>
              </div>
              {/* Probability bar */}
              <div className="mt-2">
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      result.risk_category === 'High'   ? 'bg-red-500'
                      : result.risk_category === 'Medium' ? 'bg-amber-400'
                      : 'bg-emerald-500'
                    }`}
                    style={{ width: `${(result.churn_probability * 100).toFixed(1)}%` }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Risk Distribution Chart ── */}
        <div className="card">
          <h2 className="text-base font-medium text-gray-800 mb-4">Risk Distribution</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={RISK_COLORS[entry.name] || '#6366f1'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-16">
              No predictions yet. Click "Run Batch Predictions".
            </p>
          )}
        </div>
      </div>

      {/* ── All Predictions Table ── */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-base font-medium text-gray-800">All Customer Predictions</h2>
          <span className="text-sm text-gray-400">{preds.length} customers</span>
        </div>

        {pLoading && <Loader text="Loading predictions…" />}
        {pError   && <div className="p-6"><ErrorBanner message={pError} /></div>}

        {!pLoading && !pError && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {['Customer ID','Name','Churn Probability','Risk','Churn Label','Predicted At'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {preds.map(p => (
                  <tr key={p.customer_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">{p.customer_id}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{p.name}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              p.risk_category === 'High' ? 'bg-red-500'
                              : p.risk_category === 'Medium' ? 'bg-amber-400'
                              : 'bg-emerald-500'
                            }`}
                            style={{ width: `${(p.churn_prob * 100).toFixed(0)}%` }}
                          />
                        </div>
                        <span className="text-gray-700">{(p.churn_prob * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3"><RiskBadge risk={p.risk_category} /></td>
                    <td className="px-4 py-3">
                      <span className={p.churn_label ? 'text-red-600 font-medium' : 'text-emerald-600 font-medium'}>
                        {p.churn_label ? 'Churn' : 'Retain'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">
                      {p.predicted_at ? new Date(p.predicted_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {preds.length === 0 && (
              <p className="text-center text-gray-400 py-12 text-sm">
                No predictions yet. Run batch predictions above.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
