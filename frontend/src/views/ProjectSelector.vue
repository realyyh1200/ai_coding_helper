<template>
  <div class="project-selector">
    <div class="container">
      <div class="header">
        <h1>选择项目目录</h1>
        <p>请选择您的项目所在文件夹，以便AI助手更好地理解您的文件结构</p>
      </div>

      <div class="folder-display">
        <div v-if="selectedFolder" class="selected-folder">
          <div class="folder-icon">📂</div>
          <div class="folder-info">
            <div class="folder-name">{{ selectedFolder.name }}</div>
            <div class="folder-path">{{ selectedFolder.path }}</div>
          </div>
          <button class="btn-clear" @click="clearSelection">✕</button>
        </div>
        <div v-else class="no-selection">
          <div class="empty-icon">📁</div>
          <div class="empty-text">未选择文件夹</div>
        </div>
      </div>

      <div class="actions">
        <button class="btn-select" @click="selectFolder">
          <span class="btn-icon">📂</span>
          <span>选择文件夹</span>
        </button>

        <div v-if="selectedFolder" class="btn-group">
          <button class="btn-skip" @click="skipSelection">
            <span>跳过此步骤</span>
          </button>
          <button class="btn-confirm" @click="confirmSelection">
            <span class="btn-icon">✓</span>
            <span>确认选择</span>
          </button>
        </div>
      </div>

      <div v-if="files.length > 0" class="file-list">
        <h3>📋 目录内容预览</h3>
        <div class="files-container">
          <div v-for="file in files" :key="file.path" class="file-item">
            <span class="file-icon">{{ getFileIcon(file) }}</span>
            <span class="file-name">{{ file.name }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const selectedFolder = ref(null)
const files = ref([])

const selectFolder = async () => {
  try {
    const handle = await window.showDirectoryPicker({
      mode: 'read'
    })

    selectedFolder.value = {
      name: handle.name,
      path: handle.name
    }

    await loadFiles(handle)
  } catch (error) {
    console.log('用户取消选择')
  }
}

const loadFiles = async (handle, path = '') => {
  files.value = []

  for await (const entry of handle.values()) {
    const fullPath = path ? `${path}/${entry.name}` : entry.name

    if (entry.kind === 'file') {
      files.value.push({
        name: entry.name,
        path: fullPath,
        kind: 'file'
      })
    } else if (entry.kind === 'directory') {
      files.value.push({
        name: entry.name + '/',
        path: fullPath + '/',
        kind: 'directory'
      })
    }
  }

  files.value.sort((a, b) => {
    if (a.kind !== b.kind) {
      return a.kind === 'directory' ? -1 : 1
    }
    return a.name.localeCompare(b.name)
  })
}

const getFileIcon = (file) => {
  if (file.kind === 'directory') return '📁'

  const ext = file.name.split('.').pop().toLowerCase()
  const icons = {
    js: '📄',
    ts: '📘',
    py: '🐍',
    json: '📋',
    html: '🌐',
    css: '🎨',
    vue: '💚',
    md: '📝',
    gitignore: '🔒'
  }

  return icons[ext] || '📄'
}

const clearSelection = () => {
  selectedFolder.value = null
  files.value = []
}

const skipSelection = () => {
  localStorage.setItem('projectFolder', JSON.stringify({ skipped: true }))
  router.push('/chat')
}

const confirmSelection = () => {
  if (selectedFolder.value) {
    localStorage.setItem('projectFolder', JSON.stringify(selectedFolder.value))
  }
  router.push('/chat')
}
</script>

<style scoped>
.project-selector {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.container {
  background: white;
  border-radius: 20px;
  padding: 40px;
  max-width: 600px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 10px;
}

.header p {
  color: #666;
  font-size: 14px;
}

.folder-display {
  margin-bottom: 30px;
}

.selected-folder {
  display: flex;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border-radius: 12px;
  border: 2px solid #4caf50;
}

.folder-icon {
  font-size: 40px;
  margin-right: 15px;
}

.folder-info {
  flex: 1;
}

.folder-name {
  font-size: 18px;
  font-weight: bold;
  color: #2e7d32;
  margin-bottom: 5px;
}

.folder-path {
  font-size: 12px;
  color: #666;
  word-break: break-all;
}

.btn-clear {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
  padding: 5px 10px;
  border-radius: 50%;
  transition: all 0.2s;
}

.btn-clear:hover {
  background: rgba(0, 0, 0, 0.1);
  color: #666;
}

.no-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  background: #f5f5f5;
  border-radius: 12px;
  border: 2px dashed #ddd;
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 15px;
}

.empty-text {
  color: #999;
  font-size: 14px;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 30px;
}

.btn-select, .btn-confirm, .btn-skip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 15px 30px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-icon {
  font-size: 18px;
}

.btn-select {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-select:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
}

.btn-group {
  display: flex;
  gap: 15px;
}

.btn-skip {
  flex: 1;
  background: #f0f0f0;
  color: #666;
}

.btn-skip:hover {
  background: #e0e0e0;
}

.btn-confirm {
  flex: 2;
  background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%);
  color: white;
}

.btn-confirm:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(76, 175, 80, 0.4);
}

.file-list {
  background: #fafafa;
  border-radius: 12px;
  padding: 20px;
}

.file-list h3 {
  margin-bottom: 15px;
  color: #333;
  font-size: 16px;
}

.files-container {
  max-height: 300px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background 0.2s;
}

.file-item:hover {
  background: #eee;
}

.file-icon {
  font-size: 16px;
}

.file-name {
  font-size: 14px;
  color: #333;
  flex: 1;
}
</style>
