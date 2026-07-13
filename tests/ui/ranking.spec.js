import { test, expect } from '@playwright/test'
import { AppPage, RankingPage } from './pages.js'

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'Ximas2026@'

test.describe('Ranking Semestral', () => {
  test.beforeEach(async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()
    await app.nav.ranking.click()
  })

  test('exibe todas as rodadas por padrão sem autenticação', async ({ page }) => {
    const ranking = new RankingPage(page)

    // Counter deve mostrar total/total (todas visíveis por padrão)
    const counter = page.locator('.stat-grid').first()
    await expect(counter).toContainText(/\d+ \/ \d+/)

    // Deve ter pelo menos uma linha de dados no ranking (header + dados)
    const rowCount = await ranking.table.getByRole('row').count()
    expect(rowCount).toBeGreaterThanOrEqual(2)

    await expect(ranking.table.getByRole('columnheader', { name: 'Buy-ins' })).toBeVisible()
    await expect(ranking.table.getByRole('columnheader', { name: 'Rebuys' })).toBeVisible()
    await expect(ranking.table.getByRole('columnheader', { name: 'Addons' })).toBeVisible()
  })

  test('ordena colunas de rodada da menor para maior e deixa Total por último', async ({ page }) => {
    const ranking = new RankingPage(page)
    const headers = (await ranking.table.locator('thead th').allTextContents())
      .map((text) => text.trim())
      .filter(Boolean)

    const totalIndex = headers.lastIndexOf('Total')
    expect(totalIndex).toBe(headers.length - 1)

    const roundNumbers = headers
      .filter((text) => /^Rodada\s+\d+/i.test(text))
      .map((text) => {
        const match = text.match(/Rodada\s+(\d+)/i)
        return match ? parseInt(match[1], 10) : null
      })
      .filter((n) => Number.isFinite(n))

    const sorted = [...roundNumbers].sort((a, b) => a - b)
    expect(roundNumbers).toEqual(sorted)
  })

  test('filtra rodadas localmente clicando nos pills sem precisar de auth', async ({ page }) => {
    const ranking = new RankingPage(page)

    // Pega o counter antes de filtrar
    const counterBefore = await page.locator('.stat-grid').first()
      .locator('.stat-card').first().textContent()

    // Clica em "Nenhuma" — deve zerar sem pedir senha
    await ranking.nenhumaBtn.click()
    await expect(page.locator('.stat-grid').first()).toContainText('0 /')

    // Clica em "Todas" — restaura
    await ranking.todasBtn.click()
    await expect(page.locator('.stat-grid').first()).not.toContainText('0 /')
  })

  test('pill de rodada individual alterna visibilidade da coluna', async ({ page }) => {
    const ranking = new RankingPage(page)

    // Seleciona nenhuma primeiro, depois ativa uma única rodada
    await ranking.nenhumaBtn.click()
    const pill = page.locator('.round-pill').first()
    const pillText = await pill.textContent()
    await pill.click()

    await expect(page.locator('.stat-grid').first()).toContainText('1 /')
    // A coluna da rodada deve aparecer na tabela
    await expect(ranking.table).toContainText(pillText.trim())
  })

  test('modo de edição exige autenticação', async ({ page }) => {
    const ranking = new RankingPage(page)
    await ranking.desbloquear.click()

    await expect(page.getByRole('heading', { name: 'Autenticação' })).toBeVisible()
  })

  test('modo de edição abre após autenticação correta', async ({ page }) => {
    const ranking = new RankingPage(page)
    await ranking.desbloquear.click()

    await page.locator('#auth-password').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page.getByText('🔓 Modo edição')).toBeVisible()
    await expect(page.getByRole('button', { name: '+ Nova Rodada' })).toBeVisible()
  })

  test('botão Bloquear sai do modo de edição', async ({ page }) => {
    const ranking = new RankingPage(page)

    // Autentica
    await ranking.desbloquear.click()
    await page.locator('#auth-password').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Entrar' }).click()
    await expect(page.getByText('🔓 Modo edição')).toBeVisible()

    // Bloqueia via toolbar do ranking
    await page.getByRole('button', { name: 'Bloquear', exact: true }).first().click()
    await expect(page.getByText('🔒 Edição bloqueada')).toBeVisible()
  })

  test('pontuações somam corretamente para as rodadas selecionadas', async ({ page }) => {
    const ranking = new RankingPage(page)

    // Remove todas as rodadas e valida total zero
    await ranking.nenhumaBtn.click()
    const totalCells = ranking.table.locator('td.total')
    for (const cell of await totalCells.all()) {
      await expect(cell).toHaveText('0')
    }

    // Ativa todas e verifica que o total do líder é > 0
    await ranking.todasBtn.click()
    const leaderTotal = totalCells.first()
    const text = await leaderTotal.textContent()
    expect(parseInt(text, 10)).toBeGreaterThan(0)
  })
})
