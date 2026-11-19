# WP-002 LLM Gateway 与 API Key

## 1. 目标

提供统一模型调用、Provider 管理、加密密钥和连接测试。

## 2. 范围

- 包含：OpenAI-compatible Provider、模型 alias、流式响应、usage、错误、密钥加密。
- 不包含：Anthropic 原生协议和公网多租户。

## 3. 关键规则

- 前端永不回显完整密钥。
- Pi 不持有上游密钥。
- 所有请求经 FastAPI。
- 敏感字段进入日志前必须脱敏。

## 4. 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/providers` | 新建 Provider |
| PUT | `/api/v1/providers/{id}/credential` | 保存密钥 |
| POST | `/api/v1/providers/{id}/test` | 测试连接 |
| POST | `/internal/llm/v1/chat/completions` | Pi 模型请求 |

## 5. 验收

- [ ] 密钥加密入库。
- [ ] 测试连接可用。
- [ ] DeepSeek 可流式调用。
- [ ] tool call delta 可透传。
- [ ] usage 和 cost 可记录。
- [ ] 错误可标准化。

## 6. 负责角色

- 后端开发
- 架构师
- 测试

