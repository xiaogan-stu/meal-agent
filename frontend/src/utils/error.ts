import axios from 'axios'

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data: unknown = error.response?.data

    if (typeof data === 'string' && data.trim()) {
      return data
    }

    if (data && typeof data === 'object') {
      const body = data as Record<string, unknown>
      if (typeof body.message === 'string' && body.message) {
        return body.message
      }
      if (typeof body.error === 'string' && body.error) {
        return body.error
      }
    }

    if (error.code === 'ECONNABORTED') {
      return '请求超时，请确认模型服务可用后重试。'
    }

    if (!error.response) {
      return '无法连接后端，请确认 Spring Boot 已在 8080 端口启动。'
    }

    return '请求失败，HTTP 状态码：' + String(error.response.status)
  }

  if (error instanceof Error) return error.message
  return '发生未知错误。'
}

export function safePrettyJson(value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value
    return JSON.stringify(parsed, null, 2)
  } catch {
    return String(value)
  }
}