import axios from 'axios'

const api = axios.create({
  baseURL: 'https://shoppulse-api-kptx.onrender.com',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

export const fetchKPIs            = ()       => api.get('/kpis')
export const fetchMonthlyRevenue  = ()       => api.get('/kpis/monthly-revenue')
export const fetchTopProducts     = (n=10)   => api.get(`/kpis/top-products?limit=${n}`)
export const fetchCategoryRevenue = ()       => api.get('/kpis/category-revenue')
export const fetchSegments        = ()       => api.get('/segments')
export const fetchRFM             = ()       => api.get('/rfm')
export const fetchCustomers       = (p={})   => api.get('/customers', { params: p })
export const fetchCustomer        = (id)     => api.get(`/customers/${id}`)
export const fetchTransactions    = (p={})   => api.get('/transactions', { params: p })
export const predictChurn         = (body)   => api.post('/predict-churn', body)
export const fetchAllPredictions  = ()       => api.get('/predict-churn/all')
export const runBatchPrediction   = ()       => api.post('/predict-churn/batch')

export default api

