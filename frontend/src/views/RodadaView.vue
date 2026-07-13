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
      <!-- PIX charges from last round -->
      <div v-if="pixCodes.length" style="margin-bottom:24px">
        <p style="font-size:11px;color:var(--text-dim);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">
          Cobranças PIX — {{ pixCodes[0]?.receiverName }}
        </p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Jogador</th>
                <th style="text-align:right">Valor</th>
                <th style="text-align:center;width:120px">Copiar</th>
                <th style="text-align:center;width:110px">Download</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in pixCodes" :key="item.player_name">
                <td class="name">{{ item.player_name }}</td>
                <td style="text-align:right;color:var(--gold);font-weight:500">{{ brl(item.valor) }}</td>
                <td style="text-align:center">
                  <button class="btn btn-ghost" style="padding:4px 10px;font-size:11px" @click="copyPixCode(item)">
                    {{ item.copied ? '✓ Copiado' : 'Copiar PIX' }}
                  </button>
                </td>
                <td style="text-align:center">
                  <a
                    class="btn btn-ghost"
                    style="padding:4px 10px;font-size:11px;text-decoration:none;display:inline-block"
                    :href="'data:text/plain;charset=utf-8,' + encodeURIComponent(item.code)"
                    :download="'pix-' + item.player_name + '.txt'"
                  >⬇ .txt</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div style="text-align:right;margin-top:8px">
          <button class="btn btn-ghost btn-sm" style="font-size:11px" @click="pixCodes = []">✕ Limpar</button>
        </div>
      </div>

      <div class="empty">
        <div class="empty-icon">♠</div>
        <p>Nenhuma rodada em andamento.<br>Inicie uma nova rodada para começar.</p>
        <br>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
          <button class="btn btn-gold" @click="showStartModal = true">+ Iniciar Rodada</button>
          <button class="btn btn-primary" @click="openImport">📋 Importar via CSV</button>
        </div>
      </div>
    </template>

    <!-- Current round active -->
    <template v-else>
      <div class="toolbar">
        <button class="btn btn-primary" @click="openAdd">+ Adicionar Jogador</button>
        <button class="btn btn-ghost"   @click="openEdit">✎ Editar</button>
        <button class="btn btn-danger btn-sm" @click="doRemove">✕ Remover</button>
        <button class="btn btn-gold" style="margin-left:auto" @click="openFinalize">✓ Finalizar Rodada</button>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th style="width:44px">#</th>
              <th style="width:140px">Nome</th>
              <th>Buy-in/Rebuy</th>
              <th>Addon</th>
              <th>Colocação</th>
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
              <td :class="p.colocacao ? 'num' : 'zero'">{{ p.colocacao === 1 ? '🥇' : p.colocacao === 2 ? '🥈' : p.colocacao === 3 ? '🥉' : p.colocacao >= 4 ? p.colocacao + 'º' : '—' }}</td>
              <td :class="p.calcPontos ? 'num' : 'zero'">{{ p.calcPontos }}</td>
              <td :class="p.presenca ? 'num' : 'zero'">{{ p.presenca }}</td>
              <td :class="p.bonus ? 'num' : 'zero'">{{ p.bonus }}</td>
              <td :class="p.indicacao ? 'num' : 'zero'">{{ p.indicacao }}</td>
              <td :class="p.pontualidade ? 'num' : 'zero'">{{ p.pontualidade }}</td>
              <td class="total">{{ p.calcTotal }}</td>
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
        <label>Colocação</label>
        <select v-model.number="form.colocacao">
          <option :value="0" disabled>— Selecione —</option>
          <option
            v-for="pos in roundPlayers.length"
            :key="pos"
            :value="pos"
            v-if="!takenPositions.has(pos)"
          >{{ pos === 1 ? '🥇 1º lugar' : pos === 2 ? '🥈 2º lugar' : pos === 3 ? '🥉 3º lugar' : pos + 'º lugar' }}</option>
        </select>
      </div>
      <div class="field">
        <label>Pontos (calculado)</label>
        <input type="number" :value="previewPontos" disabled style="opacity:0.5;cursor:not-allowed" />
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

  <!-- Import PDF Modal -->
  <BaseModal v-if="showImportModal" @close="closeImport">
    <!-- Step 1: form -->
    <template v-if="importStep === 'form'">
      <h2>Importar Rodada via CSV</h2>
      <p style="font-size:12px;color:var(--text-dim);margin-bottom:16px">
        Exporte a planilha como <strong>CSV</strong> e selecione o arquivo abaixo.<br>
        Colunas reconhecidas: <em>Nome / Jogador, Buy in / Rebuy, Addon, Pontos, Presença, Bônus ITM, Indicação, Pontualidade, Colocação.</em>
      </p>
      <div class="form-grid">
        <div class="field full">
          <label>Arquivo CSV</label>
          <input type="file" accept=".csv" @change="onFileChange" style="color:var(--text)" />
        </div>
        <div class="field full">
          <label>Label da rodada (opcional)</label>
          <input type="text" v-model="importForm.label" placeholder="ex: Rodada 20 - 15/06" />
        </div>
      </div>
      <div v-if="importError" style="color:var(--red);font-size:12px;margin-top:8px">{{ importError }}</div>
      <div class="modal-actions">
        <button class="btn btn-primary" @click="doAnalyze" :disabled="importing">
          {{ importing ? 'Analisando...' : '🔍 Analisar CSV' }}
        </button>
        <button class="btn btn-ghost" @click="closeImport">Cancelar</button>
      </div>
    </template>

    <!-- Step 2: preview -->
    <template v-else-if="importStep === 'preview'">
      <h2>Preview da Importação</h2>

      <p style="font-size:13px;color:var(--text-dim);margin-bottom:12px">
        {{ importPreview.matched.length }} jogador(es) reconhecido(s)
        <span v-if="importPreview.unmatched.length" style="color:var(--red)">
          · {{ importPreview.unmatched.length }} não encontrado(s)
        </span>
      </p>

      <div style="max-height:280px;overflow-y:auto;margin-bottom:12px">
        <table style="width:100%;font-size:12px">
          <thead>
            <tr style="color:var(--text-dim)">
              <th style="text-align:left;padding:4px 8px">Jogador</th>
              <th>Buy-in</th><th>Addon</th><th>Pts</th>
              <th>Pres.</th><th>Bônus</th><th>Pont.</th><th>Ind.</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in importPreview.matched" :key="p.player_id" style="border-top:1px solid var(--border)">
              <td style="padding:4px 8px">{{ p.player_name }}</td>
              <td style="text-align:center">{{ p.buyin }}</td>
              <td style="text-align:center">{{ p.addon }}</td>
              <td style="text-align:center">{{ p.pontos }}</td>
              <td style="text-align:center">{{ p.presenca }}</td>
              <td style="text-align:center">{{ p.bonus }}</td>
              <td style="text-align:center">{{ p.pontualidade }}</td>
              <td style="text-align:center">{{ p.indicacao }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="importPreview.unmatched.length" style="margin-bottom:12px">
        <p style="font-size:12px;color:var(--red);margin-bottom:4px">Nomes não encontrados no cadastro:</p>
        <p style="font-size:12px;color:var(--text-dim)">{{ importPreview.unmatched.join(', ') }}</p>
      </div>

      <div v-if="importError" style="color:var(--red);font-size:12px;margin-bottom:8px">{{ importError }}</div>
      <div class="modal-actions">
        <button class="btn btn-gold" @click="doCreateRound" :disabled="importing">
          {{ importing ? 'Criando...' : '✓ Criar Rodada' }}
        </button>
        <button class="btn btn-ghost" @click="importStep = 'form'">← Voltar</button>
      </div>
    </template>
  </BaseModal>

  <!-- Finalize Modal -->
  <BaseModal v-if="showFinalize" @close="showFinalize = false">
    <template v-if="!finalizeResult">
      <h2>Finalizar Rodada</h2>
      <div class="stat-grid" style="margin-bottom:16px">
        <StatCard label="CAIXA DA NOITE"  :value="brl(caixaNoite)"  variant="green" />
        <StatCard label="PREMIAÇÃO (85%)" :value="brl(premiacao)" />
      </div>
      <div class="fin-row">
        <span class="fin-lbl">🥇 {{ player1st?.player_name || '— Não definido' }}</span>
        <span class="fin-val gold">{{ brl(premiacao * 0.7) }}</span>
      </div>
      <div class="fin-row">
        <span class="fin-lbl">🥈 {{ player2nd?.player_name || '— Não definido' }}</span>
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
      <!-- PIX section -->
      <div v-if="pixCodes.length" style="margin-top:16px;border-top:1px solid var(--border);padding-top:12px">
        <p style="font-size:11px;color:var(--text-dim);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">Cobranças via PIX ({{ pixCodes[0]?.receiverName }})</p>
        <div v-for="item in pixCodes" :key="item.player_name" class="fin-row" style="align-items:center;gap:8px">
          <span class="fin-lbl" style="flex:1">{{ item.player_name }}</span>
          <span style="color:var(--gold);font-size:13px;min-width:70px;text-align:right">{{ brl(item.valor) }}</span>
          <button
            class="btn btn-ghost"
            style="padding:4px 10px;font-size:11px;min-width:70px"
            @click="copyPixCode(item)"
          >{{ item.copied ? '✓ Copiado' : 'Copiar PIX' }}</button>
        </div>
      </div>
      <div v-else-if="finalizeResult" style="margin-top:12px;font-size:12px;color:var(--text-dim)">
        Cadastre a chave PIX no perfil de Marcio para gerar cobranças automáticas.
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
import { authApi, roundsApi, setAdminPassword } from '../api'
import { useAuth } from '../composables/useAuth'

const { currentRound, roundPlayers, allPlayers, fetchCurrent, fetchAllPlayers, startRound, addPlayer, updatePlayer, removePlayer, finalize } = useRounds()
const { config, fetch: fetchConfig } = useConfig()
const { show: toast } = useToast()
const { requireAuth } = useAuth()

const medals = ['🥇', '🥈', '🥉']

const selectedId = ref(null)
const showStartModal  = ref(false)
const showPlayerModal = ref(false)
const showFinalize    = ref(false)
const editingPlayer   = ref(null)
const finalizeResult  = ref(null)
const pixCodes        = ref([])
const saving          = ref(false)
const finalizing      = ref(false)
const starting        = ref(false)
const formError       = ref('')
const startError      = ref('')

const startForm = ref({ label: '', date: '', password: '' })

// ── CSV Import ───────────────────────────────────────────────────────────────
const showImportModal = ref(false)
const importStep      = ref('form')   // 'form' | 'preview'
const importForm      = ref({ label: '' })
const importFile      = ref(null)
const importPreview   = ref({ matched: [], unmatched: [] })
const importError     = ref('')
const importing       = ref(false)

function openImport() {
  importStep.value    = 'form'
  importForm.value    = { label: '' }
  importFile.value    = null
  importPreview.value = { matched: [], unmatched: [] }
  importError.value   = ''
  showImportModal.value = true
}

function closeImport() {
  showImportModal.value = false
}

function onFileChange(event) {
  const file = event.target.files[0] || null
  importError.value = ''
  importFile.value = file
}

function doAnalyze() {
  importError.value = ''
  if (!importFile.value) { importError.value = 'Selecione um arquivo CSV.'; return }
  requireAuth(async () => {
    importing.value = true
    try {
      const fd = new FormData()
      fd.append('file', importFile.value)
      fd.append('label', importForm.value.label || '')
      fd.append('dry_run', 'true')

      const { data } = await roundsApi.importCsv(fd)
      importPreview.value = data
      importStep.value = 'preview'
    } catch (e) {
      const detail = e.response?.data?.detail
      if (detail) {
        importError.value = Array.isArray(detail) ? detail.map(d => d.msg).join('; ') : detail
      } else {
        importError.value = `Erro: ${e.code ?? ''} ${e.message ?? ''} (HTTP ${e.response?.status ?? 'sem resposta'}).`
      }
    } finally {
      importing.value = false
    }
  })
}

async function doCreateRound() {
  importError.value = ''
  importing.value = true
  try {
    const fd = new FormData()
    fd.append('file', importFile.value)
    fd.append('label', importForm.value.label || '')
    fd.append('dry_run', 'false')

    const { data } = await roundsApi.importCsv(fd)
    pixCodes.value = []
    await fetchCurrent()
    closeImport()
    toast(`Rodada "${data.round_label}" criada com ${data.players_added} jogadores! ✓`)
  } catch (e) {
    importError.value = e.response?.data?.detail || 'Erro ao criar rodada.'
  } finally {
    importing.value = false
  }
}
const form = ref({
  name: '', buyin: 1, addon: 0, colocacao: 0,
  presenca: 10, bonus: 0, indicacao: 0, pontualidade: 15,
})

const presencaPts  = computed(() => config.value?.presence_points    ?? 10)
const pontPts      = computed(() => config.value?.punctuality_points  ?? 15)

function calcEntryValue(entries) {
  if (!entries || entries <= 0) return 0
  const buyinValue = config.value?.buyin_value ?? 50
  const rebuyValue = config.value?.rebuy_value ?? 50
  return buyinValue + Math.max(entries - 1, 0) * rebuyValue
}

const totalBuyins = computed(() => roundPlayers.value.reduce((s, p) => s + p.buyin, 0))
const totalAddons = computed(() => roundPlayers.value.reduce((s, p) => s + p.addon, 0))
const totalEntriesValue = computed(() => roundPlayers.value.reduce((s, p) => s + calcEntryValue(p.buyin), 0))
const caixaNoite  = computed(() =>
  totalEntriesValue.value +
  totalAddons.value * (config.value?.addon_value ?? 50)
)
const premiacao = computed(() => caixaNoite.value * 0.85)

// Calculates ranking points from placement using the prize pool formula.
// Points = int(prize_reais) // 10 → 2 digits for <R$1000, 3 for ≥R$1000.
function calcRoundPontos(colocacao) {
  const prizePool = caixaNoite.value * 0.85
  if (colocacao === 1) return Math.floor(prizePool * 0.70 / 10)
  if (colocacao === 2) return Math.floor(prizePool * 0.30 / 10)
  return 0
}

// Live preview for the form (includes the player being added if not editing)
const previewPontos = computed(() => {
  const addon_v = config.value?.addon_value ?? 50
  let totalEntries = totalEntriesValue.value
  let addons = totalAddons.value
  if (!editingPlayer.value) {
    totalEntries += calcEntryValue(form.value.buyin || 0)
    addons += form.value.addon || 0
  }
  const prizePool = (totalEntries + addons * addon_v) * 0.85
  if (form.value.colocacao === 1) return Math.floor(prizePool * 0.70 / 10)
  if (form.value.colocacao === 2) return Math.floor(prizePool * 0.30 / 10)
  return 0
})

const sortedPlayers = computed(() =>
  [...roundPlayers.value]
    .map(p => {
      const calcPontos = calcRoundPontos(p.colocacao || 0)
      const calcTotal  = calcPontos + (p.presenca || 0) + (p.bonus || 0) + (p.indicacao || 0) + (p.pontualidade || 0)
      return { ...p, calcPontos, calcTotal }
    })
    .sort((a, b) => b.calcTotal - a.calcTotal)
)

const leader    = computed(() => sortedPlayers.value[0] ?? null)
const player1st = computed(() => roundPlayers.value.find(p => (p.colocacao || 0) === 1) ?? null)
const player2nd = computed(() => roundPlayers.value.find(p => (p.colocacao || 0) === 2) ?? null)

// Positions already taken by OTHER players (not the one being edited)
const takenPositions = computed(() => {
  const editingId = editingPlayer.value?.player_id ?? null
  return new Set(
    roundPlayers.value
      .filter(p => p.player_id !== editingId && p.colocacao > 0)
      .map(p => p.colocacao)
  )
})

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
    name: '', buyin: 1, addon: 0, colocacao: 0,
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
  if (!selectedId.value) { toast('Selecione um jogador na tabela para editar.'); return }
  const p = roundPlayers.value.find(x => x.player_id === selectedId.value)
  if (!p) return
  editingPlayer.value = p
  form.value = {
    name: p.player_name,
    buyin: p.buyin, addon: p.addon, colocacao: p.colocacao || 0,
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
    pixCodes.value = []
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
  formError.value = ''
  requireAuth(async () => {
    saving.value = true
    try {
      if (editingPlayer.value) {
        await updatePlayer(editingPlayer.value.player_id, {
          buyin: form.value.buyin, addon: form.value.addon,
          colocacao: form.value.colocacao,
          presenca: form.value.presenca,
          bonus: form.value.bonus, indicacao: form.value.indicacao,
          pontualidade: form.value.pontualidade,
        })
        toast('Jogador atualizado! ✓')
      } else {
        await addPlayer({
          name: form.value.name.trim(),
          buyin: form.value.buyin, addon: form.value.addon,
          colocacao: form.value.colocacao,
          presenca: form.value.presenca,
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
  })
}

function doRemove() {
  if (!selectedId.value) { toast('Selecione um jogador na tabela para remover.'); return }
  const p = roundPlayers.value.find(x => x.player_id === selectedId.value)
  if (!p || !confirm(`Remover "${p.player_name}"?`)) return
  requireAuth(async () => {
    try {
      await removePlayer(selectedId.value)
      selectedId.value = null
      toast('Jogador removido.')
    } catch (e) {
      toast('Erro ao remover jogador.')
    }
  })
}

async function copyPixCode(item) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(item.code)
    } else {
      // Fallback for non-HTTPS or blocked clipboard
      const ta = document.createElement('textarea')
      ta.value = item.code
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    item.copied = true
    setTimeout(() => { item.copied = false }, 2000)
  } catch {
    toast('Não foi possível copiar. Tente manualmente.')
  }
}

function gerarPixCopiaCola(chave, nome, valor) {
  function fld(id, value) {
    return `${id}${String(value.length).padStart(2, '0')}${value}`
  }
  const mai = fld('00', 'br.gov.bcb.pix') + fld('01', chave)
  let p = fld('00', '01') + fld('01', '12') + fld('26', mai) +
          fld('52', '0000') + fld('53', '986') +
          (valor > 0 ? fld('54', valor.toFixed(2)) : '') +
          fld('58', 'BR') + fld('59', nome.substring(0, 25)) +
          fld('60', 'SAO PAULO') + '6304'
  let crc = 0xFFFF
  for (let i = 0; i < p.length; i++) {
    crc ^= p.charCodeAt(i) << 8
    for (let j = 0; j < 8; j++) crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) & 0xFFFF : (crc << 1) & 0xFFFF
  }
  return p + crc.toString(16).toUpperCase().padStart(4, '0')
}

function openFinalize() {
  const sem = roundPlayers.value.filter(p => !p.colocacao)
  if (sem.length) {
    toast(`Defina a colocação de: ${sem.map(p => p.player_name).join(', ')}`)
    return
  }
  showFinalize.value = true
}

function doFinalize() {
  requireAuth(async () => {
    // Snapshot buy-ins and PIX receiver's key before round data is cleared
    const marcio = config.value?.pix_receiver_player_id
      ? allPlayers.value.find(p => p.id === config.value.pix_receiver_player_id)
      : null
    const snapshot = roundPlayers.value.map(p => ({
      player_name: p.player_name,
      colocacao: p.colocacao,
      valor: calcEntryValue(p.buyin) + p.addon * (config.value?.addon_value || 50),
    }))

    finalizing.value = true
    try {
      finalizeResult.value = await finalize()
      if (marcio?.pix) {
        pixCodes.value = snapshot
          .filter(p => p.valor > 0 && p.colocacao !== 1 && p.colocacao !== 2)
          .map(p => ({
            player_name: p.player_name,
            receiverName: marcio.name,
            valor: p.valor,
            code: gerarPixCopiaCola(marcio.pix, marcio.name, p.valor),
            copied: false,
          }))
      } else {
        pixCodes.value = []
      }
      toast('Rodada finalizada e salva no ranking! ✓')
    } catch (e) {
      toast(e.response?.data?.detail || 'Erro ao finalizar.')
      showFinalize.value = false
    } finally {
      finalizing.value = false
    }
  })
}

onMounted(async () => {
  await Promise.all([fetchCurrent(), fetchAllPlayers(), fetchConfig()])
})
</script>
