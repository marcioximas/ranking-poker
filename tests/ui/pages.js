/**
 * Page Object Models for Poker Night Manager.
 * Each class wraps a specific view with semantic locators and actions.
 */

export class AppPage {
  constructor(page) {
    this.page = page
    this.nav = {
      rodada:     page.getByRole('button', { name: 'Rodada Atual', exact: true }),
      ranking:    page.getByRole('button', { name: 'Ranking Semestral', exact: true }),
      financeiro: page.getByRole('button', { name: 'Financeiro', exact: true }),
      config:     page.getByRole('button', { name: 'Configurações', exact: true }),
    }
  }

  async goto() {
    await this.page.goto('/')
  }
}

export class AuthModal {
  constructor(page) {
    this.page = page
    this.modal   = page.getByRole('heading', { name: 'Autenticação' })
    this.input   = page.locator('#auth-password')
    this.submit  = page.getByRole('button', { name: 'Entrar' })
    this.cancel  = page.getByRole('button', { name: 'Cancelar' })
    this.error   = page.getByText('Senha incorreta.')
  }

  async fillAndSubmit(password) {
    const hasModal = (await this.input.count()) > 0
    if (!hasModal) return
    await this.input.fill(password)
    await this.submit.click()
  }
}

export class RodadaPage {
  constructor(page) {
    this.page = page
    this.iniciarBtn    = page.getByRole('button', { name: '+ Iniciar Rodada' })
    this.finalizarBtn  = page.getByRole('button', { name: '✓ Finalizar Rodada' })
    this.adicionarBtn  = page.getByRole('button', { name: '+ Adicionar Jogador' })
    this.emptyMessage  = page.getByText('Nenhuma rodada em andamento.')
  }

  get startModal() {
    const page = this.page
    return {
      heading:  page.getByRole('heading', { name: 'Iniciar Rodada' }),
      date:     page.locator('#start-label').locator('..').locator('input[type="date"]'),
      label:    page.locator('#start-label'),
      password: page.locator('#start-password'),
      iniciar:  page.getByRole('button', { name: 'Iniciar', exact: true }),
      cancelar: page.getByRole('button', { name: 'Cancelar' }),
      error:    page.locator('[style*="color:var(--red)"]').first(),
    }
  }
}

export class RankingPage {
  constructor(page) {
    this.page = page
    this.todasBtn      = page.getByRole('button', { name: 'Todas' })
    this.nenhumaBtn    = page.getByRole('button', { name: 'Nenhuma' })
    this.desbloquear   = page.getByRole('button', { name: 'Desbloquear' })
    this.bloquear      = page.getByRole('button', { name: 'Bloquear', exact: true })
    this.table         = page.getByRole('table')
    this.rodadasLabel  = page.getByText(/RODADAS VISÍVEIS/)
  }

  roundPill(label) {
    return this.page.getByText(label, { exact: true })
  }

  statCard(label) {
    return this.page.locator('.stat-grid').getByText(label)
  }
}
