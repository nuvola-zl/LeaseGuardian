import os
from typing import Any, Optional

import requests


class JavaServiceError(RuntimeError):
    """
    调用 Java 业务层失败时抛出。
    上层节点只捕获这个异常，不直接感知 requests/HTTP 细节。
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        http_status: Optional[int] = None,
        response_body: Any = None,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.response_body = response_body


_BASE_URL = os.getenv("JAVA_SERVICE_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
_SUCCESS_CODE = "A00000"


def _unwrap_result(body: Any) -> Any:
    """
    按 LeaseGuardian 统一 Result 契约解包：
    - 若 body 是 Result，则 code=A00000 时返回 data，否则抛 JavaServiceError
    - 若不是 Result（兼容早期接口），原样返回
    """
    if isinstance(body, dict) and "code" in body and ("data" in body or "msg" in body):
        code = body.get("code")
        if code == _SUCCESS_CODE:
            return body.get("data")
        raise JavaServiceError(
            message=body.get("msg") or "java service returned business error",
            code=code,
            response_body=body,
        )
    return body

def java_request(
    method: str,
    path: str,
    *,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: float = 10,
) -> Any:
    """
    Python 调 Java 的唯一 HTTP 入口。
    后续要加重试、鉴权、trace header，只改这里。
    """
    url = f"{_BASE_URL}{path}"

    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise JavaServiceError(f"java service request failed: {exc}") from exc

    try:
        body = resp.json()
    except ValueError:
        body = None

    if 200 <= resp.status_code < 300:
        try:
            return _unwrap_result(body)
        except JavaServiceError as exc:
            exc.http_status = resp.status_code
            raise

    # 非 2xx：优先解析 Result 错误体，解析不到就给原始提示
    code = None
    message = f"java service http error: {resp.status_code}"
    if isinstance(body, dict):
        code = body.get("code")
        message = body.get("msg") or message

    raise JavaServiceError(
        message=message,
        code=code,
        http_status=resp.status_code,
        response_body=body,
    )