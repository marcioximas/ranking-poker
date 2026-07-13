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
  test('acessa a aba sem autenticação inicial', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()
    await app.nav.financeiro.click()
    await expect(app.nav.financeiro).toHaveAttribute('class', /active/)
    await expect(page.getByText('RESUMO FINANCEIRO')).toBeVisible()
  })

  test('exibe seções principais após autenticação', async ({ page }) => {
    await navigateToFinanceiro(page)
    await expect(page.getByText('DESPESAS', { exact: true })).toBeVisible()
    await expect(page.getByText('HISTÓRICO', { exact: true })).toBeVisible()
    await expect(page.getByText('RESUMO FINANCEIRO', { exact: true })).toBeVisible()
    await expect(page.locator('.fin-section-title', { hasText: 'PREMIAÇÃO DA NOITE' })).toBeVisible()
  })

  test('exibe stat cards financeiros', async ({ page }) => {
    await navigateToFinanceiro(page)
    await expect(page.locator('.stat-grid').getByText('CAIXA ATUAL', { exact: true })).toBeVisible()
    await expect(page.locator('.stat-grid').getByText('RANKING TOTAL', { exact: true })).toBeVisible()
    await expect(page.locator('.stat-grid').getByText('CAIXA C/ DESPESAS', { exact: true })).toBeVisible()
  })

  test('exibe seção de histórico', async ({ page }) => {
    await navigateToFinanceiro(page)
    await expect(page.getByText('Caixa Anterior (R$)')).toBeVisible()
    await expect(page.getByText('Ranking Anterior (R$)')).toBeVisible()
  })

  test('exibe prêmios 1º e 2º lugar no resumo', async ({ page }) => {
    await navigateToFinanceiro(page)
    await expect(page.getByText('🥇 1º lugar (70%)')).toBeVisible()
    await expect(page.getByText('🥈 2º lugar (30%)')).toBeVisible()
  })

  test('botão + Adicionar solicita autenticação quando bloqueado', async ({ page }) => {
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Autenticação' })).toBeVisible()
  })

  test('após autenticar botão + Adicionar abre modal Nova Despesa', async ({ page }) => {
    const auth = new AuthModal(page)
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar', exact: true }).click()
    await auth.fillAndSubmit(ADMIN_PASSWORD)
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).toBeVisible()
    await expect(page.getByPlaceholder('ex: Mesa, Fichas, Bebida...')).toBeVisible()
  })

  test('modal Nova Despesa valida nome obrigatório', async ({ page }) => {
    const auth = new AuthModal(page)
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar', exact: true }).click()
    await auth.fillAndSubmit(ADMIN_PASSWORD)
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).toBeVisible()
    await page.getByRole('button', { name: 'Adicionar', exact: true }).click()
    await expect(page.getByText('Informe o nome da despesa.')).toBeVisible()
  })

  test('modal Nova Despesa fecha ao cancelar', async ({ page }) => {
    const auth = new AuthModal(page)
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar', exact: true }).click()
    await auth.fillAndSubmit(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Cancelar' }).click()
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).not.toBeVisible()
  })

  test('adiciona despesa e ela aparece na lista', async ({ page }) => {
    const auth = new AuthModal(page)
    const expName = `Despesa E2E ${Date.now()}`
    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar', exact: true }).click()
    await auth.fillAndSubmit(ADMIN_PASSWORD)
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).toBeVisible()
    await page.getByPlaceholder('ex: Mesa, Fichas, Bebida...').fill(expName)
    await page.getByRole('button', { name: 'Adicionar', exact: true }).click()

    await expect(page.locator(`label[title="${expName}"]`)).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).not.toBeVisible()

    await cleanupExpense(expName)
  })

  test('despesa duplicada exibe erro no modal', async ({ page }) => {
    const auth = new AuthModal(page)
    const api = await request.newContext()
    await api.post(`${API}/expenses`, {
      data: { name: 'Despesa Duplicada', value: 10 },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })

    await navigateToFinanceiro(page)
    await page.getByRole('button', { name: '+ Adicionar', exact: true }).click()
    await auth.fillAndSubmit(ADMIN_PASSWORD)
    await expect(page.getByRole('heading', { name: 'Nova Despesa' })).toBeVisible()
    await page.getByPlaceholder('ex: Mesa, Fichas, Bebida...').fill('Despesa Duplicada')
    await page.getByRole('button', { name: 'Adicionar', exact: true }).click()

    await expect(page.getByText(/já existe|erro/i)).toBeVisible()

    await cleanupExpense('Despesa Duplicada')
    await api.dispose()
  })
})
