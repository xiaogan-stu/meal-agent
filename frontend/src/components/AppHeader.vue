<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()
const { userId } = storeToRefs(appStore)
const menuOpen = ref(false)

function updateUserId(event: Event): void {
  const value = Number((event.target as HTMLInputElement).value)
  appStore.setUserId(value)
}
</script>

<template>
  <header class="site-header">
    <RouterLink class="brand" to="/" @click="menuOpen = false">
      <span class="brand-mark" aria-hidden="true">
        <span class="brand-sun"></span>
        <span class="brand-bowl"></span>
      </span>
      <span>
        <strong>今日宜食</strong>
        <small>读懂此刻，选好这一餐</small>
      </span>
    </RouterLink>

    <button
      class="menu-button"
      type="button"
      aria-label="展开导航"
      @click="menuOpen = !menuOpen"
    >
      ☰
    </button>

    <nav class="main-nav" :class="{ open: menuOpen }">
      <RouterLink to="/" @click="menuOpen = false">今日</RouterLink>
      <RouterLink to="/chat" @click="menuOpen = false">宜食问答</RouterLink>
      <RouterLink to="/meals/personal" @click="menuOpen = false">
        我的食单
      </RouterLink>
      <RouterLink to="/meals/public" @click="menuOpen = false">
        灵感食单
      </RouterLink>
      <RouterLink class="lab-link" to="/lab/traces" @click="menuOpen = false">
        宜食 Lab
      </RouterLink>
    </nav>

    <label class="user-switcher">
      <span>调试用户</span>
      <input
        :value="userId"
        type="number"
        min="1"
        aria-label="用户 ID"
        @change="updateUserId"
      />
    </label>
  </header>
</template>