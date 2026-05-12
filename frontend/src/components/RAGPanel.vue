<template>
  <div class="rag-panel" :class="{ 'rag-panel-expanded': isExpanded }">
    <div class="rag-panel-header" @click="toggleExpand">
      <h3>📚 自定义RAG库</h3>
      <span class="expand-icon">{{ isExpanded ? '▼' : '▲' }}</span>
    </div>

    <div v-if="isExpanded" class="rag-panel-content">
      <!-- 拖拽区域 -->
      <div
        class="rag-drop-zone"
        :class="{ 'drag-over': isDragOver }"
        @dragover.prevent="onDragOver"
        @dragleave="onDragLeave"
        @drop.prevent="onDrop"
      >
        <div v-if="isDragOver" class="drop-indicator">
          📁 释放以添加到RAG库
        </div>
        <div v-else class="drop-hint">
          <p>将文件或文件夹拖放到此处</p>
          <p class="hint-text">支持: .txt, .md, .py, .js, .json 等文本文件</p>
        </div>
      </div>

      <!-- 文件列表 -->
      <div v-if="ragFiles.length > 0" class="rag-files-list">
        <div class="list-header">
          <span>已添加文件 ({{ ragFiles.length }})</span>
          <button @click="refreshFiles" class="refresh-btn">↻</button>
        </div>
        <div
          v-for="file in ragFiles"
          :key="file.id"
          class="rag-file-item"
        >
          <span class="file-name">{{ file.file_name }}</span>
          <button @click="removeFile(file.id)" class="remove-btn">×</button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <p>暂无文件</p>
        <p class="hint-text">拖拽文件到上方区域添加</p>
      </div>

      <!-- 处理状态 -->
      <div v-if="isProcessing" class="processing-status">
        <span class="loading-spinner">⏳</span>
        <span>{{ processingMessage }}</span>
      </div>

      <!-- 处理结果 -->
      <div v-if="processResult" class="process-result" :class="processResult.success ? 'success' : 'error'">
        <p>{{ processResult.message }}</p>
        <p v-if="processResult.success">
          文件数: {{ processResult.total_files }} | Chunks: {{ processResult.stored_chunks }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { processFilesForRAG, getRAGFiles, deleteRAGFile, readLocalFile } from '../api/rag'
import { getDragFileHandle } from '../store/dragStore'

const isExpanded = ref(true)
const isDragOver = ref(false)
const ragFiles = ref([])
const isProcessing = ref(false)
const processingMessage = ref('')
const processResult = ref(null)

const TEXT_EXTENSIONS = [
  '.txt', '.md', '.py', '.js', '.json', '.xml', '.html', '.css', '.ts',
  '.java', '.cpp', '.c', '.go', '.rs', '.yml', '.yaml', '.toml', '.sql',
  '.log', '.csv'
]

onMounted(() => {
  loadRAGFiles()
})

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

async function loadRAGFiles() {
  try {
    ragFiles.value = await getRAGFiles()
  } catch (error) {
    console.error('Failed to load RAG files:', error)
  }
}

function refreshFiles() {
  loadRAGFiles()
}

function onDragOver(e) {
  isDragOver.value = true
}

function onDragLeave(e) {
  isDragOver.value = false
}

function isTextFilePath(path) {
  const lower = path.toLowerCase()
  return TEXT_EXTENSIONS.some(ext => lower.endsWith(ext))
}

async function onDrop(e) {
  isDragOver.value = false

  const standardFiles = e.dataTransfer.files
  let fileContents = []

  if (standardFiles.length > 0) {
    for (const file of standardFiles) {
      try {
        const content = await file.text()
        fileContents.push({
          name: file.name,
          content: content,
          size: file.size
        })
      } catch (err) {
        console.error('Cannot read file:', err)
      }
    }
  }

  if (fileContents.length === 0) {
    const dragHandle = getDragFileHandle()
    if (dragHandle && dragHandle.handle) {
      try {
        const file = await dragHandle.handle.getFile()
        const content = await file.text()
        fileContents.push({
          name: dragHandle.name,
          content: content,
          size: file.size
        })
      } catch (err) {
        console.error('Cannot read file via handle:', err)
      }
    }
  }

  if (fileContents.length === 0) {
    const textData = e.dataTransfer.getData('text/plain')
    if (textData && isTextFilePath(textData)) {
      try {
        const result = await readLocalFile(textData)
        if (result.success) {
          fileContents.push({
            name: result.name,
            content: result.content,
            size: result.size
          })
        }
      } catch (err) {
        console.error('Cannot read file via API:', err)
      }
    }
  }

  if (fileContents.length === 0) {
    for (const item of e.dataTransfer.items) {
      if (item.kind === 'file') {
        const file = item.getAsFile()
        if (file) {
          try {
            const content = await file.text()
            fileContents.push({
              name: file.name,
              content: content,
              size: file.size
            })
          } catch (err) {
            console.error('Cannot read file:', err)
          }
        }
      }
    }
  }

  if (fileContents.length === 0) {
    processResult.value = {
      success: false,
      message: '未检测到有效文件，请从项目目录拖拽文件或从文件夹直接拖放文件'
    }
    return
  }

  isProcessing.value = true
  processingMessage.value = '正在处理文件...'
  processResult.value = null

  try {
    const result = await processFilesForRAG(fileContents)
    processResult.value = result

    if (result.success) {
      await loadRAGFiles()
    }
  } catch (error) {
    processResult.value = {
      success: false,
      message: error.response?.data?.detail || '处理失败: ' + error.message
    }
  } finally {
    isProcessing.value = false
    processingMessage.value = ''
  }
}

async function removeFile(fileId) {
  try {
    await deleteRAGFile(fileId)
    ragFiles.value = ragFiles.value.filter(f => f.id !== fileId)
  } catch (error) {
    console.error('Failed to remove file:', error)
    alert('删除失败: ' + error.message)
  }
}
</script>

<style scoped>
.rag-panel {
  background: #34495e;
  border-left: 1px solid #2c3e50;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
}

.rag-panel-expanded {
  width: 320px;
}

.rag-panel-header {
  padding: 15px;
  background: #2c3e50;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #2c3e50;
}

.rag-panel-header h3 {
  margin: 0;
  font-size: 14px;
  color: white;
}

.expand-icon {
  color: #95a5a6;
  font-size: 12px;
}

.rag-panel-content {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
}

.rag-drop-zone {
  border: 2px dashed #95a5a6;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  margin-bottom: 15px;
  transition: all 0.3s;
}

.rag-drop-zone.drag-over {
  border-color: #3498db;
  background: rgba(52, 152, 219, 0.1);
}

.drop-hint {
  color: #bdc3c7;
}

.drop-hint p {
  margin: 5px 0;
  font-size: 13px;
}

.hint-text {
  font-size: 11px !important;
  color: #7f8c8d !important;
}

.drop-indicator {
  color: #3498db;
  font-size: 14px;
  font-weight: bold;
}

.rag-files-list {
  margin-bottom: 15px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  color: #bdc3c7;
  font-size: 12px;
}

.refresh-btn {
  background: none;
  border: none;
  color: #95a5a6;
  cursor: pointer;
  font-size: 14px;
}

.rag-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: #2c3e50;
  border-radius: 4px;
  margin-bottom: 5px;
}

.file-name {
  color: #ecf0f1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-btn {
  background: #e74c3c;
  border: none;
  color: white;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  text-align: center;
  color: #7f8c8d;
}

.empty-state p {
  margin: 5px 0;
}

.processing-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 10px;
  background: rgba(52, 152, 219, 0.1);
  border-radius: 4px;
  color: #3498db;
  font-size: 13px;
  margin-bottom: 10px;
}

.loading-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.process-result {
  padding: 10px;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 10px;
}

.process-result.success {
  background: rgba(39, 174, 96, 0.1);
  color: #27ae60;
}

.process-result.error {
  background: rgba(231, 76, 60, 0.1);
  color: #e74c3c;
}

.process-result p {
  margin: 5px 0;
}
</style>