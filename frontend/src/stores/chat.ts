import { ref } from 'vue'
import { defineStore } from 'pinia'
import { createSession, sendChat } from '../api/diet'
import type { SourceMode, UiChatMessage } from '../types/diet'

function messageId(): string {
  return 'msg_' + Date.now() + '_' + Math.random().toString(16).slice(2)
}

function welcomeMessage(): UiChatMessage {
  return {
    id: messageId(),
    role: 'assistant',
    text: '告诉我这顿饭的时间、心情、场景或口味，我会帮你找出今天更合适的一餐。',
    sessionId: null,
    traceId: null,
    responseType: null,
    meals: [],
    missingSlots: [],
  }
}

export const useChatStore = defineStore('chat', () => {
  const sourceMode = ref<SourceMode>('PUBLIC')
  const sessionId = ref<string | null>(null)
  const messages = ref<UiChatMessage[]>([welcomeMessage()])
  const sending = ref(false)

  async function newConversation(): Promise<void> {
    const created = await createSession()
    sessionId.value = created.sessionId
    messages.value = [welcomeMessage()]
  }

  async function changeSourceMode(mode: SourceMode): Promise<void> {
    if (sourceMode.value === mode && sessionId.value) return
    sourceMode.value = mode
    await newConversation()
  }

  async function send(text: string): Promise<void> {
    const content = text.trim()
    if (!content || sending.value) return

    if (!sessionId.value) {
      await newConversation()
    }

    messages.value.push({
      id: messageId(),
      role: 'user',
      text: content,
      sessionId: sessionId.value,
      traceId: null,
      responseType: null,
      meals: [],
      missingSlots: [],
    })

    sending.value = true

    try {
      const result = await sendChat({
        sessionId: sessionId.value,
        message: content,
        sourceMode: sourceMode.value,
        context: {},
      })

      sessionId.value = result.sessionId
      messages.value.push({
        id: messageId(),
        role: 'assistant',
        text: result.speechText,
        sessionId: result.sessionId,
        traceId: result.traceId,
        responseType: result.responseType,
        meals: result.displayBlocks || [],
        missingSlots: result.missingSlots || [],
      })
    } finally {
      sending.value = false
    }
  }

  return {
    sourceMode,
    sessionId,
    messages,
    sending,
    newConversation,
    changeSourceMode,
    send,
  }
})