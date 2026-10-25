import { java, unwrapResult } from './http'
import type { ChatHistoryItem, ChatSession } from '@/types'

export type Scene = 'REPAIR' | 'CHECKOUT'

export function fetchChatSessions(scene: Scene) {
  return unwrapResult<ChatSession[]>(
      java.get('/chat/sessions', { params: { scene } }),
  )
}

export function fetchChatHistory(sessionId: string | number) {
  return unwrapResult<ChatHistoryItem[]>(
      java.get(`/chat/sessions/${sessionId}/messages`),
  )
}