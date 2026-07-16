<template>
  <div>
    <!-- Stats -->
    <div class="stat-grid">
      <StatCard label="RODADAS VISÍVEIS"  :value="`${activeRounds.length} / ${allRounds.length}`" variant="white" />
      <StatCard label="JOGADORES ATIVOS"  :value="activePlayers"                                  variant="white" />
      <StatCard label="LÍDER SEMESTRAL"   :value="rows[0]?.player_name || '—'"                    variant="small" />
      <StatCard label="PONTUAÇÃO DO LÍDER" :value="rows[0]?.total || 0"                           />
    </div>

    <!-- Round filter pills -->
    <div class="round-filter">
      <span class="pill-label">Rodadas:</span>
      <span
        v-for="r in allRounds"
        :key="r.id"
        class="round-pill"
        :class="{ active: activeIds.has(r.id) }"
        @click="toggleRound(r.id)"
      >{{ r.label.replace(' - ', ' ') }}</span>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <button class="btn btn-ghost btn-sm" @click="selectAll">Todas</button>
      <button class="btn btn-ghost btn-sm" @click="selectNone">Nenhuma</button>
      <span style="margin-left:auto;display:flex;gap:8px;align-items:center">
        <span :style="{ fontSize:'11px', color: editMode ? 'var(--gold)' : 'var(--text-faint)' }">
          {{ editMode ? '🔓 Modo edição' : '🔒 Edição bloqueada' }}
        </span>
        <button class="btn btn-ghost btn-sm" @click="toggleEdit">
          {{ editMode ? 'Bloquear' : 'Desbloquear' }}
        </button>
        <button v-if="editMode" class="btn btn-primary btn-sm" @click="openAddRound">+ Nova Rodada</button>
        <button v-if="editMode" class="btn btn-ghost btn-sm"   @click="openRenameRound">✎ Renomear</button>
        <button v-if="editMode" class="btn btn-danger btn-sm"  @click="openDeleteRound">✕ Excluir Rodada</button>
        <button v-if="editMode" class="btn btn-ghost btn-sm"   @click="saveActiveRounds">💾 Salvar como padrão</button>
      </span>
    </div>

    <!-- Table -->
    <div class="table-wrap" v-if="ranking">
      <table>
        <thead>
          <tr>
            <th style="width:44px">#</th>
            <th style="width:130px">Nome</th>
            <th style="width:80px">Buy-ins</th>
            <th style="width:80px">Rebuys</th>
            <th style="width:80px">Addons</th>
            <th v-for="r in orderedActiveRounds" :key="r.id" style="width:75px;font-size:10px">
              {{ r.label.replace(' - ', ' ') }}
            </th>
            <th style="width:80px">Total</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in rows" :key="row.player_id">
            <td class="medal">{{ medals[i] || i + 1 }}</td>
            <td class="name">{{ row.player_name }}</td>
            <td class="num">{{ row.total_buyins }}</td>
            <td :class="row.total_rebuys > 0 ? 'num' : 'zero'">{{ row.total_rebuys }}</td>
            <td :class="row.total_addons > 0 ? 'num' : 'zero'">{{ row.total_addons }}</td>
            <td
              v-for="r in orderedActiveRounds"
              :key="r.id"
              :class="[score(row, r.id) > 0 ? 'num' : 'zero', editMode ? 'editable' : '']"
              @click="editMode && openEditScore(row, r)"
            >
              {{ score(row, r.id) }}
            </td>
            <td class="total">{{ row.total }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="empty">
      <div class="empty-icon">♠</div>
      <p>Carregando ranking...</p>
    </div>
  </div>

  <!-- Edit Score Modal -->
  <BaseModal v-if="scoreModal.show" @close="scoreModal.show = false">
    <h2>Editar Pontuação</h2>
    <p style="font-size:13px;color:var(--text-dim);margin-bottom:16px">
      {{ scoreModal.playerName }} — {{ scoreModal.roundLabel }}
    </p>
    <div class="field">
      <label>Pontuação</label>
      <input type="number" v-model.number="scoreModal.value" min="0" autofocus @keyup.enter="doSaveScore" />
    </div>
    <div class="modal-actions">
      <button class="btn btn-gold"  @click="doSaveScore">Salvar</button>
      <button class="btn btn-ghost" @click="scoreModal.show = false">Cancelar</button>
    </div>
  </BaseModal>

  <!-- Add Round Modal -->
  <BaseModal v-if="showAddRound" @close="showAddRound = false">
    <h2>Nova Rodada</h2>
    <div class="form-grid">
      <div class="field full">
        <label>Data</label>
        <input type="date" v-model="roundForm.date" />
      </div>
      <div class="field full">
        <label>Label (opcional)</label>
        <input type="text" v-model="roundForm.label" placeholder="ex: Rodada 20 - 27/07" />
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn btn-primary" @click="doAddRound">Adicionar</button>
      <button class="btn btn-ghost"   @click="showAddRound = false">Cancelar</button>
    </div>
  </BaseModal>

  <!-- Rename Round Modal -->
  <BaseModal v-if="showRenameRound" @close="showRenameRound = false">
    <h2>Renomear Rodada</h2>
    <div class="form-grid">
      <div class="field full">
        <label>Rodada</label>
        <select v-model.number="renameRoundId" @change="renameLabel = allRounds.find(r => r.id === renameRoundId)?.label ?? ''">
          <option v-for="r in allRounds" :key="r.id" :value="r.id">{{ r.label }}</option>
        </select>
      </div>
      <div class="field full">
        <label>Novo nome</label>
        <input type="text" v-model="renameLabel" placeholder="ex: Rodada 01 - 01/07" autofocus @keyup.enter="doRenameRound" />
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn btn-primary" @click="doRenameRound">Renomear</button>
      <button class="btn btn-ghost"   @click="showRenameRound = false">Cancelar</button>
    </div>
  </BaseModal>

  <!-- Delete Round Modal -->
  <BaseModal v-if="showDeleteRound" @close="showDeleteRound = false">
    <h2>Excluir Rodada</h2>
    <p style="font-size:13px;color:var(--text-dim);margin-bottom:16px">
      Selecione a rodada que deseja excluir permanentemente.
    </p>
    <div class="field">
      <label>Rodada</label>
      <select v-model.number="deleteRoundId">
        <option v-for="r in allRounds" :key="r.id" :value="r.id">{{ r.label }}</option>
      </select>
    </div>
    <div class="modal-actions">
      <button class="btn btn-danger" @click="doDeleteRound">Excluir</button>
      <button class="btn btn-ghost"  @click="showDeleteRound = false">Cancelar</button>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import StatCard from '../components/StatCard.vue'
import BaseModal from '../components/BaseModal.vue'
import { useRanking } from '../stores/ranking'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { roundsApi } from '../api'

const { ranking, fetch, setActive, updateScore } = useRanking()
const { isUnlocked, requireAuth } = useAuth()
const { show: toast } = useToast()

const medals = ['🥇', '🥈', '🥉']
const editMode = ref(false)

const showAddRound    = ref(false)
const showDeleteRound = ref(false)
const showRenameRound = ref(false)
const deleteRoundId   = ref(null)
const renameRoundId   = ref(null)
const renameLabel     = ref('')
const roundForm       = ref({ label: '', date: '' })

const scoreModal = ref({ show: false, playerId: null, roundId: null, playerName: '', roundLabel: '', value: 0 })

// Local filter state — never requires auth, just filters the table view.
// Initialized from the backend's active_round_ids; defaults to ALL rounds when none are configured.
const localActiveIds = ref(new Set())

watch(ranking, (val) => {
  if (!val) return
  localActiveIds.value = new Set(val.rounds.map(r => r.id))
}, { immediate: true })

const allRounds    = computed(() => ranking.value?.rounds ?? [])
const activeIds    = computed(() => localActiveIds.value)
const activeRounds = computed(() => allRounds.value.filter(r => localActiveIds.value.has(r.id)))
const roundNumberFromLabel = (label) => {
  const match = String(label ?? '').match(/Rodada\s*(\d+)/i)
  return match ? parseInt(match[1], 10) : Number.POSITIVE_INFINITY
}

const orderedActiveRounds = computed(() =>
  [...activeRounds.value].sort((a, b) => {
    const aNumber = roundNumberFromLabel(a.label)
    const bNumber = roundNumberFromLabel(b.label)
    if (aNumber !== bNumber) return aNumber - bNumber
    return a.id - b.id
  }),
)

const sumByActiveRounds = (roundMap) =>
  [...localActiveIds.value].reduce(
    (s, rid) => s + (roundMap?.[String(rid)] ?? roundMap?.[rid] ?? 0),
    0,
  )

// Recompute totals locally so filtering is instant without a backend call.
const rows = computed(() => {
  const base = ranking.value?.rows ?? []
  return base.map(row => ({
    ...row,
    total: [...localActiveIds.value].reduce((s, rid) => s + (row.scores[String(rid)] || 0), 0),
    total_buyins: sumByActiveRounds(row.buyins),
    total_rebuys: sumByActiveRounds(row.rebuys),
    total_addons: sumByActiveRounds(row.addons),
  })).sort((a, b) => b.total - a.total)
})

const activePlayers = computed(() => rows.value.filter(r => r.total > 0).length)

const score = (row, roundId) => row.scores[String(roundId)] ?? row.scores[roundId] ?? 0

function toggleRound(id) {
  const ids = new Set(localActiveIds.value)
  ids.has(id) ? ids.delete(id) : ids.add(id)
  localActiveIds.value = ids
}

function selectAll()  { localActiveIds.value = new Set(allRounds.value.map(r => r.id)) }
function selectNone() { localActiveIds.value = new Set() }

async function saveActiveRounds() {
  try {
    await setActive([...localActiveIds.value])
    toast('Configuração de rodadas salva ✓')
  } catch {
    toast('Erro ao salvar configuração.')
  }
}

function toggleEdit() {
  if (editMode.value) { editMode.value = false; return }
  requireAuth(() => { editMode.value = true })
}

function openEditScore(row, round) {
  scoreModal.value = {
    show: true,
    playerId: row.player_id,
    roundId: round.id,
    playerName: row.player_name,
    roundLabel: round.label,
    value: score(row, round.id),
  }
}

async function doSaveScore() {
  try {
    await updateScore(scoreModal.value.playerId, scoreModal.value.roundId, scoreModal.value.value)
    scoreModal.value.show = false
    toast('Pontuação atualizada ✓')
  } catch {
    toast('Erro ao salvar pontuação.')
  }
}

function openAddRound()    { roundForm.value = { label: '', date: '' }; showAddRound.value = true }
function openRenameRound() {
  renameRoundId.value = allRounds.value[0]?.id ?? null
  renameLabel.value = allRounds.value[0]?.label ?? ''
  showRenameRound.value = true
}
async function doRenameRound() {
  const r = allRounds.value.find(x => x.id === renameRoundId.value)
  if (!r || !renameLabel.value.trim()) return
  try {
    await roundsApi.update(r.id, { label: renameLabel.value.trim() })
    await fetch()
    showRenameRound.value = false
    toast(`Rodada renomeada para "${renameLabel.value.trim()}" ✓`)
  } catch (e) {
    toast(e.response?.data?.detail || 'Erro ao renomear rodada.')
  }
}
function openDeleteRound() {
  deleteRoundId.value = allRounds.value[0]?.id ?? null
  showDeleteRound.value = true
}

async function doAddRound() {
  try {
    const total = allRounds.value.length + 1
    const label = roundForm.value.label ||
      (roundForm.value.date ? `Rodada ${total} - ${roundForm.value.date.slice(8)}/${roundForm.value.date.slice(5,7)}` : `Rodada ${total}`)
    await roundsApi.create({ label, date: roundForm.value.date || null })
    await fetch()
    showAddRound.value = false
    toast(`${label} adicionada! ✓`)
  } catch (e) {
    toast(e.response?.data?.detail || 'Erro ao adicionar rodada.')
  }
}

async function doDeleteRound() {
  const r = allRounds.value.find(x => x.id === deleteRoundId.value)
  if (!r || !confirm(`Excluir "${r.label}"? Esta ação não pode ser desfeita.`)) return
  try {
    await roundsApi.remove(r.id)
    await fetch()
    showDeleteRound.value = false
    toast(`"${r.label}" excluída ✓`)
  } catch (e) {
    toast(e.response?.data?.detail || 'Erro ao excluir rodada.')
  }
}

onMounted(fetch)
</script>

<style scoped>
/* Sticky first 2 columns */
table :is(th, td):nth-child(1),
table :is(th, td):nth-child(2) {
  position: sticky;
  z-index: 1;
  background: var(--bg);
}
table :is(th, td):nth-child(1) { left: 0; }
table :is(th, td):nth-child(2) { left: 44px; }

/* Header cells need darker bg and higher z-index */
table th:nth-child(1),
table th:nth-child(2) {
  background: #0f2a1a;
  z-index: 2;
}

/* Visual separator after the frozen columns */
table :is(th, td):nth-child(2) {
  box-shadow: 3px 0 8px -2px rgba(0, 0, 0, 0.6);
}
</style>
