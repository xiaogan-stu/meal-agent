<script setup lang="ts">
import MealCard from './MealCard.vue'
import type { MealResponse, UiChatMessage } from '../types/diet'
import { SLOT_LABELS } from '../utils/slots'

defineProps<{
  message: UiChatMessage
}>()

const emit = defineEmits<{
  feedback: [
    meal: MealResponse,
    action: 'LIKE' | 'ADOPT' | 'DISLIKE',
  ]
}>()

function slotLabel(value: string): string {
  const labels = SLOT_LABELS as Record<string, string>
  return labels[value] || value
}

function forwardFeedback(
  meal: MealResponse,
  action: 'LIKE' | 'ADOPT' | 'DISLIKE',
): void {
  emit('feedback', meal, action)
}
</script>

<template>
  <article class="chat-message" :class="'message-' + message.role">
    <div class="message-avatar">
      {{ message.role === 'assistant' ? '宜' : '我' }}
    </div>
    <div class="message-content">
      <div class="message-bubble">{{ message.text }}</div>

      <div v-if="message.missingSlots.length" class="missing-slots">
        <span>还想了解：</span>
        <span
          v-for="slot in message.missingSlots"
          :key="slot"
          class="tag"
        >
          {{ slotLabel(slot) }}
        </span>
      </div>

      <div v-if="message.meals.length" class="meal-grid recommendation-grid">
        <MealCard
          v-for="meal in message.meals"
          :key="meal.id"
          :meal="meal"
          mode="recommendation"
          @feedback="forwardFeedback"
        />
      </div>

      <div v-if="message.traceId" class="message-meta">
        <span>本轮决策可追踪</span>
        <RouterLink
          :to="{
            path: '/lab/traces',
            query: { traceId: message.traceId },
          }"
        >
          查看 Trace
        </RouterLink>
      </div>
    </div>
  </article>
</template>