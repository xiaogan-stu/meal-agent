<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import NoticeBanner from '../components/NoticeBanner.vue'
import { runEvaluation } from '../api/diet'
import type { EvaluationReport } from '../types/diet'
import {
  daysAgoDateTimeLocal,
  formatDateTime,
  toDateTimeLocal,
} from '../utils/datetime'
import { getErrorMessage, safePrettyJson } from '../utils/error'

const form = reactive({
  startAt: daysAgoDateTimeLocal(7),
  endAt: toDateTimeLocal(new Date()),
  includeLlmJudge: false,
  limit: 100,
})

const report = ref<EvaluationReport | null>(null)
const loading = ref(false)
const notice = ref('')
const noticeType = ref<'info' | 'success' | 'error'>('info')

const metricEntries = computed(() =>
  Object.entries(report.value?.metricAverages || {}),
)

function score(value: number | null): string {
  return value === null ? '-' : value.toFixed(2)
}

async function evaluate(): Promise<void> {
  loading.value = true
  notice.value = ''
  try {
    report.value = await runEvaluation({
      startAt: form.startAt,
      endAt: form.endAt,
      includeLlmJudge: form.includeLlmJudge,
      limit: form.limit,
    })
    noticeType.value = 'success'
    notice.value = '评测报告已生成。'
  } catch (error) {
    noticeType.value = 'error'
    notice.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-stack lab-page">
    <section class="page-intro lab-intro">
      <div>
        <span class="eyebrow">宜食 Lab · 效果评测</span>
        <h1>让每次反馈进入下一轮优化</h1>
        <p>组合查看规则指标、人工标注、用户反馈和可选 LLM Judge。</p>
      </div>
      <RouterLink class="button button-soft" to="/lab/traces">
        返回决策回放
      </RouterLink>
    </section>

    <NoticeBanner :message="notice" :type="noticeType" />

    <form class="filter-panel evaluation-filter" @submit.prevent="evaluate">
      <label class="form-field">
        <span>开始时间</span>
        <input v-model="form.startAt" type="datetime-local" required />
      </label>
      <label class="form-field">
        <span>结束时间</span>
        <input v-model="form.endAt" type="datetime-local" required />
      </label>
      <label class="form-field small-field">
        <span>数量</span>
        <input v-model.number="form.limit" type="number" min="1" max="1000" />
      </label>
      <label class="check-field">
        <input v-model="form.includeLlmJudge" type="checkbox" />
        <span>启用 LLM Judge（增加耗时与费用）</span>
      </label>
      <button class="button button-lab" type="submit" :disabled="loading">
        {{ loading ? '评测中…' : '生成评测报告' }}
      </button>
    </form>

    <div v-if="!report" class="empty-state">
      选择时间范围后生成第一份报告。
    </div>

    <template v-else>
      <section class="stats-grid">
        <article class="stat-card">
          <span>Trace 总数</span>
          <strong>{{ report.totalTraces }}</strong>
          <p>本次纳入评测的请求数</p>
        </article>
        <article class="stat-card">
          <span>已标注</span>
          <strong>{{ report.labeledTraces }}</strong>
          <p>具备人工预期的 Trace</p>
        </article>
        <article class="stat-card lab-accent">
          <span>平均得分</span>
          <strong>{{ score(report.avgScore) }}</strong>
          <p>按当前可用权重归一化</p>
        </article>
      </section>

      <section class="content-section">
        <div class="section-heading">
          <div>
            <span class="eyebrow">指标均值</span>
            <h2>本次评测概览</h2>
          </div>
          <p class="muted">
            {{ formatDateTime(report.startAt) }} 至
            {{ formatDateTime(report.endAt) }}
          </p>
        </div>
        <div class="metric-grid">
          <article
            v-for="[name, value] in metricEntries"
            :key="name"
            class="metric-card"
          >
            <span>{{ name }}</span>
            <strong>{{ Number(value).toFixed(2) }}</strong>
          </article>
        </div>
      </section>

      <section class="table-panel">
        <div class="section-heading compact">
          <div>
            <span class="eyebrow">Trace 明细</span>
            <h2>逐条结果</h2>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Trace / 会话</th>
                <th>综合分</th>
                <th>规则分</th>
                <th>Judge</th>
                <th>反馈分</th>
                <th>详情</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in report.traceResults" :key="row.traceId">
                <td>
                  <strong class="mono">{{ row.traceId }}</strong>
                  <small>{{ row.sessionId }}</small>
                </td>
                <td>{{ score(row.score) }}</td>
                <td>{{ score(row.ruleScore) }}</td>
                <td>{{ score(row.llmJudgeScore) }}</td>
                <td>{{ score(row.userFeedbackScore) }}</td>
                <td>
                  <details class="json-details table-json">
                    <summary>查看 JSON</summary>
                    <pre>{{ safePrettyJson({
                      metrics: row.metrics,
                      detail: row.detail,
                    }) }}</pre>
                  </details>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>