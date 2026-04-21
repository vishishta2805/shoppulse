// src/api/index.js
// All API call functions, consumed by pages/components via React hooks.

import api from './client'

// ── KPIs ──
export const fetchKPIs             = () => api.get('/kpis').then(r => r.data)
export const fetchMonthlyRevenue   = () => api.get('/kpis/monthly-revenue').then(r => r.data.data)
export const fetchTopProducts      = (n=10) => api.get(`/kpis/top-products?limit=${n}`).then(r => r.data.data)
export const fetchCategoryRevenue  = () => api.get('/kpis/category-revenue').then(r => r.data.data)

// ── Segments & RFM ──
export const fetchSegments = () => api.get('/segments').then(r => r.data.data)
export const fetchRFM      = () => api.get('/rfm').then(r => r.data.data)

// ── Customers ──
export const fetchCustomers = (params = {}) =>
  api.get('/customers', { params }).then(r => r.data)
export const fetchCustomer  = (id) =>
  api.get(`/customers/${id}`).then(r => r.data)

// ── Transactions ──
export const fetchTransactions = (params = {}) =>
  api.get('/transactions', { params }).then(r => r.data)

// ── Churn ──
export const predictChurn   = (body) => api.post('/predict-churn', body).then(r => r.data)
export const fetchAllChurn  = ()     => api.get('/predict-churn/all').then(r => r.data.data)
export const runBatchChurn  = ()     => api.post('/predict-churn/batch').then(r => r.data)
