# AgentShow 实现说明

## 1. 作业要求覆盖

### 完整会话

提供内置示例会话“支付文档整理与回归检查”，包含 3 个用户轮次、16 个调用和 1 个已完成的 Goal。

### 总运行时长

Trace 通过全部 Span 的最早开始时间和最晚结束时间计算总时长。示例总时长为 `12.84s`。

### 轮次

顶部分别统计用户消息轮次。Goal 模式另记录 GoalIteration。

### 调用信息

每个 Span 保存：

- `started_at`
- `ended_at`
- `duration_ms`
- `summary`
- `kind`
- `status`
- `parent_span_id`

### 定位与追踪

支持通过：

- `session_id`
- `run_id`
- `span_id`
- `event_id`
- `tool_call_id`
- `goal_id`
- `checkpoint_id`

查询对应对象。

## 2. 设计思路

采用三层结构：

1. Vue 前端负责对话、轨迹和详情展示。
2. FastAPI 负责会话、Goal、API Key、LLM Gateway、Trace、Checkpoint 和 Pi 进程管理。
3. Pi Agent Host 负责真实 Agent Loop 和工具调用。

模型调用链路：

```text
Pi -> FastAPI internal OpenAI-compatible API -> Provider
```

Pi 不直接持有上游 Provider API Key。

## 3. 轨迹图

轨迹页包含：

- KPI：总时长、轮次、调用、错误、Tokens。
- 总览泳道：Agent、LLM、Tool。
- 瀑布列表：开始时间、持续时长和内容摘要。
- 详情检查器：ID、状态、父子关系、工具参数和输出。

## 4. Goal Loop

Goal Loop 由 FastAPI 编排：

```text
Goal
  -> GoalIteration
  -> Pi Run
  -> Tool Calls
  -> finish_goal
  -> Checkpoint
  -> 下一轮或完成
```

## 5. API Key

- API Key 使用 Fernet 加密。
- 主密钥保存在本地 `data/secrets/master.key`。
- API 只返回掩码。
- 上游密钥不会传入 Pi Agent 进程。

## 6. 当前模式

### Demo Agent

不要求 API Key。可以演示对话、保存会话、Goal 和 Trace。

### Pi Agent

配置 OpenAI-compatible Provider 后启用。已验证 FastAPI 内部模型网关、Pi Agent Loop、工具调用和事件回传链路。

### 文件与网络能力

- 支持导入 `.md`、`.txt`、`.docx` 和 `.pdf`。
- 支持将助手回答导出为 Markdown、Word 和 PDF。
- Pi Agent 提供 `web_search` 和 `web_fetch`。
- Trace 展示 Token 总用量和 Token 速度。
- 会话选择时预热 Pi Sidecar，降低首个 token 延迟。

## 7. 验证结果

- 后端测试：21 passed，行覆盖率 81.16%。
- 前端 TypeScript 与 Vite 构建：通过。
- Agent Host TypeScript 构建：通过。
- Demo 对话与 Goal：通过。
- 真实 Pi Tool Loop：通过 Mock OpenAI-compatible 服务验证。
- Playwright 桌面与移动截图：通过，控制台无错误。
- 默认 10 个 Skill、`@skill` 选择、Skill 路径加载和上下文注入：通过。

