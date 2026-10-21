import { createRouter, createWebHistory } from 'vue-router'

import SearchView from '@/views/SearchView.vue'

// The entity and alert pages load Cytoscape, so they are separate chunks.
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'search', component: SearchView },
    {
      path: '/entities/:id',
      name: 'entity',
      component: () => import('@/views/EntityView.vue'),
      props: true,
    },
    { path: '/alerts', name: 'alerts', component: () => import('@/views/AlertsView.vue') },
    {
      path: '/alerts/:id',
      name: 'alert',
      component: () => import('@/views/AlertView.vue'),
      props: true,
    },
    { path: '/sources', name: 'sources', component: () => import('@/views/DataSourcesView.vue') },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

export default router
