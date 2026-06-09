<template>
  <div>
    <!-- Stats -->
    <div class="stat-grid">
      <StatCard label="JOGADORES"       :value="roundPlayers.length"              variant="white" />
      <StatCard label="BUY-INS / REBUYS" :value="totalBuyins"                    variant="white" />
      <StatCard label="ADDONS"           :value="totalAddons"                     variant="white" />
      <StatCard label="CAIXA DA NOITE"   :value="brl(caixaNoite)"                 variant="green" />
      <StatCard label="LÍDER"            :value="leader?.player_name || '—'"      variant="small" />
    </div>

    <!-- No current round -->
    <template v-if="!currentRound">
      <div class="empty">
        <div class="empty-icon">♠</div>
        <p>Nenhuma rodada em andamento.<br>Inicie uma nova rodada para começar.</p>
        <br>
        <button class="btn btn-gold" @click="showStartModal = true">+ Iniciar Rodada</button>
      </div>
    </template>

    <!-- Current round active -->
    <template v-else>
      <div class="toolbar">
        <button class="btn btn-primary" @click="openAdd">+ Adicionar Jogador</button>
        <button class="btn btn-ghost"   @click="openEdit" :disabled="!selectedId">✎ Editar</button>
        <button class="btn btn-danger btn-sm" @click="doRemove" :disabled="!selectedId">✕ Remover</button>
        <button class="btn btn-gold" style="margin-left:auto" @click="showFinalize = true">✓ Finalizar Rodada</button>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th style="width:44px">#</th>
              <th style="width:140px">Nome</th>
              <th>Buy-in/Rebuy</th>
              <th>Addon</th>
              <th>Pontos</th>
              <th>Presença</th>
              <th>Bônus ITM</th>
              <th>Indicação</th>
              <th>Pontualidade</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(p, i) in sortedPlayers"
              :key="p.player_id"
              :class="{ selected: selectedId === p.player_id }"
              @click="selectedId = p.player_id"
            >
              <td class="medal">{{ medals[i] || i + 1 }}</td>
              <td class="name">{{ p.player_name }}</td>
              <td :class="p.buyin ? 'num' : 'zero'">{{ p.buyin }}</td>
              <td :class="p.addon ? 'num' : 'zero'">{{ p.addon }}</td>
              <td :class="p.pontos ? 'num' : 'zero'">{{ p.pontos }}</td>
              <td :class="p.presenca ? 'num' : 'zero'">{{ p.presenca }}</td>
              <td :class="p.bonus ? 'num' : 'zero'">{{ p.bonus }}</td>
              <td :class="p.indicacao ? 'num' : 'zero'">{{ p.indicacao }}</td>
              <td :class="p.pontualidade ? 'num' : 'zero'">{{ p.pontualidade }}</td>
              <td class="total">{{ p.total }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!roundPlayers.length" class="empty">
          <div class="empty-icon">♠</div>
          <p>Nenhum jogador adicionado ainda.<br>Clique em "Adicionar Jogador" para começar.</p>
        </div>
      </div>
    </template>
  </div>

  <!-- Start Round Modal -->
  <BaseModal v-if="showStartModal" @close="showStartModal = false; startError = ''; startForm.password = ''">
    <h2>Iniciar Rodada</h2>
    <div class="form-grid">
      <div class="field full">
        <label>Data</label>
        <input type="date" v-model="startForm.date" />
      </div>
      <div class="field full">
        <label for="start-label">Label (opcional)</label>
        <input id="start-label" type="text" v-model="startForm.label" placeholder="ex: Rodada 20 - 15/06" />
      </div>
      <div class="field full">
        <label for="start-password">Senha de administrador</label>
        <input id="start-password" type="password" v-model="startForm.password" placeholder="••••••••" autofocus @keyup.enter="doStartRound" />
      </div>
    </div>
    <div v-if="startError" style="color:var(--red);font-size:12px;margin-top:8px">{{ startError }}</div>
    <div class="modal-actions">
      <button class="btn btn-primary" @click="doStartRound" :disabled="starting">
        {{ starting ? 'Iniciando...' : 'Iniciar' }}
      </button>
      <button class="btn btn-ghost" @click="showStartModal = false">Cancelar</button>
    </div>
  </BaseModal>

  <!-- Add/Edit Player Modal -->
  <BaseModal v-if="showPlayerModal" @close="showPlayerModal = false">
    <h2>{{ editingPlayer ? 'Editar Jogador' : 'Novo Jogador' }}</h2>
    <div class="form-grid">
      <div class="field full">
        <label>Nome</label>
        <input
          type="text"
          v-model="form.name"
          list="players-list"
          placeholder="Nome do jogador"
          :disabled="!!editingPlayer"
          required
          autofocus
        />
        <datalist id="players-list">
          <option v-for="p in availablePlayers" :key="p.id" :value="p.name" />
        </datalist>
      </div>
      <div class="field">
        <label>Buy-in / Rebuys</label>
        <input type="number" v-model.number="form.buyin" min="0" />
      </div>
      <div class="field">
        <label>Addons</label>
        <input type="number" v-model.number="form.addon" min="0" />
      </div>
      <div class="field">
        <label>Pontos (chips finais)</label>
        <input type="number" v-model.number="form.pontos" min="0" />
      </div>
      <div class="field">
        <label>Bônus ITM</label>
        <input type="number" v-model.number="form.bonus" min="0" />
      </div>
      <div class="field">
        <label>Indicação (pts)</label>
        <input type="number" v-model.number="form.indicacao" min="0" />
      </div>
      <div class="field">
        <label>Presença (+{{ presencaPts }} pts)</label>
        <select v-model.number="form.presenca">
          <option :value="presencaPts">Presente</option>
          <option :value="0">Ausente</option>
        </select>
      </div>
      <div class="field">
        <label>Pontual? (+{{ pontPts }} pts)</label>
        <select v-model.number="form.pontualidade">
          <option :value="pontPts">Sim</option>
          <option :value="0">Não</option>
        </select>
      </div>
    </div>
    <div v-if="formError" style="color:var(--red);font-size:12px;margin-top:8px">{{ formError }}</div>
    <div class="modal-actions">
      <button class="btn btn-gold"  @click="doSavePlayer" :disabled="saving">
        {{ saving ? 'Salvando...' : 'Confirmar' }}
      </button>
      <button class="btn btn-ghost" @click="showPlayerModal = false">Cancelar</button>
    </div>
  </BaseModal>

  <!-- Finalize Modal -->
  <BaseModal v-if="showFinalize" @close="showFinalize = false">
    <template v-if="!finalizeResult">
      <h2>Finalizar Rodada</h2>
      <div class="stat-grid" style="margin-bottom:16px">
        <StatCard label="CAIXA DA NOITE" :value="brl(caixaNoite)" variant="green" />
        <StatCard label="PREMIAÇÃO ({{ config?.prize_pct || 70 }}%)" :value="brl(premiacao)" />
      </div>
      <div class="fin-row">
        <span class="fin-lbl">🥇 {{ sortedPlayers[0]?.player_name || '—' }}</span>
        <span class="fin-val gold">{{ brl(premiacao * 0.7) }}</span>
      </div>
      <div class="fin-row">
        <span class="fin-lbl">🥈 {{ sortedPlayers[1]?.player_name || '—' }}</span>
        <span class="fin-val">{{ brl(premiacao * 0.3) }}</span>
      </div>
      <div class="modal-actions">
        <button class="btn btn-gold"  @click="doFinalize" :disabled="finalizing">
          {{ finalizing ? 'Finalizando...' : '✓ Confirmar e Salvar' }}
        </button>
        <button class="btn btn-ghost" @click="showFinalize = false">Cancelar</button>
      </div>
    </template>

    <template v-else>
      <h2>Rodada Finalizada!</h2>
      <div class="stat-grid" style="margin-bottom:16px">
        <StatCard label="CAIXA DA NOITE"  :value="brl(finalizeResult.caixa_noite)"     variant="green" />
        <StatCard label="PREMIAÇÃO TOTAL" :value="brl(finalizeResult.premiacao_total)"  />
      </div>
      <div v-for="entry in finalizeResult.ranking" :key="entry.position" class="fin-row">
        <span class="fin-lbl">
          {{ medals[entry.position - 1] || entry.position }}
          {{ entry.player_name }}
          <span style="color:var(--text-faint)">({{ entry.total_points }} pts)</span>
        </span>
        <span class="fin-val" :class="entry.position === 1 ? 'gold' : ''">
          {{ entry.prize > 0 ? brl(entry.prize) : '—' }}
        </span>
      </div>
      <div class="modal-actions">
        <button class="btn btn-gold" @click="showFinalize = false; finalizeResult = null">Fechar</button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import StatCard from '../components/StatCard.vue'
import BaseModal from '../components/BaseModal.vue'
import { useRounds } from '../stores/rounds'
import { useConfig } from '../stores/config'
import { useToast } from '../composables/useToast'
import { authApi, setAdminPassword } from '../api'

const { currentRound, roundPlayers, allPlayers, fetchCurrent, fetchAllPlayers, startRound, addPlayer, updatePlayer, removePlayer, finalize } = useRounds()
const { config, fetch: fetchConfig } = useConfig()
const { show: toast } = useToast()

const medals = ['🥇', '🥈', '🥉']

const selectedId = ref(null)
const showStartModal  = ref(false)
const showPlayerModal = ref(false)
const showFinalize    = ref(false)
const editingPlayer   = ref(null)
const finalizeResult  = ref(null)
const saving          = ref(false)
const finalizing      = ref(false)
const starting        = ref(false)
const formError       = ref('')
const startError      = ref('')

const startForm = ref({ label: '', date: '', password: '' })
const form = ref({
  name: '', buyin: 1, addon: 0, pontos: 0,
  presenca: 10, bonus: 0, indicacao: 0, pontualidade: 15,
})

const presencaPts  = computed(() => config.value?.presence_points    ?? 10)
const pontPts      = computed(() => config.value?.punctuality_points  ?? 15)

const sortedPlayers = computed(() =>
  [...roundPlayers.value].sort((a, b) => b.total - a.total)
)

const totalBuyins = computed(() => roundPlayers.value.reduce((s, p) => s + p.buyin, 0))
const totalAddons = computed(() => roundPlayers.value.reduce((s, p) => s + p.addon, 0))
const caixaNoite  = computed(() =>
  totalBuyins.value * (config.value?.buyin_value ?? 50) +
  totalAddons.value * (config.value?.addon_value ?? 50)
)
const premiacao = computed(() => caixaNoite.value * ((config.value?.prize_pct ?? 70) / 100))
const leader    = computed(() => sortedPlayers.value[0] ?? null)

const availablePlayers = computed(() => {
  const inRound = new Set(roundPlayers.value.map(p => p.player_id))
  return allPlayers.value.filter(p => !inRound.has(p.id))
})

const brl = (v) => {
  const n = Math.abs(v || 0)
  return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function resetForm() {
  form.value = {
    name: '', buyin: 1, addon: 0, pontos: 0,
    presenca: presencaPts.value, bonus: 0, indicacao: 0,
    pontualidade: pontPts.value,
  }
  formError.value = ''
}

function openAdd() {
  editingPlayer.value = null
  resetForm()
  showPlayerModal.value = true
}

function openEdit() {
  const p = roundPlayers.value.find(x => x.player_id === selectedId.value)
  if (!p) return
  editingPlayer.value = p
  form.value = {
    name: p.player_name,
    buyin: p.buyin, addon: p.addon, pontos: p.pontos,
    presenca: p.presenca, bonus: p.bonus, indicacao: p.indicacao,
    pontualidade: p.pontualidade,
  }
  formError.value = ''
  showPlayerModal.value = true
}

async function doStartRound() {
  startError.value = ''
  if (!startForm.value.password) {
    startError.value = 'Informe a senha de administrador.'
    return
  }
  starting.value = true
  try {
    const { data: auth } = await authApi.verify(startForm.value.password)
    if (!auth.valid) {
      startError.value = 'Senha incorreta.'
      return
    }
    setAdminPassword(startForm.value.password)
    await startRound(startForm.value.label, startForm.value.date || null)
    showStartModal.value = false
    startForm.value = { label: '', date: '', password: '' }
    toast('Rodada iniciada! ✓')
  } catch (e) {
    startError.value = e.response?.data?.detail || 'Erro ao iniciar rodada.'
  } finally {
    starting.value = false
  }
}

async function doSavePlayer() {
  if (!form.value.name.trim()) { formError.value = 'Nome é obrigatório.'; return }
  saving.value = true
  formError.value = ''
  try {
    if (editingPlayer.value) {
      await updatePlayer(editingPlayer.value.player_id, {
        buyin: form.value.buyin, addon: form.value.addon,
        pontos: form.value.pontos, presenca: form.value.presenca,
        bonus: form.value.bonus, indicacao: form.value.indicacao,
        pontualidade: form.value.pontualidade,
      })
      toast('Jogador atualizado! ✓')
    } else {
      await addPlayer({
        name: form.value.name.trim(),
        buyin: form.value.buyin, addon: form.value.addon,
        pontos: form.value.pontos, presenca: form.value.presenca,
        bonus: form.value.bonus, indicacao: form.value.indicacao,
        pontualidade: form.value.pontualidade,
      })
      toast('Jogador adicionado! ✓')
    }
    showPlayerModal.value = false
  } catch (e) {
    formError.value = e.response?.data?.detail || 'Erro ao salvar.'
  } finally {
    saving.value = false
  }
}

async function doRemove() {
  const p = roundPlayers.value.find(x => x.player_id === selectedId.value)
  if (!p || !confirm(`Remover "${p.player_name}"?`)) return
  try {
    await removePlayer(selectedId.value)
    selectedId.value = null
    toast('Jogador removido.')
  } catch (e) {
    toast('Erro ao remover jogador.')
  }
}

async function doFinalize() {
  finalizing.value = true
  try {
    finalizeResult.value = await finalize()
    toast('Rodada finalizada e salva no ranking! ✓')
  } catch (e) {
    toast(e.response?.data?.detail || 'Erro ao finalizar.')
    showFinalize.value = false
  } finally {
    finalizing.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchCurrent(), fetchAllPlayers(), fetchConfig()])
})
</script>
