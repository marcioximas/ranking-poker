import { test, expect } from '@playwright/test'

async function openDashboard(page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Dashboard', exact: true }).click()
}

test('mostra totais e curiosidades de rodadas finalizadas, incluindo empates', async ({ page }) => {
  const writes = []
  page.on('request', request => {
    if (request.url().includes('/api/') && request.method() !== 'GET') writes.push(request.method())
  })
  const rounds = [
    { id: 101, label: 'Rodada 1', is_finalized: true },
    { id: 102, label: 'Rodada 2', is_finalized: true },
    { id: 103, label: 'Em andamento', is_finalized: false },
  ]
  const entries = {
    101: [
      { player_id: 1, player_name: 'Ana', rebuy: 2, addon: 1, colocacao: 1 },
      { player_id: 2, player_name: 'Bruno', rebuy: 1, addon: 0, colocacao: 2 },
    ],
    102: [
      { player_id: 1, player_name: 'Ana', rebuy: 1, addon: 1, colocacao: 2 },
      { player_id: 2, player_name: 'Bruno', rebuy: 2, addon: 1, colocacao: 1 },
      { player_id: 3, player_name: 'Carla', rebuy: 0, addon: 0, colocacao: 3 },
    ],
  }
  await page.route(/\/api\/rounds$/, route => route.fulfill({ json: rounds }))
  await page.route(/\/api\/rounds\/\d+\/players$/, route => {
    const id = Number(route.request().url().match(/\/rounds\/(\d+)\/players$/)[1])
    return route.fulfill({ json: entries[id] || [] })
  })
  await page.route('**/api/financial', route => route.fulfill({
    json: { ranking_total: 2105, caixa_total: -300 },
  }))

  await openDashboard(page)
  await expect(page.getByRole('heading', { name: 'Dashboard da mesa' })).toBeVisible()
  await expect(page.locator('.stat-card').filter({ hasText: 'RODADAS FINALIZADAS' })).toContainText('2')
  await expect(page.locator('.stat-card').filter({ hasText: 'JOGADORES PARTICIPANTES' })).toContainText('3')
  await expect(page.locator('.stat-card').filter({ hasText: 'REBUYS NO TOTAL' })).toContainText('6')
  await expect(page.locator('.stat-card').filter({ hasText: 'ADDONS NO TOTAL' })).toContainText('3')
  await expect(page.locator('.fact-card').filter({ hasText: 'Mais rebuys' })).toContainText('Ana, Bruno')
  await expect(page.locator('.fact-card').filter({ hasText: 'Mais rebuys' })).toContainText('3 rebuys')
  await expect(page.locator('.fact-card').filter({ hasText: 'Mais participações' })).toContainText('2 rodadas')
  await expect(page.locator('.fact-card').filter({ hasText: 'Mais primeiros lugares' })).toContainText('Ana, Bruno')
  await expect(page.locator('.fact-card').filter({ hasText: 'Mais addons' })).toContainText('Ana')
  await expect(page.getByRole('heading', { name: 'Resenhas recorrentes' })).toBeVisible()
  await expect(page.locator('.chat-story').filter({ hasText: 'Quem paga a pizza?' })).toContainText('Gustavo China')
  await expect(page.locator('.chat-story').filter({ hasText: 'O Vasco do Joel' })).toContainText('Joel Felipe')
  await expect(page.locator('.chat-story').filter({ hasText: 'A Coca da mesa' })).toContainText('André Yuji')
  await expect(page.locator('.chat-story').filter({ hasText: 'Falinhas garantidas' })).toContainText('Joel Felipe')
  await expect(page.locator('.chat-story').filter({ hasText: 'Blefe em debate' })).toContainText('Deivid')
  await expect(page.locator('.chat-story').filter({ hasText: 'Blefe em debate' })).toContainText('Matheus Morais')
  await expect(page.getByText('Números inventados para brincar, não são registros reais.')).toBeVisible()
  await expect(page.locator('.joke-card').filter({ hasText: 'Falinhas na mesa' })).toContainText('26 falinhas')
  await expect(page.locator('.joke-card').filter({ hasText: 'Blefes mal passados' })).toContainText('8 blefes')
  await expect(page.locator('.joke-card').filter({ hasText: 'Histórias mal contadas' })).toContainText('6 histórias')
  await expect(page.locator('.joke-card').filter({ hasText: 'Coca Zero do André Japa' })).toContainText('8 litros')
  await expect(page.locator('.joke-card').filter({ hasText: 'Coca Zero do André Japa' })).toContainText('4 garrafas de 2 L')
  await expect(page.locator('.stat-card').filter({ hasText: 'RANKING FINANCEIRO' })).toContainText('2.105,00')
  await expect(page.locator('.stat-card').filter({ hasText: 'CAIXA APÓS DESPESAS' })).toContainText('-R$')
  expect(writes).toEqual([])
})

test('mostra estado vazio sem inventar líderes', async ({ page }) => {
  await page.route(/\/api\/rounds$/, route => route.fulfill({ json: [] }))
  await page.route('**/api/financial', route => route.fulfill({ json: { ranking_total: 0, caixa_total: 0 } }))
  await openDashboard(page)
  await expect(page.getByText('Ainda não há participações registradas em rodadas finalizadas.')).toBeVisible()
  await expect(page.locator('.fact-card:not(.joke-card):not(.chat-story)')).toHaveCount(0)
  await expect(page.locator('.joke-card').filter({ hasText: 'Coca Zero do André Japa' })).toContainText('0 litros')
})

test('permite tentar novamente quando os dados não carregam', async ({ page }) => {
  await page.route(/\/api\/rounds$/, route => route.fulfill({ json: [] }))
  await page.route(/\/api\/rounds$/, route => route.fulfill({ status: 503, json: { detail: 'Erro' } }), { times: 1 })
  await page.route('**/api/financial', route => route.fulfill({ json: { ranking_total: 0, caixa_total: 0 } }))
  await openDashboard(page)
  await expect(page.getByRole('alert')).toContainText('Não foi possível carregar o dashboard.')
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByText('Ainda não há participações registradas em rodadas finalizadas.')).toBeVisible()
})
