import { ref } from 'vue'
import { configApi } from '../api'

const config = ref(null)

export function useConfig() {
  async function fetch() {
    const { data } = await configApi.get()
    config.value = data
  }

  async function save(payload) {
    const { data } = await configApi.update(payload)
    config.value = data
    return data
  }

  return { config, fetch, save }
}
