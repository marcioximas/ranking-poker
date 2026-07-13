import { test, expect, request } from '@playwright/test'
import { AppPage, RodadaPage } from './pages.js'

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'Ximas2026@'
const API = 'http://localhost:8000/api'

async function deleteCurrentRound(apiContext) {
  const res = await apiContext.get(`${API}/rounds/current`)
  if (!res.ok()) return
  const round = await res.json()
  if (!round?.id) return
  await apiContext.delete(`${API}/rounds/${round.id}`, {
    headers: { 'X-Admin-Password': ADMIN_PASSWORD },
  })
}

test.describe('Rodada Atual', () => {
  test.beforeEach(async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()
  })

  test('exibe estado vazio quando não há rodada em andamento', async ({ page }) => {
    const rodada = new RodadaPage(page)
    await expect(rodada.emptyMessage).toBeVisible()
    await expect(rodada.iniciarBtn).toBeVisible()
    await expect(rodada.finalizarBtn).not.toBeVisible()
  })

  test('stat cards exibem zeros quando não há rodada', async ({ page }) => {
    const statGrid = page.locator('.stat-grid')
    await expect(statGrid.getByText('JOGADORES', { exact: true })).toBeVisible()
    await expect(statGrid.getByText('0').first()).toBeVisible()
  })

  test('modal Iniciar Rodada abre ao clicar no botão', async ({ page }) => {
    const rodada = new RodadaPage(page)
    await rodada.iniciarBtn.click()

    const modal = rodada.startModal
    await expect(modal.heading).toBeVisible()
    await expect(modal.password).toBeVisible()
    await expect(modal.iniciar).toBeVisible()
  })

  test('modal Iniciar Rodada fecha ao clicar em Cancelar', async ({ page }) => {
    const rodada = new RodadaPage(page)
    await rodada.iniciarBtn.click()
    await rodada.startModal.cancelar.click()

    await expect(rodada.startModal.heading).not.toBeVisible()
    await expect(rodada.emptyMessage).toBeVisible()
  })

  test('iniciar rodada sem senha exibe erro de validação', async ({ page }) => {
    const rodada = new RodadaPage(page)
    await rodada.iniciarBtn.click()
    await rodada.startModal.iniciar.click()

    await expect(page.getByText('Informe a senha de administrador.')).toBeVisible()
    await expect(rodada.startModal.heading).toBeVisible()
  })

  test('iniciar rodada com senha errada exibe erro', async ({ page }) => {
    const rodada = new RodadaPage(page)
    await rodada.iniciarBtn.click()
    await rodada.startModal.password.fill('senha-errada')
    await rodada.startModal.iniciar.click()

    await expect(page.getByText('Senha incorreta.')).toBeVisible()
    await expect(rodada.startModal.heading).toBeVisible()
  })

  test('Enter no campo de senha submete o formulário', async ({ page }) => {
    const rodada = new RodadaPage(page)
    await rodada.iniciarBtn.click()
    await rodada.startModal.password.fill('senha-errada')
    await rodada.startModal.password.press('Enter')

    await expect(page.getByText('Senha incorreta.')).toBeVisible()
  })

  test('ciclo completo: iniciar rodada com senha correta', async ({ page }) => {
    const api = await request.newContext()
    await deleteCurrentRound(api)  // garante estado limpo

    const rodada = new RodadaPage(page)
    await page.reload()
    await rodada.iniciarBtn.click()

    const modal = rodada.startModal
    await modal.label.fill('Rodada Teste Playwright')
    await modal.password.fill(ADMIN_PASSWORD)
    await modal.iniciar.click()

    // Modal fecha e a toolbar da rodada aparece
    await expect(modal.heading).not.toBeVisible()
    await expect(rodada.adicionarBtn).toBeVisible()
    await expect(rodada.finalizarBtn).toBeVisible()

    // Cleanup: remove a rodada criada pelo teste
    await deleteCurrentRound(api)
    await api.dispose()
  })
})
