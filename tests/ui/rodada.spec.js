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

async function ensurePlayer(apiContext, name, pix) {
  const listRes = await apiContext.get(`${API}/players`)
  const players = await listRes.json()
  const existing = players.find((p) => p.name === name)
  if (existing) {
    await apiContext.put(`${API}/players/${existing.id}`, {
      data: { name, pix },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
    return existing.id
  }

  const created = await apiContext.post(`${API}/players`, {
    data: { name, pix },
    headers: { 'X-Admin-Password': ADMIN_PASSWORD },
  })
  return (await created.json()).id
}

async function openAuthAndSubmit(page) {
  const authInput = page.locator('#auth-password')
  if ((await authInput.count()) === 0) return
  await authInput.fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
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

  test('ao trancar rodada gera PIX de cobrança para todos os jogadores no admin configurado', async ({ page }) => {
    const api = await request.newContext()
    await deleteCurrentRound(api)

    const stamp = Date.now()
    const receiverName = `Admin Pix ${stamp}`
    const p1Name = `Jogador Cobranca 1 ${stamp}`
    const p2Name = `Jogador Cobranca 2 ${stamp}`

    const receiverId = await ensurePlayer(api, receiverName, 'admin-chave-pix')
    const p1Id = await ensurePlayer(api, p1Name, 'pix-jogador-1')
    const p2Id = await ensurePlayer(api, p2Name, 'pix-jogador-2')

    await api.put(`${API}/config`, {
      data: {
        tournament_name: 'Poker Night',
        buyin_value: 50,
        rebuy_value: 50,
        addon_value: 50,
        presence_points: 10,
        punctuality_points: 15,
        itm_bonus_points: 5,
        prize_pct: 70,
        ranking_pct: 30,
        pix_receiver_player_id: receiverId,
      },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })

    const roundRes = await api.post(`${API}/rounds/current`, {
      data: { label: `Rodada PIX Cobranca ${stamp}` },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
    const roundId = (await roundRes.json()).id

    await api.post(`${API}/rounds/${roundId}/players`, {
      data: { player_id: p1Id, buyin: 1, rebuy: 1, addon: 1 },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
    await api.post(`${API}/rounds/${roundId}/players`, {
      data: { player_id: p2Id, buyin: 1, rebuy: 0, addon: 0 },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })

    const app = new AppPage(page)
    await app.goto()

    await page.getByRole('button', { name: '🔒 Trancar Rodada' }).click()
    await openAuthAndSubmit(page)

    const chargesHeader = page.getByText(`Cobranças PIX — ${receiverName}`).first()
    await expect(chargesHeader).toBeVisible()
    const chargesTable = chargesHeader.locator('xpath=following::table[1]')
    await expect(chargesTable.getByRole('columnheader', { name: 'Código PIX (Copia e Cola)' })).toBeVisible()
    await expect(chargesTable.locator('tbody tr').filter({ hasText: p1Name }).first()).toContainText('R$ 150,00')
    await expect(chargesTable.locator('tbody tr').filter({ hasText: p2Name }).first()).toContainText('R$ 50,00')
    await expect(chargesTable.locator('tbody tr').filter({ hasText: p1Name }).first().locator('input[readonly]')).toHaveValue(/000201/)
    await expect(chargesTable.locator('tbody tr').filter({ hasText: p2Name }).first().locator('input[readonly]')).toHaveValue(/000201/)

    await deleteCurrentRound(api)
    await api.dispose()
  })

  test('ao trancar rodada gera PIX de cobrança mesmo sem recebedor configurado (fallback)', async ({ page }) => {
    const api = await request.newContext()
    await deleteCurrentRound(api)

    const stamp = Date.now()
    const p1Name = `Fallback Cobranca 1 ${stamp}`
    const p2Name = `Fallback Cobranca 2 ${stamp}`

    const p1Id = await ensurePlayer(api, p1Name, 'pix-fallback-1')
    const p2Id = await ensurePlayer(api, p2Name, 'pix-fallback-2')

    await api.put(`${API}/config`, {
      data: {
        tournament_name: 'Poker Night',
        buyin_value: 50,
        rebuy_value: 50,
        addon_value: 50,
        presence_points: 10,
        punctuality_points: 15,
        itm_bonus_points: 5,
        prize_pct: 70,
        ranking_pct: 30,
        pix_receiver_player_id: null,
      },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })

    const roundRes = await api.post(`${API}/rounds/current`, {
      data: { label: `Rodada PIX Fallback ${stamp}` },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
    const roundId = (await roundRes.json()).id

    await api.post(`${API}/rounds/${roundId}/players`, {
      data: { player_id: p1Id, buyin: 1, rebuy: 1, addon: 0 },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
    await api.post(`${API}/rounds/${roundId}/players`, {
      data: { player_id: p2Id, buyin: 1, rebuy: 0, addon: 1 },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })

    const app = new AppPage(page)
    await app.goto()

    await page.getByRole('button', { name: '🔒 Trancar Rodada' }).click()
    await openAuthAndSubmit(page)

    const chargesHeader = page.locator('p', { hasText: 'Cobranças PIX' }).first()
    await expect(chargesHeader).toBeVisible()
    const chargesTable = chargesHeader.locator('xpath=following::table[1]')
    await expect(chargesTable.getByRole('columnheader', { name: 'Código PIX (Copia e Cola)' })).toBeVisible()
    await expect(chargesTable.locator('tbody tr').filter({ hasText: p1Name }).first()).toContainText('R$ 100,00')
    await expect(chargesTable.locator('tbody tr').filter({ hasText: p2Name }).first()).toContainText('R$ 100,00')
    await expect(chargesTable.locator('tbody tr').filter({ hasText: p1Name }).first().locator('input[readonly]')).toHaveValue(/000201/)
    await expect(chargesTable.locator('tbody tr').filter({ hasText: p2Name }).first().locator('input[readonly]')).toHaveValue(/000201/)

    await deleteCurrentRound(api)
    await api.dispose()
  })

  test('ao finalizar rodada gera PIX de premiação com os ganhadores', async ({ page }) => {
    const api = await request.newContext()
    await deleteCurrentRound(api)

    const stamp = Date.now()
    const receiverId = await ensurePlayer(api, `Admin Prem ${stamp}`, 'admin-prem-pix')
    const p1Name = `Ganhar 1 ${stamp}`
    const p2Name = `Ganhar 2 ${stamp}`
    const p1Id = await ensurePlayer(api, p1Name, 'pix-ganhador-1')
    const p2Id = await ensurePlayer(api, p2Name, 'pix-ganhador-2')

    await api.put(`${API}/config`, {
      data: {
        tournament_name: 'Poker Night',
        buyin_value: 50,
        rebuy_value: 50,
        addon_value: 50,
        presence_points: 10,
        punctuality_points: 15,
        itm_bonus_points: 5,
        prize_pct: 70,
        ranking_pct: 30,
        pix_receiver_player_id: receiverId,
      },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })

    const roundRes = await api.post(`${API}/rounds/current`, {
      data: { label: `Rodada PIX Premiacao ${stamp}` },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
    const roundId = (await roundRes.json()).id

    await api.post(`${API}/rounds/${roundId}/players`, {
      data: { player_id: p1Id, buyin: 1, rebuy: 0, addon: 0, colocacao: 1 },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })
    await api.post(`${API}/rounds/${roundId}/players`, {
      data: { player_id: p2Id, buyin: 1, rebuy: 0, addon: 0, colocacao: 2 },
      headers: { 'X-Admin-Password': ADMIN_PASSWORD },
    })

    const app = new AppPage(page)
    await app.goto()

    await page.getByRole('button', { name: '🔒 Trancar Rodada' }).click()
    await openAuthAndSubmit(page)

    await page.getByRole('button', { name: '✓ Finalizar Rodada' }).click()
    await expect(page.getByRole('heading', { name: 'Finalizar Rodada' })).toBeVisible()

    await page.getByRole('button', { name: '✓ Confirmar e Salvar' }).click()
    await expect(page.getByRole('heading', { name: 'Rodada Finalizada!' })).toBeVisible()
    const prizeTitle = page.getByText('Premiação via PIX').first()
    await expect(prizeTitle).toBeVisible()
    await expect(page.locator('.fin-row').filter({ hasText: `${p1Name} 🥇` }).first()).toContainText('R$ 59,50')
    await expect(page.locator('.fin-row').filter({ hasText: `${p2Name} 🥈` }).first()).toContainText('R$ 25,50')

    await api.dispose()
  })
})
