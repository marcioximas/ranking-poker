import { test, expect } from '@playwright/test'
import { AppPage, AuthModal } from './pages.js'

test.describe('Navegação principal', () => {
  test('carrega a página inicial na aba Rodada Atual', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await expect(page).toHaveTitle(/Poker Night/)
    await expect(app.nav.rodada).toHaveAttribute('class', /active/)
    await expect(page.getByText('Nenhuma rodada em andamento.')).toBeVisible()
  })

  test('navega para Ranking Semestral sem autenticação', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.ranking.click()
    await expect(app.nav.ranking).toHaveAttribute('class', /active/)
    await expect(page.getByRole('table')).toBeVisible()
  })

  test('Financeiro abre sem autenticação inicial', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.financeiro.click()
    await expect(app.nav.financeiro).toHaveAttribute('class', /active/)
    await expect(page.getByText('RESUMO FINANCEIRO')).toBeVisible()
  })

  test('Configurações abre sem autenticação inicial', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.config.click()
    await expect(app.nav.config).toHaveAttribute('class', /active/)
    await expect(page.getByRole('button', { name: 'Salvar Configurações' })).toBeVisible()
  })

  test('cancelar autenticação mantém a aba atual', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.financeiro.click()
    await page.getByRole('button', { name: '+ Adicionar' }).click()
    const auth = new AuthModal(page)
    await auth.cancel.click()

    await expect(app.nav.financeiro).toHaveAttribute('class', /active/)
  })

  test('senha incorreta exibe mensagem de erro', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.financeiro.click()
    await page.getByRole('button', { name: '+ Adicionar' }).click()
    const auth = new AuthModal(page)
    await auth.fillAndSubmit('senha-errada')

    await expect(auth.error).toBeVisible()
    await expect(auth.modal).toBeVisible()
  })
})
