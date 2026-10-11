import axios from 'axios'

export const USER_ID_STORAGE_KEY = 'today-eat.user-id'

export const http = axios.create({
  baseURL: '/api/v1/diet',
  timeout: 60_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use((config) => {
  const userId = localStorage.getItem(USER_ID_STORAGE_KEY) || '1'
  config.headers['X-User-Id'] = userId
  return config
})