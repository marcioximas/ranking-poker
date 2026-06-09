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

  test('Financeiro exige autenticação antes de abrir', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.financeiro.click()

    const auth = new AuthModal(page)
    await expect(auth.modal).toBeVisible()
  })

  test('Configurações exige autenticação antes de abrir', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.config.click()

    const auth = new AuthModal(page)
    await expect(auth.modal).toBeVisible()
  })

  test('cancelar autenticação mantém a aba anterior', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.financeiro.click()
    const auth = new AuthModal(page)
    await auth.cancel.click()

    await expect(app.nav.rodada).toHaveAttribute('class', /active/)
  })

  test('senha incorreta exibe mensagem de erro', async ({ page }) => {
    const app = new AppPage(page)
    await app.goto()

    await app.nav.financeiro.click()
    const auth = new AuthModal(page)
    await auth.fillAndSubmit('senha-errada')

    await expect(auth.error).toBeVisible()
    await expect(auth.modal).toBeVisible()
  })
})
