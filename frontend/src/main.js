import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './views/Login.vue'
import Register from './views/Register.vue'
import Chat from './views/Chat.vue'
import { useAuthStore } from './store/auth'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/chat', component: Chat, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && authStore.isAuthenticated) {
    next('/chat')
  } else {
    next()
  }
})

app.use(router)
app.mount('#app')
