<template>
  <div>
    <!-- 当前文件/文件夹 -->
    <div
      :class="['file-item', { 'is-folder': file.isFolder }]"
      @click="handleClick"
      :draggable="!file.isFolder"
      @dragstart="handleDragStart"
      @dragend="handleDragEnd"
    >
      <span class="file-icon">{{ file.isFolder ? '📂' : '📄' }}</span>
      <span class="file-name">{{ file.name }}</span>
      <span v-if="file.isFolder" class="expand-icon">
        {{ isExpanded ? '▼' : '▶' }}
      </span>
    </div>
    
    <!-- 如果是文件夹且已展开，递归显示子文件 -->
    <div v-if="file.isFolder && isExpanded" class="sub-files">
      <FileItem
        v-for="subFile in subFiles"
        :key="subFile.path"
        :file="subFile"
        :expanded-folders="expandedFolders"
        @toggle="(path) => $emit('toggle', path)"
        @loaded="(sub) => $emit('loaded', sub)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'

const props = defineProps({
  file: {
    type: Object,
    required: true
  },
  expandedFolders: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['toggle', 'loaded', 'dragstart', 'dragend'])

const subFiles = ref([])

const isExpanded = computed(() => {
  return props.expandedFolders.includes(props.file.path)
})

async function loadSubFiles() {
  if (!props.file.handle) return
  
  try {
    const files = []
    for await (const entry of props.file.handle.values()) {
      const fullPath = `${props.file.path}/${entry.name}`
      files.push({
        name: entry.name,
        path: fullPath,
        isFolder: entry.kind === 'directory',
        handle: entry,
        parentPath: props.file.path
      })
    }
    files.sort((a, b) => {
      if (a.isFolder && !b.isFolder) return -1
      if (!a.isFolder && b.isFolder) return 1
      return a.name.localeCompare(b.name)
    })
    subFiles.value = files
    
    // 通知父组件，子文件已加载，可以添加到全局列表
    emit('loaded', files)
  } catch (error) {
    console.error('Failed to load subfiles:', error)
  }
}

function handleClick() {
  if (props.file.isFolder) {
    const wasExpanded = isExpanded.value
    emit('toggle', props.file.path)
    // 如果现在是展开状态且子文件为空，加载子文件
    const nowExpanded = !wasExpanded
    if (nowExpanded && subFiles.value.length === 0) {
      loadSubFiles()
    }
  }
}

function handleDragStart(e) {
  if (props.file.isFolder) return
  
  e.dataTransfer.setData('text/plain', props.file.path)
  e.dataTransfer.effectAllowed = 'copy'
  emit('dragstart', e)
}

function handleDragEnd(e) {
  emit('dragend', e)
}

// 如果文件夹已展开，初始化时加载子文件
onMounted(() => {
  if (isExpanded.value && props.file.isFolder) {
    loadSubFiles()
  }
})
</script>

<style scoped>
.file-item {
  display: flex;
  align-items: center;
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 3px;
  font-size: 13px;
}

.file-item:hover {
  background: #34495e;
}

.file-icon {
  margin-right: 6px;
  font-size: 12px;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.expand-icon {
  font-size: 10px;  /* 略小于文件名的13px */
  color: #95a5a6;
  margin-left: 4px;
}

.sub-files {
  padding-left: 16px;  /* 子文件夹缩进 */
}
</style>