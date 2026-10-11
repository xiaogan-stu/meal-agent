<script setup lang="ts">
defineProps<{
  message: string
  type?: 'info' | 'success' | 'error'
}>()
</script>

<template>
  <div v-if="message" class="notice" :class="'notice-' + (type || 'info')">
    {{ message }}
  </div>
</template>