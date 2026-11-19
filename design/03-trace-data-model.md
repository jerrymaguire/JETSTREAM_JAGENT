# 通用轨迹数据模型

## 1. 设计目标

`TraceSession v1` 是 AgentShow 的唯一可视化输入模型。它需要：

- 覆盖作业五必填字段。
- 能表达多个 Agent 的常见概念。
- 允许保留原始数据而不污染标准字段。
- 能被校验器稳定验证。
- 能适配本地 JSON、手动字段映射和后续标准协议。

## 2. 顶层结构

```ts
interface TraceSession {
  schemaVersion: '1.0'
  id: string
  title: string
  source: TraceSource
  agent: TraceAgent
  model?: string
  startedAt: string
  endedAt?: string
  timezone?: string
  status: TraceStatus
  rounds: TraceRound[]
  calls: TraceCall[]
  tokens?: TraceTokenUsage
  metadata?: Record<string, unknown>
  warnings?: TraceWarning[]
  raw?: unknown
}
```

`startedAt`、`endedAt` 使用 ISO 8601 UTC 字符串。`id` 在单个导入文件内唯一，`session.id` 在本地库内唯一。

## 3. 子结构

### 3.1 来源

```ts
interface TraceSource {
  adapterId: string
  adapterVersion: string
  fileName?: string
  importedAt: string
  originalFormat?: string
}
```

### 3.2 Agent

```ts
interface TraceAgent {
  name: string
  version?: string
  runtime?: string
  workspaceName?: string
}
```

### 3.3 轮次

```ts
interface TraceRound {
  id: string
  index: number
  startedAt?: string
  endedAt?: string
  status: TraceStatus
  summary?: string
  metadata?: Record<string, unknown>
}
```

### 3.4 调用

```ts
interface TraceCall {
  id: string
  roundId: string
  parentId?: string
  sequence: number
  depth?: number
  category: TraceCallCategory
  name: string
  startedAt: string
  endedAt?: string
  durationMs?: number
  status: TraceStatus
  summary: string
  model?: string
  toolName?: string
  inputPreview?: string
  outputPreview?: string
  error?: TraceError
  tokens?: TraceTokenUsage
  metadata?: Record<string, unknown>
  raw?: unknown
}
```

`summary` 为必填。若原始数据没有摘要，adapter 必须从输入、输出或名称生成不超过 160 个字符的摘要，并添加 warning。

### 3.5 状态

```ts
type TraceStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'error'
  | 'cancelled'
  | 'unknown'
```

### 3.6 调用类型

```ts
type TraceCallCategory =
  | 'llm'
  | 'tool'
  | 'agent'
  | 'system'
  | 'user'
  | 'assistant'
```

UI 可以合并 `user` 和 `assistant` 为对话类型，但模型保留原始语义。

### 3.7 Token

```ts
interface TraceTokenUsage {
  input?: number
  output?: number
  reasoning?: number
  total?: number
  costUsd?: number
}
```

缺失字段不默认为 0，UI 显示为不可用。`total` 缺失时只在 input 和 output 都存在时计算。

### 3.8 错误

```ts
interface TraceError {
  code?: string
  message: string
  stackPreview?: string
}
```

### 3.9 警告

```ts
interface TraceWarning {
  path: string
  code: string
  message: string
  severity: 'info' | 'warning'
}
```

## 4. 示例

```json
{
  "schemaVersion": "1.0",
  "id": "sess_demo_001",
  "title": "支付会话文档与 FAQ 整理",
  "source": {
    "adapterId": "agent-show/v1",
    "adapterVersion": "1.0",
    "importedAt": "2026-11-19T10:00:00.000Z",
    "originalFormat": "json"
  },
  "agent": {
    "name": "DeepSeek Harness",
    "runtime": "local",
    "workspaceName": "deepseek-work"
  },
  "model": "deepseek-chat",
  "startedAt": "2026-10-07T00:05:27.707Z",
  "endedAt": "2026-10-07T00:05:31.107Z",
  "status": "success",
  "rounds": [
    {
      "id": "round-1",
      "index": 1,
      "status": "success",
      "summary": "读取文件并整理支付会话文档"
    }
  ],
  "calls": [
    {
      "id": "call-1",
      "roundId": "round-1",
      "sequence": 1,
      "category": "tool",
      "name": "write",
      "startedAt": "2026-10-07T00:05:27.707Z",
      "endedAt": "2026-10-07T00:05:29.087Z",
      "status": "success",
      "summary": "写入支付会话文档",
      "toolName": "write"
    },
    {
      "id": "call-2",
      "roundId": "round-1",
      "sequence": 2,
      "category": "llm",
      "name": "整理 FAQ 与历史问题",
      "startedAt": "2026-10-07T00:05:29.087Z",
      "endedAt": "2026-10-07T00:05:31.107Z",
      "status": "success",
      "summary": "生成 FAQ、历史问题和代码文件摘要",
      "model": "deepseek-chat"
    }
  ],
  "tokens": {
    "input": 300,
    "output": 155,
    "total": 455
  }
}
```

## 5. 不变量

### 5.1 阻断错误

| 编号 | 规则 |
|---|---|
| E-01 | `schemaVersion` 必须为 `1.0` |
| E-02 | `session.id`、`call.id` 在当前会话内唯一 |
| E-03 | `startedAt` 必须是合法 ISO 时间 |
| E-04 | `startedAt` 不能晚于 `endedAt` |
| E-05 | 每个调用必须属于一个存在的轮次 |
| E-06 | `parentId` 必须指向存在的调用 |
| E-07 | 父子关系不得形成环 |
| E-08 | `summary` 必须存在且非空 |

### 5.2 非阻断警告

| 编号 | 规则 |
|---|---|
| W-01 | 轮次序号不连续 |
| W-02 | 调用顺序不单调 |
| W-03 | 条目不满足 `parentId`，按孤立调用显示 |
| W-04 | duration 与时间戳冲突，以时间戳计算值为准 |
| W-05 | 汇总 token 与调用 token 不一致 |
| W-06 | 摘要由 adapter 自动截断生成 |

## 6. 指标派生

| 指标 | 计算方式 |
|---|---|
| `totalDurationMs` | 最晚 `endedAt` 减最早 `startedAt` |
| `roundCount` | 有效 `roundId` 去重数量 |
| `callCount` | 有效调用数量 |
| `successCount` | `status === 'success'` |
| `errorCount` | `status === 'error'` |
| `runningCount` | `status === 'running'` |
| `activeDurationMs` | 所有调用时间区间并集长度 |
| `tokenTotal` | session token 优先，否则汇总可计算调用 |
| `criticalPathMs` | 从根调用到叶调用的最长有效路径 |

任何派生指标都不得写回原模型，应通过 selector 生成。

## 7. Adapter 映射原则

### 7.1 内置标准格式

`agent-show/v1` 直接校验和加载。

### 7.2 通用 JSON 映射

用户需要映射：

- 根数组或根对象路径。
- 调用 ID、开始时间、结束时间、名称、摘要。
- 轮次 ID、父调用 ID、类型、状态。

映射结果必须先生成预览，再允许入库。

### 7.3 OpenTelemetry GenAI

预留字段：

- span id 映射到 call id。
- parent span id 映射到 parentId。
- gen_ai.operation.name 映射到 category 和 name。
- 资源属性和 trace id 放入 metadata。

该适配器不列入第一版必达范围。

## 8. 脱敏规则

导入时检测并提示以下模式：

- `api_key`、`token`、`secret`、`password`、`authorization`。
- Bearer Token。
- 长字符串形式的私钥。
- 用户主目录绝对路径。

脱敏只发生在预览和导出副本中，不自动破坏用户本地原始数据。用户必须在导出示例前确认脱敏结果。

