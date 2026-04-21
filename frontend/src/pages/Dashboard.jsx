// src/pages/Dashboard.jsx
import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import KpiCard     from '../components/KpiCard'
import Loader      from '../components/Loader'
import ErrorBanner from '../components/ErrorBanner'
import PageHeader  from '../components/PageHeader'
import {
  fetchKPIs, fetchMonthlyRevenue, fetchSegments,
  fetchTopProducts, fetchCategoryRevenue
} from '../api'

const PIE_COLORS = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4']
const CAT_COLORS = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f43f5e','#84cc16']

function fmt(n)    { return n != null ? `$${Number(n).toLocaleString(undefined,{maximumFractionDigits:0})}` : '—' }
function fmtPct(n) { return n != null ? `${n}%` : '—' }

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'var(--color-background-primary)',
        border: '0.5px solid var(--color-border-tertiary)',
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '12px'
      }}>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 4 }}>{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color, fontWeight: 500 }}>
            {p.name}: {p.name === 'revenue' ? `$${Number(p.value).toFixed(2)}` : p.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function Dashboard() {
  const [kpis,     setKpis]     = useState(null)
  const [revenue,  setRevenue]  = useState([])
  const [segs,     setSegs]     = useState([])
  const [products, setProducts] = useState([])
  const [catRev,   setCatRev]   = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchKPIs(),
      fetchMonthlyRevenue(),
      fetchSegments(),
      fetchTopProducts(8),
      fetchCategoryRevenue(),
    ])
      .then(([k, r, s, p, c]) => {
        setKpis(k); setRevenue(r); setSegs(s); setProducts(p); setCatRev(c)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8"><Loader text="Loading dashboard…" /></div>
  if (error)   return <div className="p-8"><ErrorBanner message={error} /></div>

  return (
    <div className="p-8">
      <PageHeader
        title="Dashboard"
        subtitle="Real-time overview of your customer and sales intelligence"
      />

      {/* SECTION 1: Sales KPIs */}
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
        Sales Overview
      </p>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Total Revenue"   value={fmt(kpis?.total_revenue)}   color="indigo"  />
        <KpiCard label="Total Orders"    value={kpis?.total_orders}         color="emerald" sub="transactions" />
        <KpiCard label="Avg Order Value" value={fmt(kpis?.avg_order_value)} color="amber"   />
        <KpiCard label="Total Discounts" value={fmt(kpis?.total_discounts)} color="indigo"  sub="discounts given" />
      </div>

      {/* SECTION 2: Customer KPIs */}
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
        Customer Metrics
      </p>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Total Customers"   value={kpis?.total_customers}        color="indigo"  />
        <KpiCard label="Active Customers"  value={kpis?.active_customers}       color="emerald" sub="purchased recently" />
        <KpiCard label="Churned Customers" value={kpis?.churned_customers}      color="red"     sub="inactive 90+ days" />
        <KpiCard label="New (30 days)"     value={kpis?.new_customers_30d ?? 0} color="amber"   sub="new signups" />
      </div>

      {/* SECTION 3: Retention KPIs */}
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
        Retention & Engagement
      </p>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard label="Churn Rate"         value={fmtPct(kpis?.churn_rate)}         color="red"     sub="high-risk customers" />
        <KpiCard label="Retention Rate"     value={fmtPct(kpis?.retention_rate)}     color="emerald" />
        <KpiCard label="Deal Participation" value={fmtPct(kpis?.deal_participation)} color="amber"   sub="orders with deals" />
        <KpiCard label="Total Returns"      value={kpis?.total_returns ?? 0}         color="red"     sub="returned orders" />
      </div>

      {/* SECTION 4: Revenue Trend + Segment Pie */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="card lg:col-span-2">
          <h2 className="text-base font-medium text-gray-800 mb-4">Monthly Revenue Trend</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={revenue} margin={{ top: 10, right: 20, left: 10, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: '#6b7280' }}
                angle={-35}
                textAnchor="end"
                height={70}
                interval={0}
                tickFormatter={l => {
                  const parts = l.split(' ')
                  return parts[0].slice(0, 3) + ' ' + (parts[1] || '')
                }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={v => `$${Number(v).toLocaleString()}`}
                width={75}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="#6366f1"
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#6366f1' }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="text-base font-medium text-gray-800 mb-2">Customer Segments</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
              <Pie
                data={segs}
                dataKey="customer_count"
                nameKey="segment"
                cx="50%"
                cy="45%"
                outerRadius={80}
                labelLine={false}
                label={false}
              >
                {segs.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value, name) => [value, name]} />
              <Legend
                layout="vertical"
                align="right"
                verticalAlign="middle"
                iconType="circle"
                iconSize={8}
                formatter={(value, entry) => (
                  <span style={{ fontSize: '11px', color: '#374151' }}>
                    {value} ({entry.payload.customer_count})
                  </span>
                )}
                wrapperStyle={{ fontSize: '11px', lineHeight: '22px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION 5: Top Products + Category Revenue */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="card">
          <h2 className="text-base font-medium text-gray-800 mb-4">Top Products by Revenue</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={products}
              layout="vertical"
              margin={{ left: 120, right: 50, top: 4, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={v => `$${Number(v).toLocaleString()}`}
              />
              <YAxis
                type="category"
                dataKey="product_name"
                tick={{ fontSize: 11, fill: '#374151' }}
                width={120}
              />
              <Tooltip formatter={(v) => [`$${Number(v).toFixed(2)}`, 'Revenue']} />
              <Bar dataKey="revenue" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="text-base font-medium text-gray-800 mb-4">Revenue by Category</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={catRev}
              layout="vertical"
              margin={{ left: 90, right: 50, top: 4, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={v => `$${Number(v).toLocaleString()}`}
              />
              <YAxis
                type="category"
                dataKey="category"
                tick={{ fontSize: 11, fill: '#374151' }}
                width={90}
              />
              <Tooltip formatter={(v) => [`$${Number(v).toFixed(2)}`, 'Revenue']} />
              <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                {catRev.map((_, i) => (
                  <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION 6: Monthly Orders */}
      <div className="card mb-6">
        <h2 className="text-base font-medium text-gray-800 mb-4">Monthly Orders Count</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={revenue} margin={{ top: 4, right: 20, left: 10, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: '#6b7280' }}
              angle={-35}
              textAnchor="end"
              height={70}
              interval={0}
              tickFormatter={l => {
                const parts = l.split(' ')
                return parts[0].slice(0, 3) + ' ' + (parts[1] || '')
              }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#6b7280' }}
              allowDecimals={false}
              domain={[0, 'auto']}
            />
            <Tooltip formatter={(v) => [v, 'Orders']} />
            <Bar dataKey="orders" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* SECTION 7: Full KPI Summary Table */}
      <div className="card">
        <h2 className="text-base font-medium text-gray-800 mb-4">Full KPI Summary</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">KPI</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Value</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {[
                { kpi: 'Total Revenue',       value: fmt(kpis?.total_revenue),         desc: 'Total net revenue after discounts' },
                { kpi: 'Total Orders',        value: kpis?.total_orders,               desc: 'Total number of transactions' },
                { kpi: 'Avg Order Value',     value: fmt(kpis?.avg_order_value),       desc: 'Average spend per transaction' },
                { kpi: 'Total Discounts',     value: fmt(kpis?.total_discounts),       desc: 'Total discount amount given to customers' },
                { kpi: 'Total Returns',       value: kpis?.total_returns ?? 0,         desc: 'Number of returned orders' },
                { kpi: 'Total Customers',     value: kpis?.total_customers,            desc: 'All registered customers' },
                { kpi: 'Active Customers',    value: kpis?.active_customers,           desc: 'Customers who purchased recently' },
                { kpi: 'Churned Customers',   value: kpis?.churned_customers,          desc: 'No purchase in last 90 days' },
                { kpi: 'Churn Rate',          value: fmtPct(kpis?.churn_rate),         desc: 'Percentage of churned customers' },
                { kpi: 'Retention Rate',      value: fmtPct(kpis?.retention_rate),     desc: 'Percentage of retained customers' },
                { kpi: 'Deal Participation',  value: fmtPct(kpis?.deal_participation), desc: 'Orders that used a promotional deal' },
                { kpi: 'New Customers (30d)', value: kpis?.new_customers_30d ?? 0,     desc: 'Customers signed up in last 30 days' },
              ].map((row, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{row.kpi}</td>
                  <td className="px-4 py-3 font-semibold text-indigo-600">{row.value}</td>
                  <td className="px-4 py-3 text-gray-500">{row.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  )
}