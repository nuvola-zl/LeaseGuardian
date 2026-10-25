import { java, unwrapResult } from './http'
import type { LoginData, MeData, RegisterData } from '@/types'

export function login(username: string, password: string) {
  return unwrapResult<LoginData>(java.post('/auth/login', { username, password }))
}

export function register(username: string, password: string, room_no: string) {
  return unwrapResult<RegisterData>(java.post('/auth/register', { username, password, room_no }))
}

export function me() {
  return unwrapResult<MeData>(java.get('/auth/me'))
}