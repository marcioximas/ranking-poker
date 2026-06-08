<template>
  <header>
    <div class="logo">♠ Poker Night</div>
    <span class="header-date">{{ headerDate }}</span>
    <button v-if="auth.isUnlocked.value" class="btn btn-ghost btn-sm" @click="auth.lock()" style="margin-left:8px">
      🔒 Bloquear
    </button>
  </header>

  <nav>
    <button :class="{ active: tab === 'rodada' }"     @click="setTab('rodada')">Rodada Atual</button>
    <button :class="{ active: tab === 'ranking' }"    @click="setTab('ranking')">Ranking Semestral</button>
    <button :class="{ active: tab === 'financeiro' }" @click="setTab('financeiro', true)">Financeiro</button>
    <button :class="{ active: tab === 'config' }"     @click="setTab('config', true)">Configurações</button>
  </nav>

  <main>
    <RodadaView    v-if="tab === 'rodada'" />
    <RankingView   v-else-if="tab === 'ranking'" />
    <FinanceiroView v-else-if="tab === 'financeiro'" />
    <ConfigView    v-else-if="tab === 'config'" />
  </main>

  <footer>♠ Poker Night Manager — API {{ apiBase }}</footer>

  <!-- Auth Modal -->
  <BaseModal v-if="auth.showModal.value" @close="auth.cancel()">
    <h2>Autenticação</h2>
    <p style="font-size:13px;color:var(--text-dim);margin-bottom:16px">
      Digite a senha para acessar esta área.
    </p>
    <div class="field">
      <label>Senha</label>
      <input
        type="password"
        v-model="authPassword"
        autofocus
        @keyup.enter="doAuth"
        placeholder="••••••••"
      />
    </div>
    <div v-if="auth.authError.value" style="color:var(--red);font-size:12px;margin-top:8px">
      {{ auth.authError.value }}
    </div>
    <div class="modal-actions">
      <button class="btn btn-gold"  @click="doAuth" :disabled="authing">
        {{ authing ? 'Verificando...' : 'Entrar' }}
      </button>
      <button class="btn btn-ghost" @click="auth.cancel()">Cancelar</button>
    </div>
  </BaseModal>

  <!-- Toast -->
  <div id="toast" :class="{ show: toast.visible.value }">{{ toast.message.value }}</div>
</template>

<script setup>
import { ref, computed } from 'vue'
import BaseModal      from './components/BaseModal.vue'
import RodadaView     from './views/RodadaView.vue'
import RankingView    from './views/RankingView.vue'
import FinanceiroView from './views/FinanceiroView.vue'
import ConfigView     from './views/ConfigView.vue'
import { useAuth }    from './composables/useAuth'
import { useToast }   from './composables/useToast'

const auth  = useAuth()
const toast = useToast()

const tab          = ref('rodada')
const authPassword = ref('')
const authing      = ref(false)

const apiBase    = import.meta.env.VITE_API_URL || '/api'
const headerDate = computed(() =>
  new Date().toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'long', year: 'numeric' })
)

function setTab(name, requiresAuth = false) {
  if (requiresAuth) {
    auth.requireAuth(() => { tab.value = name })
  } else {
    tab.value = name
  }
}

async function doAuth() {
  if (authing.value) return
  authing.value = true
  await auth.submit(authPassword.value)
  authPassword.value = ''
  authing.value = false
}
</script>
