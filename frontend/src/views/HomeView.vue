<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getPersonalMeals, getPublicMeals } from '../api/diet'
import NoticeBanner from '../components/NoticeBanner.vue'
import { formatToday } from '../utils/datetime'
import { getErrorMessage } from '../utils/error'

const personalCount = ref(0)
const publicCount = ref(0)
const loading = ref(true)
const errorMessage = ref('')

onMounted(async () => {
  try {
    const [personal, publicMeals] = await Promise.all([
      getPersonalMeals(),
      getPublicMeals(),
    ])
    personalCount.value = personal.length
    publicCount.value = publicMeals.length
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-stack">
    <NoticeBanner :message="errorMessage" type="error" />

    <section class="hero-section">
      <div class="hero-copy">
        <div class="today-label">
          <span class="today-dot"></span>
          {{ formatToday() }}
        </div>
        <p class="eyebrow">今日宜 · 好好吃饭</p>
        <h1>今天，宜吃什么？</h1>
        <p class="hero-description">
          告诉我此刻的时间、心情、场景和饮食偏好，今日宜食会从真实餐食库中，
          整理出更适合这一餐的选择。
        </p>
        <div class="hero-actions">
          <RouterLink class="button button-primary button-large" to="/chat">
            看看今日宜食
          </RouterLink>
          <RouterLink class="button button-soft button-large" to="/meals/personal">
            管理我的食单
          </RouterLink>
        </div>
      </div>

      <div class="today-card">
        <div class="today-card-top">
          <span>今日宜食签</span>
          <strong>宜</strong>
        </div>
        <h2>晚餐 · 加班后</h2>
        <p>想吃热乎的，也希望清淡、少排队。</p>
        <div class="decision-steps">
          <div class="decision-step done"><span>1</span>理解此刻状态</div>
          <div class="decision-step done"><span>2</span>筛选真实餐食</div>
          <div class="decision-step active"><span>3</span>生成匹配理由</div>
        </div>
        <div class="today-result">
          <span>今日宜 · 暖胃 · 清淡</span>
          <strong>番茄鸡蛋面</strong>
        </div>
      </div>
    </section>

    <section class="stats-grid">
      <article class="stat-card">
        <span>我的食单</span>
        <strong>{{ loading ? '—' : personalCount }}</strong>
        <p>属于当前调试用户的个人餐食</p>
      </article>
      <article class="stat-card">
        <span>灵感食单</span>
        <strong>{{ loading ? '—' : publicCount }}</strong>
        <p>可用于公共模式推荐的真实候选</p>
      </article>
      <article class="stat-card accent">
        <span>感知维度</span>
        <strong>7</strong>
        <p>餐次、心情、场景、健康目标等</p>
      </article>
    </section>

    <section class="content-section">
      <div class="section-heading">
        <div>
          <span class="eyebrow">不只回答“吃什么”</span>
          <h2>把模糊想法变成一次可信的选择</h2>
        </div>
      </div>
      <div class="feature-grid">
        <article class="feature-card">
          <span class="feature-index">01</span>
          <h3>说不清也没关系</h3>
          <p>信息不足时自然追问，逐轮补全这一餐真正重要的条件。</p>
        </article>
        <article class="feature-card">
          <span class="feature-index">02</span>
          <h3>每个选择都有来源</h3>
          <p>候选来自个人或公共餐食库，不让模型凭空创造不存在的菜。</p>
        </article>
        <article class="feature-card">
          <span class="feature-index">03</span>
          <h3>不合适就换一批</h3>
          <p>保留本轮情境与历史结果，继续筛选而不是从头开始。</p>
        </article>
      </div>
    </section>
  </div>
</template>