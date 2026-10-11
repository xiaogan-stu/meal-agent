<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import MealCard from '../components/MealCard.vue'
import MealForm from '../components/MealForm.vue'
import NoticeBanner from '../components/NoticeBanner.vue'
import {
  createPersonalMeal,
  deletePersonalMeal,
  getPersonalMeals,
  getSlotOptions,
  updatePersonalMeal,
} from '../api/diet'
import { useAppStore } from '../stores/app'
import type {
  MealRequest,
  MealResponse,
  SlotOptionMap,
} from '../types/diet'
import { emptySlots } from '../utils/slots'
import { getErrorMessage } from '../utils/error'

const appStore = useAppStore()
const { userId } = storeToRefs(appStore)

const meals = ref<MealResponse[]>([])
const options = ref<SlotOptionMap>(emptySlots())
const editingMeal = ref<MealResponse | null>(null)
const loading = ref(true)
const saving = ref(false)
const notice = ref('')
const noticeType = ref<'info' | 'success' | 'error'>('info')

async function load(): Promise<void> {
  loading.value = true
  notice.value = ''
  try {
    const [mealRows, optionMap] = await Promise.all([
      getPersonalMeals(),
      getSlotOptions(),
    ])
    meals.value = mealRows
    options.value = optionMap
    editingMeal.value = null
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function save(payload: MealRequest): Promise<void> {
  saving.value = true
  notice.value = ''
  try {
    if (editingMeal.value) {
      await updatePersonalMeal(editingMeal.value.id, payload)
      notice.value = '餐食已更新。'
    } else {
      await createPersonalMeal(payload)
      notice.value = '餐食已加入我的食单。'
    }
    noticeType.value = 'success'
    await load()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

async function remove(meal: MealResponse): Promise<void> {
  const confirmed = window.confirm('确定删除“' + meal.name + '”吗？')
  if (!confirmed) return

  try {
    await deletePersonalMeal(meal.id)
    noticeType.value = 'success'
    notice.value = '餐食已删除。'
    await load()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  }
}

onMounted(load)
watch(userId, load)
</script>

<template>
  <div class="page-stack">
    <section class="page-intro">
      <div>
        <span class="eyebrow">我的食单</span>
        <h1>把常吃的，变成更懂你的候选</h1>
        <p>维护用户 {{ userId }} 的个人餐食。餐次必选，其余标签按实际情况填写。</p>
      </div>
      <button class="button button-primary" type="button" @click="editingMeal = null">
        新增餐食
      </button>
    </section>

    <NoticeBanner :message="notice" :type="noticeType" />

    <div class="meal-admin-layout">
      <section>
        <div v-if="loading" class="empty-state">正在加载我的食单…</div>
        <div v-else-if="meals.length === 0" class="empty-state">
          <strong>还没有个人餐食</strong>
          <p>先在右侧记录一道常吃的菜，再去宜食问答切换到“我的食单”。</p>
        </div>
        <div v-else class="meal-grid">
          <MealCard
            v-for="meal in meals"
            :key="meal.id"
            :meal="meal"
            mode="personal"
            @edit="editingMeal = $event"
            @remove="remove"
          />
        </div>
      </section>

      <aside class="form-panel">
        <MealForm
          :meal="editingMeal"
          :options="options"
          :saving="saving"
          @submit="save"
          @cancel="editingMeal = null"
        />
      </aside>
    </div>
  </div>
</template>