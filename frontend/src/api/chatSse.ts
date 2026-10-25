import { LOGIN_EXPIRED } from './http'
import type { Scene } from './chat'

export type Persona = 'SWEET' | 'SASSY' | 'NORTHEAST'

export interface DoneEvent {
    session_id?: string
    answer: string
}

interface StreamChatOptions {
    message: string
    scene?: Scene
    sessionId?: string | null
    persona?: Persona
    signal?: AbortSignal
    onStatus: (step: string) => void
    onToken: (text: string) => void
    onDone: (done: DoneEvent) => void
}

async function readSseStream(
    res: Response,
    handlers: Pick<StreamChatOptions, 'onStatus' | 'onToken' | 'onDone'>,
): Promise<DoneEvent> {
    if (!res.body) throw new Error('当前浏览器不支持流式读取')

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let gotDone = false

    while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() ?? ''

        for (const block of blocks) {
            const lines = block.split(/\r?\n/)
            let event = ''
            const dataLines: string[] = []

            for (const line of lines) {
                if (!line || line.startsWith(':')) continue
                if (line.startsWith('event:')) {
                    event = line.slice(6).trim()
                } else if (line.startsWith('data:')) {
                    dataLines.push(line.slice(5).replace(/^ /, ''))
                }
            }

            const data = dataLines.join('\n')
            if (!event && !data) continue

            if (event === 'status') {
                try {
                    const json = JSON.parse(data) as { step?: string }
                    if (json.step) handlers.onStatus(json.step)
                } catch {
                    // 忽略坏块
                }
            }

            if (event === 'token') {
                try {
                    const json = JSON.parse(data) as { text?: string }
                    if (json.text) handlers.onToken(json.text)
                } catch {
                    // 忽略坏块
                }
            }

            if (event === 'done') {
                const json = JSON.parse(data) as DoneEvent
                gotDone = true
                handlers.onDone(json)
                return json
            }

            if (event === 'error') {
                try {
                    const json = JSON.parse(data) as { message?: string }
                    throw new Error(json.message || '服务出错了')
                } catch (e) {
                    if (e instanceof SyntaxError) throw new Error('服务返回了错误')
                    throw e
                }
            }
        }
    }

    if (!gotDone) {
        throw new Error('连接中断了，请重试')
    }

    throw new Error('连接中断了，请重试')
}

export async function streamChat(options: StreamChatOptions): Promise<DoneEvent> {
    const token = localStorage.getItem('lg_token')

    const payload: Record<string, unknown> = {
        message: options.message,
    }

    if (options.scene) payload.scene = options.scene
    if (options.sessionId) payload.session_id = options.sessionId
    if (options.persona) payload.persona = options.persona

    const res = await fetch('/py/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
        signal: options.signal,
    })

    if (res.status === 401) {
        localStorage.removeItem('lg_token')
        const err = new Error('登录状态过期啦，请重新登录') as Error & { code?: string }
        err.code = LOGIN_EXPIRED
        throw err
    }

    if (!res.ok) {
        let msg = '请求失败'
        try {
            const json = await res.json()
            msg = json?.msg || json?.message || json?.detail || msg
        } catch {
            // 保持默认提示
        }
        throw new Error(msg)
    }

    return readSseStream(res, options)
}