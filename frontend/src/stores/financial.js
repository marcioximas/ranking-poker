import { ref } from 'vue'
import { financialApi } from '../api'

const summary = ref(null)
const expenses = ref([])

export function useFinancial() {
  async function fetch() {
    const [finRes, expRes] = await Promise.all([
      financialApi.get(),
      financialApi.getExpenses(),
    ])
    summary.value = finRes.data
    expenses.value = expRes.data
  }

  async function updateFinancial(payload) {
    await financialApi.update(payload)
    await fetch()
  }

  async function createExpense(payload) {
    const { data } = await financialApi.createExpense(payload)
    await fetch()
    return data
  }

  async function updateExpense(id, payload) {
    await financialApi.updateExpense(id, payload)
    await fetch()
  }

  async function removeExpense(id) {
    await financialApi.removeExpense(id)
    await fetch()
  }

  return { summary, expenses, fetch, updateFinancial, createExpense, updateExpense, removeExpense }
}
