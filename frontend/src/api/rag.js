import axios from 'axios'
import { useAuthStore } from '../store/auth'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function getAuthHeaders() {
  const authStore = useAuthStore()
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authStore.accessToken}`
  }
}

export async function processFilesForRAG(files) {
  const headers = await getAuthHeaders()
  const response = await axios.post(`${API_BASE_URL}/rag/upload`, { files }, { headers })
  return response.data
}

export async function readLocalFile(filePath) {
  const headers = await getAuthHeaders()
  const response = await axios.post(`${API_BASE_URL}/rag/read-file`, {}, {
    headers,
    params: { file_path: filePath }
  })
  return response.data
}

export async function getRAGFiles() {
  const headers = await getAuthHeaders()
  const response = await axios.get(`${API_BASE_URL}/rag/files`, { headers })
  return response.data
}

export async function deleteRAGFile(fileId) {
  const headers = await getAuthHeaders()
  const response = await axios.delete(`${API_BASE_URL}/rag/files/${fileId}`, { headers })
  return response.data
}

export async function retrieveDocuments(query, topK = 5) {
  const headers = await getAuthHeaders()
  const response = await axios.post(
    `${API_BASE_URL}/rag/retrieve`,
    {},
    {
      headers,
      params: { query, top_k: topK }
    }
  )
  return response.data
}