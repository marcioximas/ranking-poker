<template>
  <div class="stat-card">
    <div class="lbl">{{ label }}</div>
    <div class="val" :class="variant">{{ value }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: String,
  value: [String, Number],
  variant: { type: String, default: '' },
})
</script>
