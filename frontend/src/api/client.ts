import axios from 'axios'
import { ACCESS_KEY, REFRESH_KEY } from '../store/authTokens'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config
    if (
      error.response?.status === 401 &&
      !originalRequest?._retry &&
      localStorage.getItem(REFRESH_KEY) &&
      !originalRequest?.url?.includes('/auth/login') &&
      !originalRequest?.url?.includes('/auth/register') &&
      !originalRequest?.url?.includes('/auth/refresh')
    ) {
      originalRequest._retry = true
      try {
        const res = await axios.post('/api/v1/auth/refresh', {
          refresh_token: localStorage.getItem(REFRESH_KEY),
        })
        const token = res.data.data.access_token
        localStorage.setItem(ACCESS_KEY, token)
        localStorage.setItem(REFRESH_KEY, res.data.data.refresh_token)
        originalRequest.headers.Authorization = `Bearer ${token}`
        return client(originalRequest)
      } catch {
        localStorage.removeItem(ACCESS_KEY)
        localStorage.removeItem(REFRESH_KEY)
        window.location.href = '/login'
      }
    }
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default client
