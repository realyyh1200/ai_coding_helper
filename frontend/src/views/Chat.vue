<template>
  <div class="chat-container">
    <aside class="sidebar">
      <!-- 项目文件夹选择区域 -->
      <div class="project-section">
        <div class="section-header">
          <h3>项目目录</h3>
          <button @click="refreshFiles" class="refresh-btn" title="刷新文件列表">↻</button>
        </div>
        <div v-if="!selectedFolder" class="no-folder">
          <button @click="selectProjectFolder" class="select-folder-btn">
            📁 选择项目文件夹
          </button>
        </div>
        <div v-else-if="fileList.length === 0" class="folder-info">
          <div class="folder-path">{{ selectedFolder.name }}</div>
          <button @click="selectProjectFolder" class="rescan-btn">重新选择</button>
        </div>
        <div v-else class="folder-info">
          <div class="folder-path">{{ selectedFolder.name }}</div>
          <button @click="clearFolder" class="clear-folder-btn">清除</button>
        </div>
        
        <!-- 文件列表 -->
        <div v-if="selectedFolder && fileList.length > 0" class="file-list">
          <FileItem
            v-for="file in fileList"
            :key="file.path"
            :file="file"
            :expanded-folders="expandedFolders"
            @toggle="toggleFolder"
          />
        </div>
        <div v-if="selectedFolder && fileList.length === 0" class="empty-folder">
          文件夹为空
        </div>
      </div>

      <!-- 对话列表 -->
      <div class="conversations-section">
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
import FileItem from '../components/FileItem.vue'
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

// 文件夹相关状态
const selectedFolder = ref(null)
const fileList = ref([])
const expandedFolders = ref([])

onMounted(async () => {
  if (!authStore.isAuthenticated) {
    await authStore.fetchUser()
  }
  await loadConversations()
  // 尝试从localStorage恢复之前选择的文件夹名称
  const savedFolder = localStorage.getItem('projectFolder')
  if (savedFolder) {
    try {
      const saved = JSON.parse(savedFolder)
      selectedFolder.value = { name: saved.name }
    } catch (e) {
      console.error('Failed to load saved folder:', e)
    }
  }
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
      '你是一个专业的AI文件处理助手，帮助用户解决文件处理问题。',
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
  localStorage.removeItem('projectFolder')
  router.push('/login')
}

// 文件夹选择相关函数
async function selectProjectFolder() {
  try {
    if (!window.showDirectoryPicker) {
      alert('您的浏览器不支持文件夹选择功能，请使用Chrome浏览器')
      return
    }
    
    const handle = await window.showDirectoryPicker({
      mode: 'read',
      startIn: 'downloads'
    })
    const folderInfo = {
      name: handle.name,
      path: handle.name,
      handle: handle
    }
    selectedFolder.value = folderInfo
    localStorage.setItem('projectFolder', JSON.stringify({ name: handle.name }))
    await loadFileList(handle)
  } catch (error) {
    console.error('Failed to select folder:', error)
    if (error.name === 'AbortError') {
      return
    } else if (error.name === 'NotAllowedError') {
      alert('无法访问文件夹，请确保您已授予访问权限')
    } else {
      alert(`选择文件夹失败: ${error.message || '未知错误'}`)
    }
  }
}

async function loadFileList(handle = selectedFolder.value?.handle) {
  if (!handle) return
  
  fileList.value = []
  expandedFolders.value = []
  
  try {
    for await (const entry of handle.values()) {
      fileList.value.push({
        name: entry.name,
        path: entry.name,
        isFolder: entry.kind === 'directory',
        handle: entry
      })
    }
    fileList.value.sort((a, b) => {
      if (a.isFolder && !b.isFolder) return -1
      if (!a.isFolder && b.isFolder) return 1
      return a.name.localeCompare(b.name)
    })
  } catch (error) {
    console.error('Failed to load files:', error)
  }
}

function refreshFiles() {
  loadFileList()
}

function clearFolder() {
  selectedFolder.value = null
  fileList.value = []
  expandedFolders.value = []
  localStorage.removeItem('projectFolder')
}

function toggleFolder(folderPath) {
  const index = expandedFolders.value.indexOf(folderPath)
  if (index > -1) {
    expandedFolders.value.splice(index, 1)
  } else {
    expandedFolders.value.push(folderPath)
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 320px;
  background: #2c3e50;
  color: white;
  display: flex;
  flex-direction: column;
}

/* 项目文件夹区域 */
.project-section {
  padding: 15px;
  border-bottom: 1px solid #34495e;
  max-height: 250px;
  overflow-y: auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-header h3 {
  font-size: 14px;
  margin: 0;
  color: #bdc3c7;
}

.refresh-btn {
  background: none;
  border: none;
  color: #bdc3c7;
  font-size: 16px;
  cursor: pointer;
  padding: 5px;
}

.refresh-btn:hover {
  color: white;
}

.no-folder {
  text-align: center;
}

.select-folder-btn {
  width: 100%;
  padding: 12px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
}

.select-folder-btn:hover {
  background: #2980b9;
}

.folder-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding: 8px;
  background: #34495e;
  border-radius: 5px;
}

.folder-path {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clear-folder-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  margin-left: 10px;
}

.clear-folder-btn:hover {
  background: #c0392b;
}

.rescan-btn {
  background: #f39c12;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  margin-left: 10px;
}

.rescan-btn:hover {
  background: #e67e22;
}

.file-list {
  margin-top: 10px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  cursor: pointer;
  border-radius: 3px;
  font-size: 13px;
}

.file-item:hover {
  background: #34495e;
}

.file-icon {
  margin-right: 8px;
  font-size: 14px;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.expand-icon {
  font-size: 10px;
  color: #bdc3c7;
}

.sub-files {
  padding-left: 20px;
}

.sub-file {
  padding-left: 10px;
}

.empty-folder {
  text-align: center;
  color: #7f8c8d;
  font-size: 13px;
  padding: 10px;
}

/* 对话列表区域 */
.conversations-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 15px;
  border-bottom: 1px solid #34495e;
}

.sidebar-header h2 {
  font-size: 14px;
  margin: 0 0 10px 0;
  color: #bdc3c7;
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
  font-size: 13px;
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
  padding: 10px;
  margin-bottom: 5px;
  background: #34495e;
  border-radius: 5px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background 0.2s;
  font-size: 13px;
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
  font-size: 16px;
  cursor: pointer;
  padding: 0 5px;
}

.delete-btn:hover {
  color: #c0392b;
}

.sidebar-footer {
  padding: 15px;
  border-top: 1px solid #34495e;
}

.user-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.logout-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
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
  margin: 0;
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