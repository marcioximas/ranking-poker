import { test, expect, request } from '@playwright/test'
import { AppPage, AuthModal } from './pages.js'

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'Ximas2026@'
const API = 'http://localhost:8000/api'

async function navigateToFinanceiro(page) {
  const app = new AppPage(page)
  const auth = new AuthModal(page)
  await app.goto()
  await app.nav.financeiro.click()
  await auth.fillAndSubmit(ADMIN_PASSWORD)
  await expect(page.getByText('RESUMO FINANCEIRO')).toBeVisible()
}

async function cleanupExpense(name) {
  const api = await request.newContext()
  const expenses = await (await api.get(`${API}/expenses`)).json()
  const exp = expenses.find(e => e.name === name)
  if (exp) {
    await api.delete(`${API}/expenses/${exp.id}`, {
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
  }
  await api.dispose()
}

test.describe('Financeiro', () => {
  test('exige autenticação para acessar', async ({ page }) => {
    const app = new AppPage(page)
    const auth = new AuthModal(page)
    await app.goto()
    await app.nav.financeiro.click()
    await expect(auth.modal).toBeVisible()
  })

  test('exibe seções principais após autenticação', async ({ page }) => {
    await navigateToFinanceiro(page)
    await expect(page.getByText('DESPESAS')).toBeVisible()
    await expect(page.getByText('HISTÓRICO')).toBeVisible()
    await expect(page.getByText('RESUMO FINANCEIRO')).toBeVisible()
    await expect(page.getByText('PREMIAÇÃO DA NOITE').first()).toBeVisible()
  })

  test('exibe stat cards financeiros', async ({ page }) => {
    await navigateToFinanceiro(page)
    await expect(page.getByText('CAIXA ATUAL')).toBeVisible()
    await expect(page.getByText('RANKING TOTAL')).toBeVisible()
    await expect(page.getByText('CAIXA C/ DESPESAS')).toBeVisible()
  })

  test('exibe campos de histórico editáveis', async ({ page }) => {
    await navigateToFinanceiro(page)
    await expect(page.getByLabel('Caixa Anterior (R$)')).toBeVisible()
    await expect(page.getByLabel('Ranking Anterior (R$)')).toBeVisible()
  })

  test('exibe prêmios 1º e 2º lugar no resumo', async ({ page }) => {
    await navigateToFinanceiro(page)
    await expect(page.getByText('🥇 1º lugar (70%)')).toBeVisible()
    await expect(page.getByText('🥈 2º lugar (30%)')).toBeVisible()
  })

  test('botão + Adicionar abre modal Nova Despesa', async ({ page }) => {
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar' }).click()
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).toBeVisible()
    await expect(page.getByPlaceholder('ex: Mesa, Fichas, Bebida...')).toBeVisible()
  })

  test('modal Nova Despesa valida nome obrigatório', async ({ page }) => {
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar' }).click()
    await page.getByRole('button', { name: 'Adicionar' }).click()
    await expect(page.getByText('Informe o nome da despesa.')).toBeVisible()
  })

  test('modal Nova Despesa fecha ao cancelar', async ({ page }) => {
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar' }).click()
    await page.getByRole('button', { name: 'Cancelar' }).click()
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).not.toBeVisible()
  })

  test('adiciona despesa e ela aparece na lista', async ({ page }) => {
    const expName = 'Despesa E2E Teste'
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar' }).click()
    await page.getByPlaceholder('ex: Mesa, Fichas, Bebida...').fill(expName)
    await page.getByRole('button', { name: 'Adicionar' }).click()

    await expect(page.getByText(expName)).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).not.toBeVisible()

    await cleanupExpense(expName)
  })

  test('despesa duplicada exibe erro no modal', async ({ page }) => {
    const api = await request.newContext()
    await api.post(`${API}/expenses`, {
      data: { name: 'Despesa Duplicada', value: 10 },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })

    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar' }).click()
    await page.getByPlaceholder('ex: Mesa, Fichas, Bebida...').fill('Despesa Duplicada')
    await page.getByRole('button', { name: 'Adicionar' }).click()

    await expect(page.locator('[style*="color:var(--red)"]').filter({ hasText: /já existe|erro/i })).toBeVisible()

    await cleanupExpense('Despesa Duplicada')
    await api.dispose()
  })
})
