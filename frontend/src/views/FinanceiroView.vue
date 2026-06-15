<template>
  <div>
    <!-- Stats -->
    <div class="stat-grid" v-if="summary">
      <StatCard label="CAIXA ATUAL"       :value="brl(summary.caixa_atual)"        variant="gold" />
      <StatCard label="RANKING TOTAL"     :value="brl(summary.ranking_total)"       variant="gold" />
      <StatCard label="PREMIAÇÃO DA NOITE" :value="brl(summary.premiacao_total)"    variant="green" />
      <StatCard label="CAIXA C/ DESPESAS"
        :value="brl(summary.caixa_com_despesas)"
        :variant="summary.caixa_com_despesas >= 0 ? 'green' : 'red'"
      />
    </div>

    <div class="fin-layout">
      <!-- Left: Expenses + histórico -->
      <div>
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <p class="fin-section-title" style="margin:0">DESPESAS</p>
          <button class="btn btn-primary btn-sm" @click="openAddExpense">+ Adicionar</button>
        </div>

        <div v-for="e in expenses" :key="e.id" class="fin-input-row">
          <label :title="e.name">{{ e.name }}</label>
          <input
            type="number"
            :value="e.value"
            step="0.01"
            style="width:110px;text-align:right"
            @change="onExpenseChange(e, $event)"
          />
          <button class="btn btn-danger btn-sm" style="padding:4px 8px" @click="doRemoveExpense(e)">✕</button>
        </div>
        <p v-if="!expenses.length" style="font-size:12px;color:var(--text-faint);padding:8px 0">
          Nenhuma despesa cadastrada.
        </p>

        <br>
        <p class="fin-section-title">HISTÓRICO</p>
        <div class="fin-row">
          <span class="fin-lbl">Caixa Anterior (R$)</span>
          <span class="fin-val">{{ brl(cxAnt) }}</span>
        </div>
        <div class="fin-row">
          <span class="fin-lbl">Ranking Anterior (R$)</span>
          <span class="fin-val">{{ brl(rkAnt) }}</span>
        </div>
        <p style="font-size:11px;color:var(--text-faint);margin-top:6px">Altere em Configurações.</p>
      </div>

      <!-- Right: Summary -->
      <div v-if="summary">
        <p class="fin-section-title">RESUMO FINANCEIRO</p>
        <div class="fin-row"><span class="fin-lbl">Caixa da noite</span>         <span class="fin-val green">{{ brl(summary.caixa_noite) }}</span></div>
        <div class="fin-row"><span class="fin-lbl">Caixa anterior</span>          <span class="fin-val">{{ brl(summary.caixa_anterior) }}</span></div>
        <div class="fin-row"><span class="fin-lbl">Caixa atual</span>             <span class="fin-val gold">{{ brl(summary.caixa_atual) }}</span></div>
        <div class="fin-row"><span class="fin-lbl">Total despesas</span>          <span class="fin-val red">- {{ brl(summary.total_despesas) }}</span></div>
        <div class="fin-row"><span class="fin-lbl">Caixa c/ despesas</span>
          <span class="fin-val" :class="summary.caixa_com_despesas >= 0 ? 'green' : 'red'">
            {{ summary.caixa_com_despesas < 0 ? '- ' : '' }}{{ brl(summary.caixa_com_despesas) }}
          </span>
        </div>
        <div class="fin-row"><span class="fin-lbl">Premiação ({{ pct(summary) }})</span><span class="fin-val gold">{{ brl(summary.premiacao_total) }}</span></div>
        <div class="fin-row"><span class="fin-lbl">Ranking noite</span>           <span class="fin-val">{{ brl(summary.ranking_noite) }}</span></div>
        <div class="fin-row"><span class="fin-lbl">Ranking anterior</span>        <span class="fin-val">{{ brl(summary.ranking_anterior) }}</span></div>
        <div class="fin-row"><span class="fin-lbl">Ranking total</span>           <span class="fin-val gold">{{ brl(summary.ranking_total) }}</span></div>

        <br>
        <p class="fin-section-title">PREMIAÇÃO DA NOITE</p>
        <div class="fin-row"><span class="fin-lbl">🥇 1º lugar (70%)</span><span class="fin-val gold">{{ brl(summary.premiacao_1) }}</span></div>
        <div class="fin-row"><span class="fin-lbl">🥈 2º lugar (30%)</span><span class="fin-val">{{ brl(summary.premiacao_2) }}</span></div>
      </div>
    </div>
  </div>

  <!-- Add Expense Modal -->
  <BaseModal v-if="showExpenseModal" @close="showExpenseModal = false">
    <h2>Nova Despesa</h2>
    <div class="form-grid">
      <div class="field full">
        <label>Nome</label>
        <input type="text" v-model="expForm.name" placeholder="ex: Mesa, Fichas, Bebida..." autofocus />
      </div>
      <div class="field full">
        <label>Valor (R$)</label>
        <input type="number" v-model.number="expForm.value" min="0" step="0.01" />
      </div>
    </div>
    <div v-if="expError" style="color:var(--red);font-size:12px;margin-top:8px">{{ expError }}</div>
    <div class="modal-actions">
      <button class="btn btn-primary" @click="doAddExpense">Adicionar</button>
      <button class="btn btn-ghost"   @click="showExpenseModal = false">Cancelar</button>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import StatCard from '../components/StatCard.vue'
import BaseModal from '../components/BaseModal.vue'
import { useFinancial } from '../stores/financial'
import { useToast } from '../composables/useToast'
import { useAuth } from '../composables/useAuth'

const { summary, expenses, fetch, createExpense, updateExpense, removeExpense } = useFinancial()
const { show: toast } = useToast()
const { requireAuth } = useAuth()

const cxAnt = ref(0)
const rkAnt = ref(0)
const showExpenseModal = ref(false)
const expForm = ref({ name: '', value: 0 })
const expError = ref('')

const brl = (v) => {
  const n = Math.abs(v || 0)
  return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
const pct = (s) => s ? `${Math.round(s.premiacao_total / (s.caixa_noite || 1) * 100)}%` : '70%'

function onExpenseChange(expense, event) {
  const val = parseFloat(event.target.value) || 0
  requireAuth(async () => {
    try {
      await updateExpense(expense.id, { value: val })
    } catch {
      toast('Erro ao atualizar despesa.')
    }
  })
}

function doRemoveExpense(expense) {
  if (!confirm(`Remover despesa "${expense.name}"?`)) return
  requireAuth(async () => {
    try {
      await removeExpense(expense.id)
      toast(`Despesa "${expense.name}" removida.`)
    } catch {
      toast('Erro ao remover despesa.')
    }
  })
}

function openAddExpense() {
  requireAuth(() => {
    expForm.value = { name: '', value: 0 }
    expError.value = ''
    showExpenseModal.value = true
  })
}

async function doAddExpense() {
  if (!expForm.value.name.trim()) { expError.value = 'Informe o nome da despesa.'; return }
  try {
    await createExpense({ name: expForm.value.name.trim(), value: expForm.value.value })
    showExpenseModal.value = false
    toast(`Despesa "${expForm.value.name}" adicionada! ✓`)
  } catch (e) {
    expError.value = e.response?.data?.detail || 'Erro ao adicionar.'
  }
}

onMounted(async () => {
  await fetch()
  if (summary.value) {
    cxAnt.value = summary.value.caixa_anterior
    rkAnt.value = summary.value.ranking_anterior
  }
})
</script>
