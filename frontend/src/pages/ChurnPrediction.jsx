// src/pages/ChurnPrediction.jsx
import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Cell, ResponsiveContainer
} from 'recharts'
import { predictChurn, fetchAllPredictions, runBatchPredictions } from '../api/client'
import Spinner    from '../components/Spinner'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader from '../components/PageHeader'
import RiskBadge  from '../components/RiskBadge'

const RISK_COLORS = { Low: '#10b981', Medium: '#f59e0b', High: '#ef4444' }

function ProbBar({ value }) {
  const pct   = Math.round(value * 100)
  const color = value >= 0.66 ? '#ef4444' : value >= 0.33 ? '#f59e0b' : '#10b981'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
        <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-medium text-slate-600 w-8 text-right">{pct}%</span>
    </div>
  )
}

export default function ChurnPrediction() {
  // Single prediction form
  const [form, setForm] = useState({ recency_days: 90, frequency: 3, monetary: 200 })
  const [result,      setResult]      = useState(null)
  const [predLoading, setPredLoading] = useState(false)
  const [predError,   setPredError]   = useState(null)

  // Batch / all-customer predictions
  const [predictions, setPredictions] = useState([])
  const [listLoading, setListLoading] = useState(true)
  const [listError,   setListError]   = useState(null)
  const [batchBusy,   setBatchBusy]   = useState(false)

  // Load saved predictions
  const loadPredictions = () => {
    setListLoading(true)
    fetchAllPredictions()
      .then((r) => setPredictions(r.data || []))
      .catch((e) => setListError(e.message))
      .finally(() => setListLoading(false))
  }

  useEffect(() => { loadPredictions() }, [])

  // Single prediction
  const handlePredict = () => {
    setPredLoading(true)
    setPredError(null)
    setResult(null)
    predictChurn({
      recency_days: Number(form.recency_days),
      frequency:    Number(form.frequency),
      monetary:     Number(form.monetary),
    })
      .then(setResult)
      .catch((e) => setPredError(e.message))
      .finally(() => setPredLoading(false))
  }

  // Batch prediction
  const handleBatch = () => {
    setBatchBusy(true)
    runBatchPredictions()
      .then(() => loadPredictions())
      .catch((e) => setListError(e.message))
      .finally(() => setBatchBusy(false))
  }

  // Risk distribution for chart
  const riskDist = ['Low','Medium','High'].map((r) => ({
    risk:  r,
    count: predictions.filter((p) => p.risk_category === r).length,
  }))

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Churn Prediction"
        subtitle="ML-powered customer attrition analysis"
      >
        <button
          className="btn-primary"
          onClick={handleBatch}
          disabled={batchBusy}
        >
          {batchBusy ? 'Running…' : '⚡ Run batch prediction'}
        </button>
      </PageHeader>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* ── Single Prediction Form ── */}
        <div className="card p-5 lg:col-span-1">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Predict a customer</h2>
          <p className="text-xs text-slate-400 mb-4">
            Enter RFM values to get an instant churn probability.
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Recency (days since last purchase)
              </label>
              <input
                type="number" min="0" className="input"
                value={form.recency_days}
                onChange={(e) => setForm({ ...form, recency_days: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Frequency (number of orders)
              </label>
              <input
                type="number" min="0" className="input"
                value={form.frequency}
                onChange={(e) => setForm({ ...form, frequency: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Monetary (total spend, $)
              </label>
              <input
                type="number" min="0" step="0.01" className="input"
                value={form.monetary}
                onChange={(e) => setForm({ ...form, monetary: e.target.value })}
              />
            </div>

            <button
              className="btn-primary w-full"
              onClick={handlePredict}
              disabled={predLoading}
            >
              {predLoading ? 'Predicting…' : 'Predict churn'}
            </button>
          </div>

          {predError && (
            <p className="mt-3 text-xs text-red-500 bg-red-50 rounded-lg p-2">{predError}</p>
          )}

          {/* ── Result card ── */}
          {result && (
            <div className="mt-5 p-4 rounded-xl border-2 border-indigo-100 bg-indigo-50">
              <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wide mb-3">Prediction result</p>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Churn probability</span>
                  <span className="font-bold text-slate-800">
                    {(result.churn_probability * 100).toFixed(1)}%
                  </span>
                </div>
                <ProbBar value={result.churn_probability} />
                <div className="flex justify-between items-center mt-2">
                  <span className="text-sm text-slate-600">Risk level</span>
                  <RiskBadge risk={result.risk_category} />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Will churn?</span>
                  <span className={`text-sm font-semibold ${result.churn_label ? 'text-red-600' : 'text-emerald-600'}`}>
                    {result.churn_label ? 'Yes — take action' : 'No — customer retained'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Risk Distribution Chart ── */}
        <div className="card p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-700 mb-1">Risk distribution</h2>
          <p className="text-xs text-slate-400 mb-4">Customers by churn risk category</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={riskDist} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="risk" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {riskDist.map((r) => (
                  <Cell key={r.risk} fill={RISK_COLORS[r.risk]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Summary pills */}
          <div className="flex gap-3 mt-4 flex-wrap">
            {riskDist.map((r) => (
              <div key={r.risk} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 border border-slate-100">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: RISK_COLORS[r.risk] }} />
                <span className="text-xs text-slate-600 font-medium">{r.risk} risk</span>
                <span className="text-sm font-bold text-slate-800">{r.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── All Predictions Table ── */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">All customer predictions</h2>
          <span className="text-xs text-slate-400">{predictions.length} records</span>
        </div>
        {listLoading ? (
          <Spinner label="Loading predictions…" />
        ) : listError ? (
          <div className="p-4"><ErrorBanner message={listError} /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  {['Customer ID','Name','Churn Probability','Will Churn','Risk','Predicted At'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium text-slate-500 text-xs uppercase tracking-wide whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {predictions.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                      No predictions yet. Click "Run batch prediction" to generate.
                    </td>
                  </tr>
                )}
                {predictions.map((p) => (
                  <tr key={p.customer_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{p.customer_id}</td>
                    <td className="px-4 py-3 font-medium text-slate-800">{p.name}</td>
                    <td className="px-4 py-3 w-48">
                      <ProbBar value={p.churn_prob} />
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold ${p.churn_label ? 'text-red-600' : 'text-emerald-600'}`}>
                        {p.churn_label ? '⚠ Yes' : '✓ No'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge risk={p.risk_category} />
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {p.predicted_at ? new Date(p.predicted_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
