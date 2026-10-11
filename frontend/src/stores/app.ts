import { ref } from 'vue'
import { defineStore } from 'pinia'
import { USER_ID_STORAGE_KEY } from '../api/http'

function readInitialUserId(): number {
  const stored = Number(localStorage.getItem(USER_ID_STORAGE_KEY) || '1')
  return Number.isInteger(stored) && stored > 0 ? stored : 1
}

export const useAppStore = defineStore('app', () => {
  const userId = ref(readInitialUserId())

  function setUserId(value: number): void {
    const normalized = Number.isInteger(value) && value > 0 ? value : 1
    userId.value = normalized
    localStorage.setItem(USER_ID_STORAGE_KEY, String(normalized))
  }

  return { userId, setUserId }
})