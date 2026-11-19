# 统一 LLM Gateway 与 API Key 管理

## 1. 设计目标

- 所有模型调用经过 FastAPI。
- Pi 只看到一个 OpenAI-compatible 内部 Provider。
- 上游 Provider 密钥不进入 Pi、浏览器、日志和 Trace。
- 统一处理流式文本、工具调用、usage、成本、错误和重试。
- 新 Provider 通过 adapter 扩展，不修改 Agent Loop。

## 2. 内部接口

Pi 请求：

```text
POST /internal/llm/v1/chat/completions
Authorization: Bearer <SERVICE_TOKEN>
Content-Type: application/json
```

请求体使用 OpenAI Chat Completions 子集：

```json
{
  "model": "deepseek-default",
  "messages": [],
  "tools": [],
  "stream": true,
  "max_tokens": 8192,
  "temperature": 0.2
}
```

FastAPI 解析 `model` alias，不信任请求中的 Provider 名称。

响应：

- 流式：SSE `data:` 记录。
- 非流式：OpenAI-compatible JSON。
- 文本 delta 和 tool call delta 必须透传。

服务认证：

- 每次 Sidecar 启动生成短期内部 token。
- token 只允许访问 `/internal`。
- FastAPI 校验 session、run 和 sidecar 身份。

## 3. LLM Gateway 管线

```text
Request
  -> Authenticate internal caller
  -> Validate model alias
  -> Load model profile
  -> Load provider profile
  -> Decrypt credential
  -> Provider adapter transform
  -> Upstream request
  -> Normalize stream chunks
  -> Normalize usage and errors
  -> Emit trace events
  -> Stream back to Pi
```

每个请求记录：

- `request_id`
- `session_id`
- `run_id`
- `provider_id`
- `model_id`
- 开始和结束时间
- TTFT
- input/output/cache tokens
- 估算成本
- 状态和错误码
- 是否重试

不记录完整 Authorization。

## 4. Provider Adapter

```python
class ProviderAdapter(Protocol):
    async def stream_chat(self, request: NormalizedChatRequest) -> AsyncIterator[ChatDelta]: ...
    async def complete_chat(self, request: NormalizedChatRequest) -> NormalizedChatResponse: ...
    async def test_connection(self, profile: ProviderProfile, credential: str) -> ConnectionTest: ...
```

第一版实现：

- `OpenAICompatibleAdapter`
  - OpenAI
  - DeepSeek
  - OpenRouter
  - Ollama
  - LM Studio
  - vLLM
  - SGLang

第二版：

- `AnthropicAdapter`
- `GoogleAdapter`

## 5. Model Profile

```json
{
  "id": "deepseek-default",
  "provider_id": "deepseek-main",
  "upstream_model": "deepseek-chat",
  "display_name": "DeepSeek Chat",
  "context_window": 128000,
  "max_output_tokens": 8192,
  "supports_tools": true,
  "supports_reasoning": true,
  "input_price_per_million": 0.3,
  "output_price_per_million": 1.2,
  "cache_read_price_per_million": 0.006,
  "enabled": true
}
```

## 6. API Key Vault

### 数据模型

```text
provider_profiles
  id
  name
  protocol
  base_url
  enabled

credentials
  id
  provider_id
  ciphertext
  nonce
  key_version
  masked_hint
  created_at
  rotated_at
  last_tested_at
  test_status
```

### 加密

- 算法：AES-256-GCM 或 `cryptography.Fernet` 的稳定封装。
- 主密钥来源优先级：
  1. 操作系统 Keyring。
  2. 环境变量 `AGENTSHOW_MASTER_KEY`。
  3. 首次启动生成主密钥文件，权限限制为当前用户。
- 数据库中只保存密文、nonce、版本和掩码。
- 掩码示例：`sk-...a91f`。

### 保存流程

1. 前端提交明文密钥。
2. FastAPI 校验格式。
3. 立即用主密钥加密。
4. 保存密文。
5. 返回 `credential_id` 和掩码。
6. 明文只存在于当前请求内存。

### 使用流程

1. LLM Gateway 根据 provider 取密文。
2. 请求级解密。
3. 发起上游请求。
4. 请求结束后释放明文引用。
5. 不在异常、Trace、调试日志中输出。

### 轮换

- 新密钥先测试。
- 测试成功后替换旧密文。
- `key_version` 加一。
- 记录审计事件，不记录密钥。

### 删除

- 停用后会阻止新请求。
- 用户确认后删除密文。
- 关联会话仍可查看历史，但无法继续使用该 Provider。

## 7. 测试连接

接口：

```text
POST /api/v1/providers/{provider_id}/test
POST /api/v1/models/{model_id}/test
```

测试内容：

- base URL 可达。
- TLS 和 DNS。
- 密钥有效。
- 模型存在。
- 支持流式。
- 支持工具调用时进行最小 tool schema 测试。

不要用完整用户对话测试连接。

## 8. 错误标准化

| 错误码 | 场景 |
|---|---|
| `PROVIDER_AUTH_FAILED` | 401/403 或密钥无效 |
| `MODEL_NOT_FOUND` | 模型不存在 |
| `RATE_LIMITED` | 429 |
| `PROVIDER_TIMEOUT` | 连接或读超时 |
| `CONTEXT_OVERFLOW` | 上下文超限 |
| `TOOL_SCHEMA_UNSUPPORTED` | 模型或端点不支持工具 |
| `UPSTREAM_BAD_REQUEST` | Provider 返回 400 |
| `UPSTREAM_ERROR` | 5xx |
| `STREAM_PARSE_ERROR` | SSE 解析失败 |

错误对象包含 `retryable`，Pi 和 UI 根据它决定是否重试。

## 9. 重试策略

- 认证错误不重试。
- 400 参数错误不重试。
- 429、502、503、504 和超时可重试。
- 流式请求在尚未输出内容前允许重试。
- 已输出内容后不自动重放，避免答案重复。
- 每个 Run 有最大重试次数。

## 10. Usage 与成本

统一字段：

```text
input_tokens
output_tokens
reasoning_tokens
cache_read_tokens
cache_write_tokens
total_tokens
estimated_cost_usd
actual_cost_usd
currency
```

若 Provider 返回成本，优先使用；否则按 Model Profile 单价计算。

## 11. 安全边界

- `/internal` 默认只监听 127.0.0.1。
- 内部 token 不能访问用户 API。
- 上游 Provider 地址在管理端配置，不允许用户在普通聊天中覆盖。
- 防 SSRF：自定义 Provider 默认只允许 HTTP/HTTPS，禁止 file、gopher 和云元数据地址。
- 自定义端点需要显式“信任此地址”。
- API Key 不进入 Pi 的 `models.json`，只使用内部 service token。

