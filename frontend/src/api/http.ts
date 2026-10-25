import axios, { AxiosError, type AxiosResponse } from 'axios'
import type { Result } from '@/types'
import { useToast } from '@/composables/useToast'

export const LOGIN_EXPIRED = 'LOGIN_EXPIRED'

const java = axios.create({ baseURL: '/api', timeout: 30000 })
const py = axios.create({ baseURL: '/py', timeout: 30000 })

/* silent 为预留能力：
   目前 API 包装函数（api/auth.ts、api/chat.ts）不透传 config，页面暂传不进来。
   以后需要按请求关闭提示时，给包装函数加 config 透传即可（那边 AI 给过示例写法）。 */
declare module 'axios' {
    export interface AxiosRequestConfig {
        silent?: boolean
    }
}

/* 状态码 → 人话 词汇表：只当兜底用，有后端文案就听后端的 */
const STATUS_MSGS: Record<number, string> = {
    400: '请求参数好像不太对',
    403: '没有权限哦',
    404: '要找的东西不存在',
    409: '好像重复提交了，稍等一下',
    422: '提交的内容有问题，再检查一下吧',
    429: '操作太频繁啦，歇口气',
    500: '服务器开小差了，稍后再试',
    502: '服务打了个盹，刷新试试',
    503: '服务维护中，等会儿再来',
}

function attachToken(instance: typeof java) {
    instance.interceptors.request.use(cfg => {
        const t = localStorage.getItem('lg_token')
        if (t) cfg.headers.Authorization = `Bearer ${t}`
        return cfg
    })
}

function toErr(r?: Partial<Result<unknown>>, fallback = '请求失败', status?: number) {
    const err = new Error(r?.msg || fallback) as Error & {
        code?: string
        request_id?: string | null
        status?: number
    }
    err.code = r?.code
    err.request_id = r?.request_id
    err.status = status
    return err
}

function handleUnauthorized(err: Error & { code?: string; status?: number }) {
    localStorage.removeItem('lg_token')
    err.code = LOGIN_EXPIRED
}

/* ★ 翻译优先级（v3 修订：后端文案永远优先）：
   1. 登录过期 → 统一提示
   2. 根本没收到响应（断网/服务没起）→ 网络提示
   3. 后端说过话（有 msg）→ 原样展示后端文案，如"用户名已存在"
   4. 后端没说话 + 状态码认识 → 词汇表
   5. 都不认识 → "出了点小状况" */
function friendlyMessage(err: Error & { code?: string; status?: number }, hasBackendMsg: boolean): string {
    if (err.code === LOGIN_EXPIRED) return '登录状态过期啦，请重新登录'
    if (!err.status) return '网络好像断了，检查下连接再试'
    if (hasBackendMsg) return err.message
    return STATUS_MSGS[err.status] ?? '出了点小状况'
}

function toastError(
    err: Error & { code?: string; status?: number },
    hasBackendMsg: boolean,
    cfg?: { silent?: boolean },
) {
    if (cfg?.silent) return
    useToast().error(friendlyMessage(err, hasBackendMsg))
}

/* ★ 登录/注册页自己展示错误（内联红字），全局 toast 别插嘴，否则双重打扰 */
function isAuthPageReq(url?: string): boolean {
    const u = url || ''
    return u.includes('login') || u.includes('register')
}

attachToken(java)
attachToken(py)

java.interceptors.response.use(
    (res: AxiosResponse) => res,
    (error: AxiosError<Partial<Result<unknown>>>) => {
        const r = error.response?.data
        const hasMsg = !!r?.msg
        const err = toErr(r, error.message || '网络异常', error.response?.status)

        /* 登录接口的 401 是"密码错误"，不算登录过期，别误伤 */
        const isLoginReq = (error.config?.url || '').includes('login')
        if ((error.response?.status === 401 && !isLoginReq) || r?.code === 'A00010') {
            handleUnauthorized(err)
        }
        if (!isAuthPageReq(error.config?.url)) {
            toastError(err, hasMsg, error.config ?? undefined)
        }
        return Promise.reject(err)
    },
)

py.interceptors.response.use(
    (res: AxiosResponse) => res,
    (error: AxiosError<Partial<Result<unknown>>>) => {
        const r = error.response?.data
        const hasMsg = !!r?.msg
        const err = toErr(r, error.message || '网络异常', error.response?.status)

        if (error.response?.status === 401) handleUnauthorized(err)
        if (!isAuthPageReq(error.config?.url)) {
            toastError(err, hasMsg, error.config ?? undefined)
        }
        return Promise.reject(err)
    },
)

export function unwrapResult<T>(p: Promise<AxiosResponse<unknown>>) {
    return p.then(res => {
        const body = res.data as Result<T>

        if (body.code === 'A00000') return body.data

        const err = new Error(body.msg || '请求失败') as Error & {
            code?: string
            request_id?: string | null
        }
        err.code = body.code
        err.request_id = body.request_id
        throw err
    })
}

export function unwrap<T>(p: Promise<AxiosResponse<T>>) {
    return p.then(r => r.data)
}

export { java, py }