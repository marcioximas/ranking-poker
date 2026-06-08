# ♠ Poker Night Manager

Aplicação web de gerenciamento de torneios de poker. Um único arquivo HTML auto-contido, sem dependências externas, que funciona localmente no navegador.

---

## Arquivos

```
poker_night.html   → app completo (HTML + CSS + JS em um único arquivo)
poker_data.json    → (gerado automaticamente) dados salvos pelo Python app legado
README.md          → este arquivo
```

---

## Como rodar

### Opção 1 — Abrir direto no navegador
Abra o `poker_night.html` no Chrome. **Atenção:** o Chrome bloqueia algumas features em `file://`. Para evitar problemas, use a Opção 2.

### Opção 2 — Servidor local (recomendado)
```bash
# Python
python -m http.server 8080

# Node
npx serve .
```
Acesse: `http://localhost:8080/poker_night.html`

---

## Funcionalidades

### 1. Rodada Atual
- Adicionar / editar / remover jogadores
- Campos por jogador:
  - **Buy-in / Rebuys** (numérico)
  - **Addon** (Sim/Não → valor configurável)
  - **Pontos** (chips finais)
  - **Presença** (Sim/Não → padrão: 10 pts)
  - **Bônus ITM** (Sim/Não → padrão: 5 pts)
  - **Indicação** (Sim/Não → 25 pts fixo)
  - **Pontualidade** (Sim/Não → padrão: 15 pts)
- Total calculado automaticamente: `pontos + presença + bonus + indicação + pontualidade`
- Ranking da rodada em tempo real com medalhas 🥇🥈🥉
- Cards de resumo: jogadores, buy-ins, addons, caixa da noite, líder

### 2. Finalizar Rodada
- Botão **✓ Finalizar Rodada** abre modal pedindo a data
- Valida se já existe rodada cadastrada com a mesma data
- Salva os pontos de cada jogador na coluna correta do Ranking Semestral
- Exibe resultado final com premiação (1º = 70%, 2º = 30%)

### 3. Ranking Semestral
- Tabela com todos os jogadores × todas as rodadas
- Pills clicáveis para filtrar quais rodadas incluir no total
- Botões **Todas / Nenhuma** para seleção rápida
- **Protegido por senha** para edição (ver seção Segurança)
- No modo edição:
  - Clicar em qualquer célula da tabela edita a pontuação
  - **+ Nova Rodada** adiciona coluna ao ranking
  - **✕ Excluir** remove uma rodada (com reindexação automática)

### 4. Financeiro *(protegido por senha)*
- Despesas cadastráveis dinamicamente (+ Adicionar / ✕ remover)
- Despesas padrão pré-cadastradas: Dealer, Maleta, Mesa, Lavagem Mesa, Cadeiras, Baralho, TV c/ Suporte, Câmera
- Campos editáveis: Caixa Anterior, Ranking Anterior
- Cálculo automático:
  - Caixa da noite = (total buy-ins × R$ buy-in) + (total addons × R$ addon)
  - Caixa Atual = Caixa Anterior + Caixa da noite
  - Premiação = Caixa da noite × % premiação
  - Ranking noite = Caixa da noite × % ranking
  - Ranking Total = Ranking Anterior + Ranking noite
  - Caixa c/ Despesas = Caixa Atual − Total Despesas

### 5. Configurações *(protegida por senha)*
- Nome do torneio
- Valor Buy-in / Rebuy (padrão: R$ 50)
- Valor Addon (padrão: R$ 50)
- Pontos Presença (padrão: 10)
- Pontos Pontualidade (padrão: 15)
- Bônus ITM em pontos (padrão: 5)
- % Premiação da noite (padrão: 70%)
- % Ranking da noite (padrão: 30%)

---

## Segurança / Senhas

Áreas protegidas (Ranking Semestral, Financeiro, Configurações) exigem senha de administrador.

A senha é definida via variável de ambiente `ADMIN_PASSWORD` no servidor. Nunca commite a senha no repositório.

O botão **🔒 Bloquear** no header bloqueia todas as áreas de uma vez.

---

## Dados (localStorage)

Os dados são salvos automaticamente no `localStorage` do navegador com a chave:
```
poker_night_v5
```

Estrutura do estado (`S`):
```js
{
  players: [],           // jogadores da rodada atual
  nextId: 1,             // contador de IDs
  selectedId: null,      // jogador selecionado na tabela
  despesas: {},          // objeto chave:valor das despesas
  finCxAnt: 3868.23,     // caixa anterior
  finRkAnt: 1621.25,     // ranking anterior
  rounds: [...],         // lista de rodadas { id, label }
  activeRounds: [...],   // IDs das rodadas visíveis no ranking
  semestral: {},         // { "Nome": [pts_r1, pts_r2, ...] }
  rankEditMode: false,   // modo edição do ranking
  unlockedPanels: [],    // painéis desbloqueados na sessão
  currentRoundId: null,  // ID da rodada em andamento
  currentRoundLabel: '', // label da rodada em andamento
  currentRoundDate: '',  // data da rodada em andamento (YYYY-MM-DD)
}
```

**Para resetar tudo:** abrir o DevTools → Application → Local Storage → deletar a chave `poker_night_v5`.

**Para mudar a versão** (forçar reset após atualização):
```js
// buscar no código:
localStorage.getItem('poker_night_v5')
localStorage.setItem('poker_night_v5', ...)
// trocar v5 por v6
```

---

## Dados do 1º Semestre 2026

O ranking já vem pré-carregado com 19 rodadas (07/01 a 13/05/2026) e 16 jogadores:

| Jogador | Total |
|---------|-------|
| Mateus | 1143 |
| Henrique | 825 |
| China | 805 |
| Ximas | 709 |
| Deivid | 686 |
| Morais | 558 |
| Danilo Vieira | 557 |
| Andre | 313 |
| Joel | 110 |
| Rafael | 75 |
| Marcelo | 63 |
| Chamma | 50 |
| Comando | 45 |
| Para | 25 |
| Cicero | 25 |
| Claudinho | 25 |

---

## Melhorias sugeridas para o futuro

- [ ] Migrar para backend (Node.js + SQLite ou Supabase) para dados compartilhados entre dispositivos
- [ ] Exportar ranking como PDF ou imagem para compartilhar no WhatsApp
- [ ] Histórico de rodadas anteriores (2025, etc.)
- [ ] Notificação de novo líder ao finalizar rodada
- [ ] PWA (Progressive Web App) para instalar no celular
- [ ] Múltiplos torneios / semestres

---

## Histórico de desenvolvimento

Projeto criado via Claude (claude.ai), migrado para Claude Code.
Última versão: `poker_night_v5` no localStorage.
