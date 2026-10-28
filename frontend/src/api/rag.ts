const BASE = '/py'

async function request(path: string, options: RequestInit = {}) {
    const token = localStorage.getItem('lg_token')

    const res = await fetch(BASE + path, {
        ...options,
        headers: {
            ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers || {}),
        },
    })

    if (res.status === 401) {
        localStorage.removeItem('lg_token')
        window.location.href = '/login'
        throw new Error('登录过期')
    }

    if (!res.ok) {
        let msg = '请求失败'
        try {
            const json = await res.json()
            msg = json?.detail || json?.message || msg
        } catch {}
        throw new Error(msg)
    }

    return res.json()
}

export const ragApi = {
    listFiles() {
        return request('/rag/files') as Promise<{ filename: string }[]>
    },
    uploadFile(file: File) {
        const fd = new FormData()
        fd.append('file', file)
        return request('/rag/upload', { method: 'POST', body: fd }) as Promise<{ filename: string; chunks: number }>
    },
    deleteFile(filename: string) {
        return request(`/rag/files/${encodeURIComponent(filename)}`, { method: 'DELETE' }) as Promise<{ deleted: string }>
    },
}