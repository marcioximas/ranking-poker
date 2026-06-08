<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineEmits(['close'])
</script>
