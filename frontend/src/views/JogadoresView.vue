<template>
  <div>
    <!-- Stats -->
    <div class="stat-grid">
      <StatCard label="JOGADORES CADASTRADOS" :value="players.length" variant="white" />
      <StatCard label="COM TELEFONE" :value="players.filter(p => p.telefone).length" variant="white" />
      <StatCard label="COM PIX"      :value="players.filter(p => p.pix).length"      variant="white" />
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <button class="btn btn-primary" @click="openCreate">+ Novo Jogador</button>
    </div>

    <!-- Table -->
    <div class="table-wrap">
      <table v-if="players.length">
        <thead>
          <tr>
            <th style="width:44px">#</th>
            <th style="width:160px">Nome</th>
            <th>Telefone</th>
            <th>PIX</th>
            <th style="width:110px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(p, i) in players" :key="p.id">
            <td class="zero">{{ i + 1 }}</td>
            <td class="name">{{ p.name }}</td>
            <td :class="p.telefone ? 'num' : 'zero'">{{ p.telefone || '—' }}</td>
            <td :class="p.pix ? 'num' : 'zero'">{{ p.pix || '—' }}</td>
            <td style="text-align:right;padding-right:8px">
              <button class="btn btn-ghost btn-sm" @click="openEdit(p)" style="margin-right:4px">✎ Editar</button>
              <button class="btn btn-danger btn-sm" @click="doRemove(p)">✕</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">
        <div class="empty-icon">♠</div>
        <p>Nenhum jogador cadastrado ainda.</p>
      </div>
    </div>
  </div>

  <!-- Create / Edit Modal -->
  <BaseModal v-if="showModal" @close="closeModal">
    <h2>{{ editing ? 'Editar Jogador' : 'Novo Jogador' }}</h2>
    <div class="form-grid">
      <div class="field full">
        <label>Nome *</label>
        <input
          type="text"
          v-model="form.name"
          placeholder="Nome do jogador"
          autofocus
          @keyup.enter="doSave"
        />
      </div>
      <div class="field full">
        <label>Telefone</label>
        <input
          type="tel"
          v-model="form.telefone"
          placeholder="(00) 00000-0000"
          @keyup.enter="doSave"
        />
      </div>
      <div class="field full">
        <label>PIX</label>
        <input
          type="text"
          v-model="form.pix"
          placeholder="Chave PIX (telefone, CPF, e-mail ou aleatória)"
          @keyup.enter="doSave"
        />
      </div>
    </div>
    <div v-if="formError" style="color:var(--red);font-size:12px;margin-top:8px">{{ formError }}</div>
    <div class="modal-actions">
      <button class="btn btn-gold" @click="doSave" :disabled="saving">
        {{ saving ? 'Salvando...' : 'Salvar' }}
      </button>
      <button class="btn btn-ghost" @click="closeModal">Cancelar</button>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import StatCard  from '../components/StatCard.vue'
import BaseModal from '../components/BaseModal.vue'
import { playersApi } from '../api'
import { useAuth }  from '../composables/useAuth'
import { useToast } from '../composables/useToast'

const { requireAuth } = useAuth()
const { show: toast } = useToast()

const players   = ref([])
const showModal = ref(false)
const editing   = ref(null)   // Player object being edited, or null for create
const saving    = ref(false)
const formError = ref('')

const form = ref({ name: '', telefone: '', pix: '' })

async function load() {
  const { data } = await playersApi.list()
  players.value = data
}

function openCreate() {
  requireAuth(() => {
    editing.value = null
    form.value = { name: '', telefone: '', pix: '' }
    formError.value = ''
    showModal.value = true
  })
}

function openEdit(player) {
  requireAuth(() => {
    editing.value = player
    form.value = {
      name:     player.name,
      telefone: player.telefone || '',
      pix:      player.pix || '',
    }
    formError.value = ''
    showModal.value = true
  })
}

function closeModal() {
  showModal.value = false
  formError.value = ''
}

async function doSave() {
  if (!form.value.name.trim()) {
    formError.value = 'O nome é obrigatório.'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    const payload = {
      name:     form.value.name.trim(),
      telefone: form.value.telefone.trim() || null,
      pix:      form.value.pix.trim() || null,
    }
    if (editing.value) {
      await playersApi.update(editing.value.id, payload)
      toast(`${payload.name} atualizado ✓`)
    } else {
      await playersApi.create(payload)
      toast(`${payload.name} cadastrado ✓`)
    }
    await load()
    closeModal()
  } catch (e) {
    formError.value = e.response?.data?.detail || 'Erro ao salvar jogador.'
  } finally {
    saving.value = false
  }
}

async function doRemove(player) {
  requireAuth(async () => {
    if (!confirm(`Excluir "${player.name}"? Esta ação remove todos os dados do jogador.`)) return
    try {
      await playersApi.remove(player.id)
      await load()
      toast(`"${player.name}" removido ✓`)
    } catch (e) {
      toast(e.response?.data?.detail || 'Erro ao remover jogador.')
    }
  })
}

onMounted(load)
</script>
