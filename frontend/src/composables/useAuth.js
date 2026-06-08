import { ref } from 'vue'
import { authApi, setAdminPassword, clearAdminPassword } from '../api'

const isUnlocked = ref(false)
const showModal = ref(false)
const authError = ref('')
let _pending = null

export function useAuth() {
  function requireAuth(callback) {
    if (isUnlocked.value) { callback(); return }
    _pending = callback
    authError.value = ''
    showModal.value = true
  }

  async function submit(password) {
    authError.value = ''
    try {
      const { data } = await authApi.verify(password)
      if (data.valid) {
        isUnlocked.value = true
        showModal.value = false
        setAdminPassword(password)
        if (_pending) { _pending(); _pending = null }
        return true
      }
      authError.value = 'Senha incorreta.'
      return false
    } catch {
      authError.value = 'Erro ao verificar senha.'
      return false
    }
  }

  function lock() {
    isUnlocked.value = false
    _pending = null
    clearAdminPassword()
  }

  function cancel() {
    showModal.value = false
    _pending = null
  }

  return { isUnlocked, showModal, authError, requireAuth, submit, lock, cancel }
}
