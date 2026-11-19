<template>
  <section class="dashboard">
    <div class="dashboard-heading">
      <div>
        <p class="eyebrow">♠ POKER NIGHT</p>
        <h1>Dashboard da mesa</h1>
        <p class="subtitle">Números e curiosidades de todas as rodadas finalizadas.</p>
      </div>
      <button class="btn btn-ghost btn-sm" @click="load" :disabled="loading">↻ Atualizar</button>
    </div>

    <div v-if="loading" class="empty" role="status">Carregando dashboard...</div>
    <div v-else-if="error" class="empty" role="alert">
      <p>{{ error }}</p>
      <button class="btn btn-ghost" @click="load">Tentar novamente</button>
    </div>
    <template v-else>
      <div class="stat-grid">
        <StatCard label="RODADAS FINALIZADAS" :value="rounds.length" variant="white" />
        <StatCard label="JOGADORES PARTICIPANTES" :value="players.length" variant="white" />
        <StatCard label="REBUYS NO TOTAL" :value="totalRebuys" />
        <StatCard label="ADDONS NO TOTAL" :value="totalAddons" />
      </div>

      <div class="section-header">
        <div>
          <p class="eyebrow">OS DESTAQUES DA MESA</p>
          <h2>Curiosidades</h2>
        </div>
        <span>Empates aparecem juntos</span>
      </div>
      <div v-if="!players.length" class="empty">Ainda não há participações registradas em rodadas finalizadas.</div>
      <div v-else class="facts-grid">
        <article v-for="fact in facts" :key="fact.title" class="fact-card">
          <span class="fact-icon" aria-hidden="true">{{ fact.icon }}</span>
          <p class="fact-title">{{ fact.title }}</p>
          <p class="fact-names">{{ fact.names }}</p>
          <p class="fact-value">{{ fact.description }}</p>
        </article>
      </div>

      <div class="section-header">
        <div>
          <p class="eyebrow">MEMÓRIAS DA MESA</p>
          <h2>Resenhas recorrentes</h2>
        </div>
      </div>
      <p class="jokes-note">Inspirado no chat do grupo: os fatos são reais, o tempero é por conta da resenha.</p>
      <div class="facts-grid">
        <article v-for="story in stories" :key="story.title" class="fact-card chat-story">
          <span class="fact-icon" aria-hidden="true">{{ story.icon }}</span>
          <p class="fact-title">{{ story.title }}</p>
          <p class="fact-names">{{ story.description }}</p>
        </article>
      </div>

      <div class="section-header">
        <div>
          <p class="eyebrow">RESENHA DA MESA</p>
          <h2>Estatísticas da zoeira</h2>
        </div>
      </div>
      <p class="jokes-note">Números inventados para brincar, não são registros reais.</p>
      <div class="facts-grid">
        <article class="fact-card joke-card">
          <span class="fact-icon" aria-hidden="true">💬</span>
          <p class="fact-title">Falinhas na mesa</p>
          <p class="fact-names">{{ rounds.length * 13 }} falinhas</p>
          <p class="fact-value">13 por rodada, na imaginação</p>
        </article>
        <article class="fact-card joke-card">
          <span class="fact-icon" aria-hidden="true">🎭</span>
          <p class="fact-title">Blefes mal passados</p>
          <p class="fact-names">{{ rounds.length * 4 }} blefes</p>
          <p class="fact-value">4 por rodada, quem nunca?</p>
        </article>
        <article class="fact-card joke-card">
          <span class="fact-icon" aria-hidden="true">📖</span>
          <p class="fact-title">Histórias mal contadas</p>
          <p class="fact-names">{{ rounds.length * 3 }} histórias</p>
          <p class="fact-value">3 por rodada, segundo a lenda</p>
        </article>
        <article class="fact-card joke-card">
          <span class="fact-icon" aria-hidden="true">🥤</span>
          <p class="fact-title">Coca Zero do André Japa</p>
          <p class="fact-names">{{ rounds.length * 4 }} litros</p>
          <p class="fact-value">{{ rounds.length * 2 }} garrafas de 2 L — 2 por rodada finalizada</p>
        </article>
      </div>

      <div class="section-header finance-heading">
        <div>
          <p class="eyebrow">SALDOS ATUAIS</p>
          <h2>Financeiro</h2>
        </div>
      </div>
      <div class="stat-grid">
        <StatCard label="RANKING FINANCEIRO" :value="brl(financial.ranking_total)" />
        <StatCard label="CAIXA APÓS DESPESAS" :value="brl(financial.caixa_total)" :variant="financial.caixa_total < 0 ? 'red' : 'green'" />
      </div>
      <p class="finance-note">Saldos incluem os valores da rodada em andamento, se houver, e retiradas registradas.</p>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StatCard from '../components/StatCard.vue'
import { financialApi, roundsApi } from '../api'

const loading = ref(true)
const error = ref('')
const rounds = ref([])
const entries = ref([])
const financial = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [roundsResponse, financialResponse] = await Promise.all([roundsApi.list(), financialApi.get()])
    const finalized = roundsResponse.data.filter(round => round.is_finalized)
    const playersByRound = await Promise.all(finalized.map(round => roundsApi.getPlayers(round.id)))
    rounds.value = finalized
    entries.value = playersByRound.flatMap(response => response.data)
    financial.value = financialResponse.data
  } catch {
    error.value = 'Não foi possível carregar o dashboard. Verifique a conexão e tente novamente.'
  } finally {
    loading.value = false
  }
}

const players = computed(() => {
  const grouped = new Map()
  for (const entry of entries.value) {
    if (!grouped.has(entry.player_id)) {
      grouped.set(entry.player_id, { name: entry.player_name, appearances: 0, rebuys: 0, addons: 0, wins: 0 })
    }
    const player = grouped.get(entry.player_id)
    player.appearances += 1
    player.rebuys += entry.rebuy || 0
    player.addons += entry.addon || 0
    if (entry.colocacao === 1) player.wins += 1
  }
  return [...grouped.values()]
})

const totalRebuys = computed(() => players.value.reduce((sum, player) => sum + player.rebuys, 0))
const totalAddons = computed(() => players.value.reduce((sum, player) => sum + player.addons, 0))

const stories = [
  { icon: '🍕', title: 'Quem paga a pizza?', description: 'Gustavo China já tinha até escolhido o Deivid para pagar. Ganhar o pote é uma coisa; escapar do fiscal da pizza é outra.' },
  { icon: '⚽', title: 'O Vasco do Joel', description: 'Joel Felipe confessou que o Vasco desestabiliza a cabeça. Tem bad beat que começa muito antes do flop.' },
  { icon: '🥤', title: 'A Coca da mesa', description: 'André Yuji pediu Coca Zero e sugeriu revezamento. Danilo avisou: não basta levar, tem que estar gelada!' },
  { icon: '💬', title: 'Falinhas garantidas', description: 'Joel Felipe confirmou presença com falinhas. O all-in pode até esperar; o comentário sobre a jogada, não.' },
  { icon: '🧴', title: 'Operação desodorante', description: 'Joel Felipe se ofereceu para pagar o desodorante, e Matheus Riacho disse que levava o perfume. Se depender da resenha, o kit perfumaria está garantido!' },
  { icon: '🃏', title: 'Blefe em debate', description: 'Deivid foi chamado para explicar uma mão; Matheus Morais ficou no “se meu blefe passa...”. O jogo acaba, a análise não.' },
]

function leader(key, singular, plural) {
  const highest = Math.max(0, ...players.value.map(player => player[key]))
  if (!highest) return { names: '—', description: 'Nenhum registro ainda' }
  const names = players.value.filter(player => player[key] === highest)
    .map(player => player.name).sort((a, b) => a.localeCompare(b, 'pt-BR')).join(', ')
  return { names, description: `${highest} ${highest === 1 ? singular : plural}` }
}

const facts = computed(() => [
  { icon: '🔄', title: 'Mais rebuys', ...leader('rebuys', 'rebuy', 'rebuys') },
  { icon: '🗓️', title: 'Mais participações', ...leader('appearances', 'rodada', 'rodadas') },
  { icon: '🏆', title: 'Mais primeiros lugares', ...leader('wins', 'primeiro lugar', 'primeiros lugares') },
  { icon: '🃏', title: 'Mais addons', ...leader('addons', 'addon', 'addons') },
])

function brl(value) {
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

onMounted(load)
</script>

<style scoped>
.dashboard-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 24px; }
.eyebrow { color: var(--gold); font-size: 11px; font-weight: 600; letter-spacing: 1.4px; margin-bottom: 8px; }
h1 { font-size: 28px; line-height: 1.2; margin-bottom: 6px; }
h2 { font-size: 19px; }
.subtitle, .finance-note, .jokes-note { color: var(--text-dim); font-size: 13px; line-height: 1.5; }
.jokes-note { margin: 0 0 14px; }
.section-header { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; margin: 28px 0 14px; }
.section-header > span { color: var(--text-dim); font-size: 12px; }
.facts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; }
.fact-card { background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 18px; min-width: 0; }
.fact-icon { display: inline-flex; align-items: center; justify-content: center; background: rgba(201,162,39,.1); border-radius: 8px; width: 36px; height: 36px; font-size: 19px; margin-bottom: 16px; }
.fact-title { color: var(--text-dim); font-size: 12px; margin-bottom: 8px; }
.fact-names { color: var(--text); font-weight: 600; line-height: 1.4; overflow-wrap: anywhere; }
.fact-value { color: var(--gold); font-size: 13px; margin-top: 6px; }
.finance-note { margin-top: -10px; }
.empty .btn { margin-top: 12px; }
@media (max-width: 500px) {
  .dashboard-heading { align-items: center; }
  h1 { font-size: 23px; }
  .section-header { align-items: flex-start; flex-direction: column; }
}
</style>
