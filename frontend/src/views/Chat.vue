<template>
  <div class="chat-container">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>对话列表</h2>
        <button @click="createNewChat" class="new-chat-btn">+ 新对话</button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          :class="['conversation-item', { active: currentConversation?.id === conv.id }]"
          @click="selectConversation(conv)"
        >
          <span class="conversation-title">{{ conv.title }}</span>
          <button @click.stop="deleteConversation(conv.id)" class="delete-btn">×</button>
        </div>
      </div>
      <div class="sidebar-footer">
        <div class="user-info">
          <span>{{ authStore.user?.username }}</span>
          <button @click="handleLogout" class="logout-btn">退出</button>
        </div>
      </div>
    </aside>

    <main class="chat-main">
      <div class="chat-header">
        <h1>{{ currentConversation?.title || '新对话' }}</h1>
      </div>

      <div class="messages-container" ref="messagesContainer">
        <div
          v-for="(message, index) in currentMessages"
          :key="index"
          :class="['message', message.role]"
        >
          <div class="message-avatar">
            {{ message.role === 'user' ? 'U' : 'AI' }}
          </div>
          <div class="message-content">
            <pre>{{ message.content }}</pre>
          </div>
        </div>
        <div v-if="isLoading" class="message assistant">
          <div class="message-avatar">AI</div>
          <div class="message-content">
            <pre>{{ loadingContent }}</pre>
            <span class="loading-cursor">▋</span>
          </div>
        </div>
      </div>

      <div class="input-container">
        <textarea
          v-model="inputMessage"
          @keydown.enter.exact="handleSend"
          placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
          :disabled="isLoading"
        ></textarea>
        <button @click="handleSend" :disabled="isLoading || !inputMessage.trim()">
          发送
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import {
  fetchConversations,
  createConversation,
  getConversation,
  deleteConversation as apiDeleteConversation,
  streamChat
} from '../api/chat'

const router = useRouter()
const authStore = useAuthStore()

const conversations = ref([])
const currentConversation = ref(null)
const currentMessages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const loadingContent = ref('')
const messagesContainer = ref(null)

onMounted(async () => {
  if (!authStore.isAuthenticated) {
    await authStore.fetchUser()
  }
  await loadConversations()
})

watch(currentMessages, async () => {
  await nextTick()
  scrollToBottom()
}, { deep: true })

async function loadConversations() {
  try {
    conversations.value = await fetchConversations()
    if (conversations.value.length > 0 && !currentConversation.value) {
      await selectConversation(conversations.value[0])
    }
  } catch (error) {
    console.error('Failed to load conversations:', error)
  }
}

async function createNewChat() {
  try {
    const newConv = await createConversation('新对话')
    conversations.value.unshift(newConv)
    await selectConversation(newConv)
  } catch (error) {
    console.error('Failed to create conversation:', error)
  }
}

async function selectConversation(conv) {
  currentConversation.value = conv
  try {
    const fullConv = await getConversation(conv.id)
    currentMessages.value = fullConv.messages.map(m => ({
      role: m.role,
      content: m.content
    }))
  } catch (error) {
    console.error('Failed to load conversation:', error)
  }
}

async function handleSend() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  currentMessages.value.push({
    role: 'user',
    content: message
  })

  isLoading.value = true
  loadingContent.value = ''

  let conversationId = currentConversation.value?.id

  try {
    await streamChat(
      message,
      conversationId,
      '你是一个专业的AI编程助手，帮助用户解决编程问题。',
      (chunk) => {
        loadingContent.value += chunk
      },
      (newConversationId) => {
        if (newConversationId && !conversationId) {
          conversationId = newConversationId
          currentConversation.value.id = newConversationId
          loadConversations()
        }
        currentMessages.value.push({
          role: 'assistant',
          content: loadingContent.value
        })
        loadingContent.value = ''
      },
      (error) => {
        console.error('Chat error:', error)
        loadingContent.value = '抱歉，发生了错误。'
      }
    )
  } catch (error) {
    console.error('Failed to send message:', error)
    loadingContent.value = '抱歉，发生了错误。'
  } finally {
    isLoading.value = false
    if (loadingContent.value) {
      currentMessages.value.push({
        role: 'assistant',
        content: loadingContent.value
      })
      loadingContent.value = ''
    }
  }
}

async function deleteConversation(convId) {
  try {
    await apiDeleteConversation(convId)
    conversations.value = conversations.value.filter(c => c.id !== convId)
    if (currentConversation.value?.id === convId) {
      currentConversation.value = null
      currentMessages.value = []
      if (conversations.value.length > 0) {
        await selectConversation(conversations.value[0])
      }
    }
  } catch (error) {
    console.error('Failed to delete conversation:', error)
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 280px;
  background: #2c3e50;
  color: white;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #34495e;
}

.sidebar-header h2 {
  font-size: 16px;
  margin-bottom: 15px;
}

.new-chat-btn {
  width: 100%;
  padding: 10px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 600;
}

.new-chat-btn:hover {
  background: #2980b9;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.conversation-item {
  padding: 12px;
  margin-bottom: 5px;
  background: #34495e;
  border-radius: 5px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background 0.2s;
}

.conversation-item:hover {
  background: #4a5f7f;
}

.conversation-item.active {
  background: #3498db;
}

.conversation-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  background: none;
  border: none;
  color: #e74c3c;
  font-size: 18px;
  cursor: pointer;
  padding: 0 5px;
}

.delete-btn:hover {
  color: #c0392b;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid #34495e;
}

.user-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logout-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 8px 15px;
  border-radius: 5px;
  cursor: pointer;
}

.logout-btn:hover {
  background: #c0392b;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ecf0f1;
}

.chat-header {
  padding: 20px;
  background: white;
  border-bottom: 1px solid #bdc3c7;
}

.chat-header h1 {
  font-size: 20px;
  color: #2c3e50;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.message {
  display: flex;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #3498db;
  color: white;
  margin-left: 15px;
}

.message.assistant .message-avatar {
  background: #2ecc71;
  color: white;
  margin-right: 15px;
}

.message-content {
  max-width: 70%;
  padding: 15px;
  border-radius: 10px;
  background: white;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.message.user .message-content {
  background: #3498db;
  color: white;
}

.message-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  margin: 0;
}

.loading-cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.input-container {
  padding: 20px;
  background: white;
  border-top: 1px solid #bdc3c7;
  display: flex;
  gap: 10px;
}

.input-container textarea {
  flex: 1;
  padding: 15px;
  border: 1px solid #bdc3c7;
  border-radius: 5px;
  resize: none;
  font-size: 14px;
  font-family: inherit;
}

.input-container textarea:focus {
  outline: none;
  border-color: #3498db;
}

.input-container button {
  padding: 15px 30px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 600;
}

.input-container button:hover:not(:disabled) {
  background: #2980b9;
}

.input-container button:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}
</style>
