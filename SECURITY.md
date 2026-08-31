# Security Policy

请勿在公开 Issue 中披露未修复漏洞。仓库启用 GitHub Private Vulnerability Reporting 后，请通过仓库的 **Security → Report a vulnerability** 私下报告，并包含影响、复现步骤和建议修复。

本地演示 API 没有身份验证，默认只监听回环地址。公网部署前应使用成熟的生产 WSGI/ASGI 服务或反向代理，加入 TLS、身份验证、速率限制、请求超时、并发上限、审计和依赖/容器扫描。不要记录完整偏好请求；过敏原和饮食限制可能涉及敏感健康信息。

维护者目前仅支持最新发布版本。任何声称模型能确保食物过敏安全的行为都是误用。
