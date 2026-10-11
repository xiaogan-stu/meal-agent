<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import ChatMessage from '../components/ChatMessage.vue'
import NoticeBanner from '../components/NoticeBanner.vue'
import { saveFeedback } from '../api/diet'
import { useAppStore } from '../stores/app'
import { useChatStore } from '../stores/chat'
import type { MealResponse, SourceMode } from '../types/diet'
import { getErrorMessage } from '../utils/error'

const appStore = useAppStore()
const chatStore = useChatStore()
const { userId } = storeToRefs(appStore)
const { messages, sourceMode, sessionId, sending } = storeToRefs(chatStore)

const input = ref('')
const notice = ref('')
const noticeType = ref<'info' | 'success' | 'error'>('info')
const messagesElement = ref<HTMLElement | null>(null)

const quickPrompts = [
  '晚饭想吃清淡一点，最好快一些',
  '今天有点累，想吃热乎的',
  '运动后想吃高蛋白的午餐',
  '换一批，不想吃刚才那些',
]

async function startConversation(): Promise<void> {
  notice.value = ''
  try {
    await chatStore.newConversation()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  }
}

async function changeMode(mode: SourceMode): Promise<void> {
  notice.value = ''
  try {
    await chatStore.changeSourceMode(mode)
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  }
}

async function submit(): Promise<void> {
  const text = input.value.trim()
  if (!text || sending.value) return
  input.value = ''
  notice.value = ''

  try {
    await chatStore.send(text)
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  }
}

function usePrompt(prompt: string): void {
  input.value = prompt
}

async function feedback(
  meal: MealResponse,
  action: 'LIKE' | 'ADOPT' | 'DISLIKE',
): Promise<void> {
  if (!sessionId.value) return
  try {
    await saveFeedback({
      sessionId: sessionId.value,
      itemId: meal.id,
      action,
      rating: action === 'DISLIKE' ? 2 : 5,
      reason: '',
    })
    noticeType.value = 'success'
    notice.value = '已记录你对“' + meal.name + '”的反馈。'
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  }
}

onMounted(async () => {
  if (!sessionId.value) await startConversation()
})

watch(userId, async () => {
  await startConversation()
})

watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    messagesElement.value?.scrollTo({
      top: messagesElement.value.scrollHeight,
      behavior: 'smooth',
    })
  },
)
</script>

<template>
  <div class="page-stack">
    <section class="chat-toolbar">
      <div>
        <span class="eyebrow">宜食问答</span>
        <h1>告诉我此刻的状态</h1>
        <p class="muted session-text">会话：{{ sessionId || '创建中…' }}</p>
      </div>
      <div class="toolbar-actions">
        <div class="segmented-control">
          <button
            type="button"
            :class="{ active: sourceMode === 'PUBLIC' }"
            @click="changeMode('PUBLIC')"
          >
            灵感食单
          </button>
          <button
            type="button"
            :class="{ active: sourceMode === 'PERSONAL' }"
            @click="changeMode('PERSONAL')"
          >
            我的食单
          </button>
        </div>
        <button class="button button-ghost" type="button" @click="startConversation">
          新对话
        </button>
      </div>
    </section>

    <NoticeBanner :message="notice" :type="noticeType" />

    <div class="chat-layout">
      <section class="chat-panel">
        <div ref="messagesElement" class="message-list">
          <ChatMessage
            v-for="message in messages"
            :key="message.id"
            :message="message"
            @feedback="feedback"
          />
          <div v-if="sending" class="thinking-row">
            <span></span><span></span><span></span>
            正在理解并筛选这一餐…
          </div>
        </div>

        <form class="chat-composer" @submit.prevent="submit">
          <textarea
            v-model="input"
            rows="3"
            placeholder="例如：今晚加班，想吃点热乎又清淡的"
            @keydown.ctrl.enter="submit"
          ></textarea>
          <div class="composer-bottom">
            <span>Ctrl + Enter 发送</span>
            <button
              class="button button-primary"
              type="submit"
              :disabled="sending || !input.trim()"
            >
              {{ sending ? '等待回复…' : '发送' }}
            </button>
          </div>
        </form>
      </section>

      <aside class="chat-aside">
        <div class="aside-card">
          <span class="eyebrow">不知道怎么说？</span>
          <h2>试试这些表达</h2>
          <button
            v-for="prompt in quickPrompts"
            :key="prompt"
            class="prompt-button"
            type="button"
            @click="usePrompt(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
        <div class="aside-card quiet">
          <h3>数据源说明</h3>
          <p>
            灵感食单来自公共餐食库；我的食单只使用当前用户维护的餐食。
            切换数据源会自动创建新会话。
          </p>
        </div>
      </aside>
    </div>
  </div>
</template>