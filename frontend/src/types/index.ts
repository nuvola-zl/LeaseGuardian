export interface Result<T> {
  code: string
  msg: string
  data: T
  request_id?: string | null
}

export interface LoginData {
  token: string
  user_id: number
  username: string
}

export interface RegisterData {
  message: string
  room_no: string
  monthly_rent: number
  deposit: number
}

export interface MeData {
  user_id: number
  username: string
  room_no: string
  monthly_rent: number
  deposit: number
  start_date: string
  end_date: string
  status: 'ACTIVE' | 'TERMINATING' | 'TERMINATED' | 'EXPIRED'
}

export interface ChatResponse {
  answer: string
  session_id?: string
}

export interface ChatHistoryItem {
  role: 'USER' | 'ASSISTANT'
  content: string
  created_at: string
}

export interface ChatSession {
  session_id: number | string
  title: string
  created_at: string
  updated_at: string
}