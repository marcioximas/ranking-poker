<template>
  <div>
    <p style="font-size:13px;color:var(--text-dim);margin-bottom:20px">
      Configurações aplicadas em todas as rodadas novas.
    </p>

    <div class="config-grid" v-if="form">
      <div class="field">
        <label for="cfg-tournament-name">Nome do torneio</label>
        <input id="cfg-tournament-name" type="text" v-model="form.tournament_name" />
      </div>
      <div class="field">
        <label for="cfg-buyin">Buy-in (R$)</label>
        <input id="cfg-buyin" type="number" v-model.number="form.buyin_value" min="0" step="0.5" />
      </div>
      <div class="field">
        <label for="cfg-rebuy">Rebuy (R$)</label>
        <input id="cfg-rebuy" type="number" v-model.number="form.rebuy_value" min="0" step="0.5" />
      </div>
      <div class="field">
        <label for="cfg-addon">Addon (R$)</label>
        <input id="cfg-addon" type="number" v-model.number="form.addon_value" min="0" step="0.5" />
      </div>
      <div class="field">
        <label for="cfg-presence">Pontos presença</label>
        <input id="cfg-presence" type="number" v-model.number="form.presence_points" min="0" />
      </div>
      <div class="field">
        <label for="cfg-punctuality">Pontos pontualidade</label>
        <input id="cfg-punctuality" type="number" v-model.number="form.punctuality_points" min="0" />
      </div>
      <div class="field">
        <label for="cfg-itm">Bônus ITM (pontos)</label>
        <input id="cfg-itm" type="number" v-model.number="form.itm_bonus_points" min="0" />
      </div>
      <div class="field">
        <label for="cfg-prize-pct">% Premiação da noite</label>
        <input id="cfg-prize-pct" type="number" v-model.number="form.prize_pct" min="0" max="100" />
      </div>
      <div class="field">
        <label for="cfg-ranking-pct">% Ranking da noite</label>
        <input id="cfg-ranking-pct" type="number" v-model.number="form.ranking_pct" min="0" max="100" />
      </div>
      <div class="field" style="grid-column: 1 / -1">
        <label for="cfg-pix-receiver">Jogador que recebe o PIX</label>
        <select id="cfg-pix-receiver" v-model.number="form.pix_receiver_player_id">
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
import { useToast } from '../composables/useToast'
import { useAuth } from '../composables/useAuth'
import { playersApi } from '../api'

const { config, fetch, save } = useConfig()
const { show: toast } = useToast()
const { requireAuth } = useAuth()

const form    = ref(null)
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
      await save(form.value)
      toast('Configurações salvas! ✓')
    } catch {
      toast('Erro ao salvar configurações.')
    } finally {
      saving.value = false
    }
  })
}

onMounted(async () => {
  const [, { data }] = await Promise.all([fetch(), playersApi.list()])
  players.value = data
  form.value = { ...config.value }
  if (form.value.rebuy_value == null) {
    form.value.rebuy_value = form.value.buyin_value ?? 50
  }
  if (!form.value.pix_receiver_player_id) {
    const marcio = data.find(p => p.name.toLowerCase() === 'marcio ximas')
    if (marcio) form.value.pix_receiver_player_id = marcio.id
  }
})
</script>
