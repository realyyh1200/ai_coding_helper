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

export async function fetchConversations() {
  const headers = await getAuthHeaders()
  const response = await axios.get(`${API_BASE_URL}/chat/conversations`, { headers })
  return response.data
}

export async function createConversation(title) {
  const headers = await getAuthHeaders()
  const response = await axios.post(`${API_BASE_URL}/chat/conversations`, { title }, { headers })
  return response.data
}

export async function getConversation(conversationId) {
  const headers = await getAuthHeaders()
  const response = await axios.get(`${API_BASE_URL}/chat/conversations/${conversationId}`, { headers })
  return response.data
}

export async function updateConversation(conversationId, data) {
  const headers = await getAuthHeaders()
  const response = await axios.patch(`${API_BASE_URL}/chat/conversations/${conversationId}`, data, { headers })
  return response.data
}

export async function deleteConversation(conversationId) {
  const headers = await getAuthHeaders()
  await axios.delete(`${API_BASE_URL}/chat/conversations/${conversationId}`, { headers })
}

export async function streamChat(message, conversationId, systemPrompt, onChunk, onDone, onError) {
  const headers = await getAuthHeaders()

  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      system_prompt: systemPrompt
    })
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value, { stream: true })
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (data.error) {
            onError(data.error)
          } else if (data.done) {
            onDone(data.conversation_id)
          } else {
            onChunk(data.content)
          }
        } catch (e) {
          console.error('Failed to parse SSE data:', e)
        }
      }
    }
  }
}
