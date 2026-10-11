import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { title: '今日' },
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../views/ChatView.vue'),
      meta: { title: '宜食问答' },
    },
    {
      path: '/meals/personal',
      name: 'personal-meals',
      component: () => import('../views/PersonalMealsView.vue'),
      meta: { title: '我的食单' },
    },
    {
      path: '/meals/public',
      name: 'public-meals',
      component: () => import('../views/PublicMealsView.vue'),
      meta: { title: '灵感食单' },
    },
    {
      path: '/lab/traces',
      name: 'traces',
      component: () => import('../views/TraceView.vue'),
      meta: { title: '决策回放' },
    },
    {
      path: '/lab/evaluations',
      name: 'evaluations',
      component: () => import('../views/EvaluationView.vue'),
      meta: { title: '效果评测' },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
      meta: { title: '页面不存在' },
    },
  ],
})

router.afterEach((to) => {
  document.title = String(to.meta.title) + '｜今日宜食'
})