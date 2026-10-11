<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import MealCard from '../components/MealCard.vue'
import NoticeBanner from '../components/NoticeBanner.vue'
import { getPublicMeals } from '../api/diet'
import type { MealResponse } from '../types/diet'
import { collectMealTags } from '../utils/slots'
import { getErrorMessage } from '../utils/error'

const meals = ref<MealResponse[]>([])
const keyword = ref('')
const loading = ref(true)
const errorMessage = ref('')

const filteredMeals = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return meals.value

  return meals.value.filter((meal) => {
    const searchable = [meal.name, ...collectMealTags(meal)]
      .join(' ')
      .toLowerCase()
    return searchable.includes(query)
  })
})

onMounted(async () => {
  try {
    meals.value = await getPublicMeals()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-stack">
    <section class="page-intro">
      <div>
        <span class="eyebrow">灵感食单</span>
        <h1>没有明确想法时，从这里找一点灵感</h1>
        <p>这里展示公共餐食库。列表中的匹配分固定为 0，只有聊天推荐会计算匹配度。</p>
      </div>
      <label class="search-box">
        <span>搜索</span>
        <input v-model="keyword" type="search" placeholder="餐食名称或标签" />
      </label>
    </section>

    <NoticeBanner :message="errorMessage" type="error" />

    <div v-if="loading" class="empty-state">正在加载灵感食单…</div>
    <div v-else-if="filteredMeals.length === 0" class="empty-state">
      <strong>没有找到匹配的餐食</strong>
      <p>尝试搜索“清淡”“晚餐”或“快速”。</p>
    </div>
    <div v-else class="meal-grid">
      <MealCard
        v-for="meal in filteredMeals"
        :key="meal.id"
        :meal="meal"
      />
    </div>
  </div>
</template>