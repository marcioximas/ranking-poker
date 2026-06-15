<template>
  <div>
    <p style="font-size:13px;color:var(--text-dim);margin-bottom:20px">
      Configurações aplicadas em todas as rodadas novas.
    </p>

    <div class="config-grid" v-if="form">
      <div class="field">
        <label>Nome do torneio</label>
        <input type="text" v-model="form.tournament_name" />
      </div>
      <div class="field">
        <label>Buy-in / Rebuy (R$)</label>
        <input type="number" v-model.number="form.buyin_value" min="0" step="0.5" />
      </div>
      <div class="field">
        <label>Addon (R$)</label>
        <input type="number" v-model.number="form.addon_value" min="0" step="0.5" />
      </div>
      <div class="field">
        <label>Pontos presença</label>
        <input type="number" v-model.number="form.presence_points" min="0" />
      </div>
      <div class="field">
        <label>Pontos pontualidade</label>
        <input type="number" v-model.number="form.punctuality_points" min="0" />
      </div>
      <div class="field">
        <label>Bônus ITM (pontos)</label>
        <input type="number" v-model.number="form.itm_bonus_points" min="0" />
      </div>
      <div class="field">
        <label>% Premiação da noite</label>
        <input type="number" v-model.number="form.prize_pct" min="0" max="100" />
      </div>
      <div class="field">
        <label>% Ranking da noite</label>
        <input type="number" v-model.number="form.ranking_pct" min="0" max="100" />
      </div>
      <div class="field">
        <label>Caixa Anterior (R$)</label>
        <input type="number" v-model.number="fin.caixa_anterior" step="0.01" min="0" />
      </div>
      <div class="field">
        <label>Ranking Anterior (R$)</label>
        <input type="number" v-model.number="fin.ranking_anterior" step="0.01" min="0" />
      </div>
      <div class="field" style="grid-column: 1 / -1">
        <label>Jogador que recebe o PIX</label>
        <select v-model.number="form.pix_receiver_player_id">
          <option :value="null">— Nenhum —</option>
          <option v-for="p in players" :key="p.id" :value="p.id">
            {{ p.name }}{{ p.pix ? ' — ' + p.pix : ' (sem PIX cadastrado)' }}
          </option>
        </select>
        <p v-if="selectedReceiver && !selectedReceiver.pix" style="font-size:11px;color:var(--red);margin-top:4px">
          Este jogador não tem chave PIX cadastrada. Edite o perfil dele na aba Jogadores.
        </p>
      </div>
    </div>
    <br>
    <button class="btn btn-gold" @click="doSave" :disabled="saving">
      {{ saving ? 'Salvando...' : 'Salvar Configurações' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useConfig } from '../stores/config'
import { useFinancial } from '../stores/financial'
import { useToast } from '../composables/useToast'
import { useAuth } from '../composables/useAuth'
import { playersApi } from '../api'

const { config, fetch, save } = useConfig()
const { summary: finSummary, fetch: fetchFin, updateFinancial } = useFinancial()
const { show: toast } = useToast()
const { requireAuth } = useAuth()

const form    = ref(null)
const fin     = ref({ caixa_anterior: 0, ranking_anterior: 0 })
const saving  = ref(false)
const players = ref([])

const selectedReceiver = computed(() =>
  form.value?.pix_receiver_player_id
    ? players.value.find(p => p.id === form.value.pix_receiver_player_id) ?? null
    : null
)

function doSave() {
  requireAuth(async () => {
    saving.value = true
    try {
      await Promise.all([
        save(form.value),
        updateFinancial({ caixa_anterior: fin.value.caixa_anterior, ranking_anterior: fin.value.ranking_anterior }),
      ])
      toast('Configurações salvas! ✓')
    } catch {
      toast('Erro ao salvar configurações.')
    } finally {
      saving.value = false
    }
  })
}

onMounted(async () => {
  const [, { data }] = await Promise.all([fetch(), playersApi.list(), fetchFin()])
  players.value = data

  form.value = { ...config.value }

  if (!form.value.pix_receiver_player_id) {
    const marcio = data.find(p => p.name.toLowerCase() === 'marcio ximas')
    if (marcio) form.value.pix_receiver_player_id = marcio.id
  }

  fin.value.caixa_anterior   = finSummary.value?.caixa_anterior   ?? 0
  fin.value.ranking_anterior = finSummary.value?.ranking_anterior ?? 0
})
</script>
