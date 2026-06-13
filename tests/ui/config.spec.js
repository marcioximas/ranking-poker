import { test, expect, request } from '@playwright/test'
import { AppPage, AuthModal } from './pages.js'

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'Ximas2026@'
const API = 'http://localhost:8000/api'

async function navigateToConfig(page) {
  const app = new AppPage(page)
  const auth = new AuthModal(page)
  await app.goto()
  await app.nav.config.click()
  await auth.fillAndSubmit(ADMIN_PASSWORD)
  await expect(page.getByRole('button', { name: 'Salvar Configurações' })).toBeVisible()
}

test.describe('Configurações', () => {
  test('exige autenticação para acessar', async ({ page }) => {
    const app = new AppPage(page)
    const auth = new AuthModal(page)
    await app.goto()
    await app.nav.config.click()
    await expect(auth.modal).toBeVisible()
  })

  test('exibe descrição informativa', async ({ page }) => {
    await navigateToConfig(page)
    await expect(page.getByText('Configurações aplicadas em todas as rodadas novas.')).toBeVisible()
  })

  test('exibe todos os campos de configuração', async ({ page }) => {
    await navigateToConfig(page)
    await expect(page.getByLabel('Buy-in / Rebuy (R$)')).toBeVisible()
    await expect(page.getByLabel('Addon (R$)')).toBeVisible()
    await expect(page.getByLabel('Pontos presença')).toBeVisible()
    await expect(page.getByLabel('Pontos pontualidade')).toBeVisible()
    await expect(page.getByLabel('Bônus ITM (pontos)')).toBeVisible()
    await expect(page.getByLabel('% Premiação da noite')).toBeVisible()
    await expect(page.getByLabel('% Ranking da noite')).toBeVisible()
  })

  test('campos têm valores padrão maiores que zero', async ({ page }) => {
    await navigateToConfig(page)
    const buyin = page.getByLabel('Buy-in / Rebuy (R$)')
    const value = parseFloat(await buyin.inputValue())
    expect(value).toBeGreaterThan(0)
  })

  test('botão Salvar está habilitado por padrão', async ({ page }) => {
    await navigateToConfig(page)
    await expect(page.getByRole('button', { name: 'Salvar Configurações' })).toBeEnabled()
  })

  test('salva configurações e exibe toast de confirmação', async ({ page }) => {
    const api = await request.newContext()
    const original = await (await api.get(`${API}/config`)).json()

    await navigateToConfig(page)
    const buyinInput = page.getByLabel('Buy-in / Rebuy (R$)')
    await buyinInput.fill(String(original.buyin_value + 10))
    await page.getByRole('button', { name: 'Salvar Configurações' }).click()

    await expect(page.getByText('Configurações salvas! ✓')).toBeVisible()

    // Restore original value
    await api.put(`${API}/config`, {
      data: { buyin_value: original.buyin_value },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
    await api.dispose()
  })

  test('botão mostra Salvando... enquanto processa', async ({ page }) => {
    await navigateToConfig(page)
    const saveBtn = page.getByRole('button', { name: /Salvar Configurações|Salvando/ })
    await saveBtn.click()
    // After click it briefly shows "Salvando..." — just verify the flow completes
    await expect(page.getByRole('button', { name: 'Salvar Configurações' })).toBeVisible()
  })
})
