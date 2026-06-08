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
    </div>
    <br>
    <button class="btn btn-gold" @click="doSave" :disabled="saving">
      {{ saving ? 'Salvando...' : 'Salvar Configurações' }}
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useConfig } from '../stores/config'
import { useToast } from '../composables/useToast'

const { config, fetch, save } = useConfig()
const { show: toast } = useToast()

const form   = ref(null)
const saving = ref(false)

async function doSave() {
  saving.value = true
  try {
    await save(form.value)
    toast('Configurações salvas! ✓')
  } catch {
    toast('Erro ao salvar configurações.')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await fetch()
  form.value = { ...config.value }
})
</script>
