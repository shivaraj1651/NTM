import axios from 'axios'
import { useAuthStore } from '@/store/useAuthStore'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
})

apiClient.interceptors.request.use((config) => {
  const { token, user } = useAuthStore.getState()
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (user?.tenant_id) config.headers['X-Tenant-ID'] = user.tenant_id
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.replace('/login')
    }
    return Promise.reject(error)
  }
)
