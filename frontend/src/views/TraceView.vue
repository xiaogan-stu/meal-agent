<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import NoticeBanner from '../components/NoticeBanner.vue'
import {
  getSessionTraces,
  getTrace,
  getTraces,
  updateTraceLabel,
} from '../api/diet'
import type {
  ClarifyAction,
  Intent,
  RequestTrace,
  SlotBundle,
} from '../types/diet'
import {
  daysAgoDateTimeLocal,
  formatDateTime,
  toDateTimeLocal,
} from '../utils/datetime'
import { getErrorMessage, safePrettyJson } from '../utils/error'

const route = useRoute()

const intents: Intent[] = [
  'MEAL_RECOMMENDATION',
  'CLARIFY_NEEDED',
  'MEAL_ADJUST',
  'MEAL_PLAN',
  'HEALTH_RISK',
  'OTHER',
]

const filters = reactive({
  startAt: daysAgoDateTimeLocal(7),
  endAt: toDateTimeLocal(new Date()),
  sessionId: '',
  onlyUnlabeled: false,
  limit: 50,
})

const traces = ref<RequestTrace[]>([])
const selected = ref<RequestTrace | null>(null)
const loading = ref(false)
const saving = ref(false)
const notice = ref('')
const noticeType = ref<'info' | 'success' | 'error'>('info')

const labelForm = reactive({
  expectedIntent: '' as Intent | '',
  expectedClarifyAction: '' as ClarifyAction | '',
  expectedSlots: '',
  labelNote: '',
})

const selectedTraceJson = computed(() =>
  safePrettyJson(selected.value?.traceJson),
)

function fillLabelForm(trace: RequestTrace | null): void {
  labelForm.expectedIntent = trace?.expectedIntent || ''
  labelForm.expectedClarifyAction = trace?.expectedClarifyAction || ''
  labelForm.expectedSlots = safePrettyJson(trace?.expectedSlots)
  labelForm.labelNote = trace?.labelNote || ''
}

function choose(trace: RequestTrace): void {
  selected.value = trace
  fillLabelForm(trace)
}

async function chooseById(traceId: string): Promise<void> {
  loading.value = true
  notice.value = ''
  try {
    const trace = await getTrace(traceId)
    if (!trace) {
      selected.value = null
      noticeType.value = 'info'
      notice.value = '没有找到该 Trace，或它不属于当前用户。'
      return
    }
    selected.value = trace
    fillLabelForm(trace)
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function search(): Promise<void> {
  loading.value = true
  notice.value = ''
  try {
    const session = filters.sessionId.trim()
    traces.value = session
      ? await getSessionTraces(session, filters.limit)
      : await getTraces({
          startAt: filters.startAt,
          endAt: filters.endAt,
          onlyUnlabeled: filters.onlyUnlabeled,
          limit: filters.limit,
        })

    selected.value = traces.value[0] || null
    fillLabelForm(selected.value)
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function saveLabel(): Promise<void> {
  if (!selected.value) return

  let expectedSlots: SlotBundle | null = null
  if (labelForm.expectedSlots.trim()) {
    try {
      expectedSlots = JSON.parse(labelForm.expectedSlots) as SlotBundle
    } catch {
      noticeType.value = 'error'
      notice.value = '预期槽位必须是合法 JSON。'
      return
    }
  }

  saving.value = true
  notice.value = ''
  try {
    await updateTraceLabel(selected.value.traceId, {
      expectedIntent: labelForm.expectedIntent || null,
      expectedClarifyAction: labelForm.expectedClarifyAction || null,
      expectedSlots,
      labelNote: labelForm.labelNote.trim() || null,
    })
    noticeType.value = 'success'
    notice.value = 'Trace 标注已保存。'
    await chooseById(selected.value.traceId)
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const traceId = typeof route.query.traceId === 'string'
    ? route.query.traceId
    : ''

  if (traceId) {
    await chooseById(traceId)
  } else {
    await search()
  }
})
</script>

<template>
  <div class="page-stack lab-page">
    <section class="page-intro lab-intro">
      <div>
        <span class="eyebrow">宜食 Lab · 决策回放</span>
        <h1>看见一次推荐是怎样被做出的</h1>
        <p>按时间或会话查询 Trace，查看完整事件，并补充人工预期标注。</p>
      </div>
      <RouterLink class="button button-soft" to="/lab/evaluations">
        前往效果评测
      </RouterLink>
    </section>

    <NoticeBanner :message="notice" :type="noticeType" />

    <form class="filter-panel" @submit.prevent="search">
      <label class="form-field">
        <span>开始时间</span>
        <input v-model="filters.startAt" type="datetime-local" />
      </label>
      <label class="form-field">
        <span>结束时间</span>
        <input v-model="filters.endAt" type="datetime-local" />
      </label>
      <label class="form-field">
        <span>会话 ID（填写后忽略时间）</span>
        <input v-model="filters.sessionId" type="text" placeholder="sess_..." />
      </label>
      <label class="form-field small-field">
        <span>数量</span>
        <input v-model.number="filters.limit" type="number" min="1" max="1000" />
      </label>
      <label class="check-field">
        <input v-model="filters.onlyUnlabeled" type="checkbox" />
        <span>仅未标注</span>
      </label>
      <button class="button button-lab" type="submit" :disabled="loading">
        {{ loading ? '查询中…' : '查询 Trace' }}
      </button>
    </form>

    <div class="lab-split">
      <section class="table-panel">
        <div v-if="loading" class="empty-state">正在查询决策链路…</div>
        <div v-else-if="traces.length === 0" class="empty-state">
          暂无 Trace。可以先去宜食问答发起几轮对话。
        </div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Trace</th>
                <th>状态</th>
                <th>事件</th>
                <th>耗时</th>
                <th>创建时间</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="trace in traces"
                :key="trace.traceId"
                :class="{ selected: selected?.traceId === trace.traceId }"
                @click="choose(trace)"
              >
                <td>
                  <strong class="mono">{{ trace.traceId }}</strong>
                  <small>{{ trace.sessionId }}</small>
                </td>
                <td><span class="status-chip">{{ trace.status }}</span></td>
                <td>{{ trace.eventCount }}</td>
                <td>{{ trace.durationMs === null ? '-' : trace.durationMs + ' ms' }}</td>
                <td>{{ formatDateTime(trace.createdAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <aside class="trace-detail">
        <div v-if="!selected" class="empty-state">
          选择一条 Trace 查看详情。
        </div>
        <template v-else>
          <div class="section-heading compact">
            <div>
              <span class="eyebrow">Trace 详情</span>
              <h2 class="mono break-text">{{ selected.traceId }}</h2>
            </div>
            <span class="status-chip">{{ selected.status }}</span>
          </div>

          <div class="trace-facts">
            <span>事件 {{ selected.eventCount }}</span>
            <span>耗时 {{ selected.durationMs || 0 }} ms</span>
            <span>{{ formatDateTime(selected.createdAt) }}</span>
          </div>

          <details class="json-details" open>
            <summary>完整 Trace JSON</summary>
            <pre>{{ selectedTraceJson }}</pre>
          </details>

          <form class="label-form" @submit.prevent="saveLabel">
            <h3>人工预期标注</h3>
            <div class="form-grid-two">
              <label class="form-field">
                <span>预期意图</span>
                <select v-model="labelForm.expectedIntent">
                  <option value="">不标注</option>
                  <option v-for="intent in intents" :key="intent" :value="intent">
                    {{ intent }}
                  </option>
                </select>
              </label>
              <label class="form-field">
                <span>预期澄清动作</span>
                <select v-model="labelForm.expectedClarifyAction">
                  <option value="">不标注</option>
                  <option value="ASK">ASK</option>
                  <option value="READY">READY</option>
                </select>
              </label>
            </div>
            <label class="form-field">
              <span>预期槽位 JSON</span>
              <textarea
                v-model="labelForm.expectedSlots"
                rows="10"
                placeholder="填写完整 SlotBundle JSON"
              ></textarea>
            </label>
            <label class="form-field">
              <span>备注</span>
              <textarea v-model="labelForm.labelNote" rows="3"></textarea>
            </label>
            <button class="button button-lab" type="submit" :disabled="saving">
              {{ saving ? '保存中…' : '保存标注' }}
            </button>
          </form>
        </template>
      </aside>
    </div>
  </div>
</template>