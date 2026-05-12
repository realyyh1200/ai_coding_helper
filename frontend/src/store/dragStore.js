import { ref } from 'vue'

const currentDragFileHandle = ref(null)

export function setDragFileHandle(handle) {
  currentDragFileHandle.value = handle
}

export function getDragFileHandle() {
  return currentDragFileHandle.value
}

export function clearDragFileHandle() {
  currentDragFileHandle.value = null
}