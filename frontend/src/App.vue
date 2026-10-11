<script setup lang="ts">
import AppHeader from './components/AppHeader.vue'
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <main class="page-shell">
      <RouterView />
    </main>
    <footer class="site-footer">
      <span>今日宜食 · 情境感知型饮食决策 Agent</span>
    </footer>
  </div>
</template>