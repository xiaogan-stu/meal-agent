<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import TagSelector from './TagSelector.vue'
import type {
  MealRequest,
  MealResponse,
  SlotKey,
  SlotOptionMap,
} from '../types/diet'
import {
  SLOT_KEYS,
  SLOT_LABELS,
  cloneSlots,
  emptyMealRequest,
} from '../utils/slots'

const props = defineProps<{
  meal: MealResponse | null
  options: SlotOptionMap
  saving: boolean
}>()

const emit = defineEmits<{
  submit: [payload: MealRequest]
  cancel: []
}>()

const form = reactive<MealRequest>(emptyMealRequest())
const validationMessage = ref('')

watch(
  () => props.meal,
  (meal) => {
    const next = meal
      ? { name: meal.name, ...cloneSlots(meal) }
      : emptyMealRequest()

    form.name = next.name
    for (const key of SLOT_KEYS) {
      form[key] = [...next[key]]
    }
    validationMessage.value = ''
  },
  { immediate: true },
)

function updateSlot(key: SlotKey, values: string[]): void {
  form[key] = values
}

function submit(): void {
  const name = form.name.trim()
  if (!name) {
    validationMessage.value = '请输入餐食名称。'
    return
  }
  if (form.mealTime.length === 0) {
    validationMessage.value = '餐次至少选择一项。'
    return
  }

  validationMessage.value = ''
  emit('submit', {
    name,
    ...cloneSlots(form),
  })
}
</script>

<template>
  <form class="meal-form" @submit.prevent="submit">
    <div class="section-heading compact">
      <div>
        <span class="eyebrow">{{ meal ? '编辑食单' : '新增食单' }}</span>
        <h2>{{ meal ? meal.name : '记录一道常吃的餐食' }}</h2>
      </div>
    </div>

    <label class="form-field">
      <span>餐食名称</span>
      <input
        v-model="form.name"
        type="text"
        maxlength="100"
        placeholder="例如：番茄鸡蛋面"
      />
    </label>

    <TagSelector
      v-for="key in SLOT_KEYS"
      :key="key"
      :label="SLOT_LABELS[key]"
      :options="options[key]"
      :model-value="form[key]"
      :required="key === 'mealTime'"
      @update:model-value="updateSlot(key, $event)"
    />

    <p v-if="validationMessage" class="form-error">{{ validationMessage }}</p>

    <div class="form-actions">
      <button class="button button-primary" type="submit" :disabled="saving">
        {{ saving ? '保存中…' : meal ? '保存修改' : '加入我的食单' }}
      </button>
      <button class="button button-ghost" type="button" @click="emit('cancel')">
        清空
      </button>
    </div>
  </form>
</template>