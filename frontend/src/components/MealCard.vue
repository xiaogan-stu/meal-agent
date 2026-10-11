<script setup lang="ts">
import { computed } from 'vue'
import type { MealResponse } from '../types/diet'
import { collectMealTags } from '../utils/slots'

const props = withDefaults(
  defineProps<{
    meal: MealResponse
    mode?: 'catalog' | 'personal' | 'recommendation'
  }>(),
  { mode: 'catalog' },
)

const emit = defineEmits<{
  edit: [meal: MealResponse]
  remove: [meal: MealResponse]
  feedback: [meal: MealResponse, action: 'LIKE' | 'ADOPT' | 'DISLIKE']
}>()

const tags = computed(() => collectMealTags(props.meal))
const score = computed(() => Math.round(props.meal.matchScore * 100))
</script>

<template>
  <article class="meal-card">
    <div class="meal-card-head">
      <div>
        <span class="eyebrow">
          {{ meal.sourceType === 'PERSONAL' ? '我的食单' : '灵感食单' }}
        </span>
        <h3>{{ meal.name }}</h3>
      </div>
      <span v-if="mode === 'recommendation'" class="match-score">
        匹配 {{ score }}%
      </span>
    </div>

    <div class="tag-list">
      <span v-for="tag in tags" :key="tag" class="tag">今日宜 · {{ tag }}</span>
      <span v-if="tags.length === 0" class="muted">暂无标签</span>
    </div>

    <div v-if="mode === 'personal'" class="card-actions">
      <button class="button button-soft" type="button" @click="emit('edit', meal)">
        编辑
      </button>
      <button class="button button-ghost danger" type="button" @click="emit('remove', meal)">
        删除
      </button>
    </div>

    <div v-if="mode === 'recommendation'" class="card-actions">
      <button
        class="button button-soft"
        type="button"
        @click="emit('feedback', meal, 'LIKE')"
      >
        喜欢
      </button>
      <button
        class="button button-primary"
        type="button"
        @click="emit('feedback', meal, 'ADOPT')"
      >
        采纳
      </button>
      <button
        class="button button-ghost"
        type="button"
        @click="emit('feedback', meal, 'DISLIKE')"
      >
        不合适
      </button>
    </div>
  </article>
</template>