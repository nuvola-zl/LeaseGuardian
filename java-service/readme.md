## Windows 中文调用注意
PowerShell 5.1 直接 curl/Invoke-RestMethod 可能出现中文乱码；可先执行 `chcp 65001`。
但更推荐用 Python requests 发 JSON 验证中文，编码更稳。