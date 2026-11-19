# 系统架构

## 1. 架构结论

采用“模块化单体控制平面 + 本地 Agent Sidecar”的架构。

当前架构只包含单个主 Agent，不包含 Multi-Agent、Subagent 或角色编排。Evaluation Harness 评测的是同一套单 Agent Runtime 的指定 Strategy。

不使用微服务的原因：

- 第一版是单用户本地应用。
- FastAPI、Pi Sidecar 和 SQLite 可在一台机器运行。
- 业务模块边界可以靠包结构和接口约束，不需要网络拆分。

不采用纯前端架构的原因：

- API Key 必须安全存储。
- LLM Provider 需要统一代理。
- Pi 是 Node.js 进程，需要 Python 控制平面管理。
- 会话、工具审批、Trace 和事件流需要持久化。

## 2. 总体图

```text
┌────────────────────────────────────────────────────────────┐
│ Vue 3 Web Workbench                                       │
│ Chat | Trace | Approvals | Providers | Skills | Settings  │
└───────────────────────┬────────────────────────────────────┘
                        │ REST / WebSocket / SSE
┌───────────────────────▼────────────────────────────────────┐
│ FastAPI Control Plane                                     │
│                                                            │
│ API Routers                                                │
│ SessionService  GoalSupervisor  ProviderService             │
│ CredentialService                                           │
│ PiProcessManager  ToolService    SkillService               │
│ MemoryService     TraceService   ApprovalService            │
│ EvaluationService SnapshotService ArtifactStore             │
│                                                            │
│ LLM Gateway ──────────► Provider Adapters                  │
│       ▲                     │                              │
└───────┼─────────────────────┼──────────────────────────────┘
        │ OpenAI-compatible   │ HTTPS
        │ internal API        ▼
┌───────┴──────────────┐  DeepSeek / OpenAI / OpenRouter
│ Pi Agent Sidecar     │  Ollama / LM Studio / vLLM
│ per active session   │
│                      │
│ Pi Agent Loop        │
│ Session Tree         │
│ Context Assembly     │
│ Skill Discovery      │
│ Custom Tools         │
└───────┬──────────────┘
        │ filesystem and subprocess
        ▼
┌────────────────────────────────────────────────────────────┐
│ Workspace | Skill dirs | Memory dir | Pi JSONL sessions    │
└────────────────────────────────────────────────────────────┘

FastAPI also owns:
SQLite metadata | trace events | approvals | encrypted credentials
```

## 3. 进程模型

### 3.1 FastAPI 主进程

职责：

- 提供浏览器 API。
- 管理 Provider 和加密凭据。
- 代理模型请求。
- 管理 Pi Sidecar。
- 持久化会话元数据。
- 把 Pi 事件转换为前端事件和 Trace Span。
- 处理工具授权和人工审批。

### 3.2 Pi Sidecar

每个活跃会话启动一个长生命周期 Node.js 子进程：

```bash
node <bundled-pi-cli> \
  --mode rpc \
  --session-dir <data>/sessions/<workspace-id> \
  --extension <agent-show-extension.js>
```

职责：

- 运行 Pi Agent Loop。
- 管理活动分支。
- 组装本次模型请求上下文。
- 发现和加载 Skills。
- 发出模型、工具和状态事件。
- 调用 AgentShow 自定义工具。

### 3.3 Sidecar 生命周期

1. 用户发送第一条消息。
2. FastAPI 查找会话对应的 Pi session 文件。
3. 若没有活跃进程，启动 Sidecar。
4. FastAPI 向 stdin 写 `prompt` 命令。
5. 持续读取 stdout JSONL。
6. 运行结束后保留一段时间，超过 idle TTL 回收。
7. 下次继续时从 JSONL 恢复。

建议配置：

- 最大活跃 Sidecar 数：4。
- idle TTL：15 分钟。
- 单进程启动超时：15 秒。
- 单 Run 总时限：由 Run Budget 配置。

## 4. 通信边界

| 边界 | 协议 | 说明 |
|---|---|---|
| 浏览器到 FastAPI | HTTPS/HTTP + WebSocket | 用户消息、事件流、设置 |
| FastAPI 到 Pi | JSONL over stdin/stdout | Pi RPC 协议 |
| Pi 到 FastAPI | 内网 OpenAI-compatible HTTP | 模型请求与流式响应 |
| Pi 到 FastAPI | 内网 Tool API | 平台工具执行与授权 |
| FastAPI 到 Provider | HTTPS | 上游 LLM |
| FastAPI 到 SQLite | SQL | 元数据、Trace、审批 |

## 5. FastAPI 模块

```text
backend/app/
├─ main.py
├─ api/
│  ├─ sessions.py
│  ├─ goals.py
│  ├─ messages.py
│  ├─ events.py
│  ├─ providers.py
│  ├─ models.py
│  ├─ tools.py
│  ├─ skills.py
│  ├─ memories.py
│  ├─ approvals.py
│  ├─ traces.py
│  ├─ evaluations.py
│  ├─ tasks.py
│  ├─ strategies.py
│  ├─ experiments.py
│  └─ settings.py
├─ agent/
│  ├─ pi_process_manager.py
│  ├─ pi_rpc_client.py
│  ├─ goal_supervisor.py
│  ├─ goal_evaluator.py
│  ├─ event_normalizer.py
│  ├─ run_supervisor.py
│  └─ budget_guard.py
├─ llm/
│  ├─ gateway.py
│  ├─ openai_compatible.py
│  ├─ anthropic_adapter.py
│  ├─ model_registry.py
│  ├─ usage.py
│  └─ errors.py
├─ tools/
│  ├─ registry.py
│  ├─ policy.py
│  ├─ approvals.py
│  ├─ executor.py
│  └─ builtins/
├─ resources/
│  ├─ skills.py
│  ├─ prompts.py
│  └─ memory.py
├─ evaluation/
│  ├─ harness.py
│  ├─ snapshot.py
│  ├─ program_grader.py
│  ├─ llm_judge.py
│  ├─ review.py
│  └─ release_gate.py
├─ trace/
│  ├─ service.py
│  ├─ span_builder.py
│  └─ query.py
├─ security/
│  ├─ credential_vault.py
│  ├─ redaction.py
│  └─ service_auth.py
├─ persistence/
│  ├─ models.py
│  ├─ repositories/
│  └─ migrations/
└─ schemas/
```

## 6. Pi Sidecar 模块

```text
agent-host/
├─ src/
│  ├─ rpc-entry.ts
│  ├─ extension/
│  │  ├─ agent-show-extension.ts
│  │  ├─ tool-registration.ts
│  │  ├─ event-forwarding.ts
│  │  └─ context-hooks.ts
│  ├─ tools/
│  │  ├─ local-executor.ts
│  │  ├─ platform-client.ts
│  │  └─ contracts.ts
│  ├─ model/
│  │  └─ models-json-generator.ts
│  └─ logging/
├─ package.json
└─ tsconfig.json
```

## 7. 一次对话的时序

```text
User -> Vue:
  POST /sessions/{id}/messages

Vue -> FastAPI:
  message + model + agent profile

FastAPI:
  validate session
  acquire Pi sidecar
  write RPC prompt

Pi:
  build context
  read active skills descriptions
  call model

Pi -> FastAPI:
  POST /internal/llm/v1/chat/completions

FastAPI LLM Gateway:
  resolve model alias
  decrypt provider credential
  call upstream provider
  stream text/tool deltas
  record usage

Pi:
  emit message events
  request tool

FastAPI Tool Governance:
  validate args
  evaluate policy
  maybe wait for approval
  return decision

Pi:
  execute local tool or call platform tool
  emit tool result
  continue loop

FastAPI:
  normalize events
  persist trace
  broadcast WebSocket events

Vue:
  render chat and trace incrementally
```

### 7.1 目标驱动时序

```text
User -> Vue:
  create Goal in an existing Session

Vue -> FastAPI:
  objective + completion criteria + constraints + budget

GoalSupervisor:
  persist Goal
  plan next iteration
  call SessionService

SessionService -> Pi:
  start one Run in the same Pi Session

Pi:
  execute Inner Loop
  emit model, tool and approval events

FastAPI:
  persist events
  collect evidence
  evaluate criteria

GoalSupervisor:
  completed -> stop
  blocked -> waiting_user
  in_progress -> start next iteration
```

GoalSupervisor 不得绕过 SessionService 直接启动 Pi，也不得绕过 Tool Governance 执行工具。

### 7.2 单 Agent 评测时序

```text
Evaluator -> FastAPI:
  create Experiment from Tasks + Strategies

EvaluationService:
  create isolated workspace from Snapshot
  create clean Session and Strategy
  start Pi Sidecar
  collect actual requests, responses, tools and artifacts
  run Program Graders
  optionally run LLM Judge
  optionally collect Human Review
  compute outcome_status and gate_status
```

评测必须复用正常 SessionService、Tool Governance 和 Pi Runtime，不另开无治理执行路径。

## 8. 断线与恢复

### 前端断线

- WebSocket 保存 `last_event_seq`。
- 重连时调用 `GET /sessions/{id}/events?after_seq=N`。
- 前端先回放持久化事件，再恢复实时订阅。

### FastAPI 重启

- Pi JSONL 和 SQLite 保留。
- 启动时终止孤立 Sidecar。
- 活跃 Run 标记为 `interrupted`。
- 用户可重新发送或继续会话。

### Pi 崩溃

- FastAPI 捕获退出码和 stderr。
- 当前 Run 标记 `failed`。
- 保留已收到事件。
- 下次打开会话时重新启动 Pi 并从最后 checkpoint 恢复。

## 9. 并发

- 一个 Session 同时只允许一个 active Run。
- 一个 Session 同时最多只有一个 active Goal。
- 新消息在运行中默认作为 steer 或 follow-up。
- 不同 Session 可并行运行，受 `MAX_ACTIVE_SIDECARS` 限制。
- 全局 SQLite 使用 WAL。
- 工具调用、审批和事件写入使用事务或批处理。

## 10. 架构约束

1. FastAPI 不得直接保存 Pi 对话正文作为唯一事实源。
2. Pi JSONL 是 Agent 会话事实源。
3. SQLite 是产品索引、Trace、审批和配置事实源。
4. Pi 不得直接持有上游 Provider 密钥。
5. 所有工具不得绕过 Tool Governance。
6. 所有运行事件必须带 `session_id`、`run_id`、`sequence` 和时间戳。
7. 浏览器不得直接访问 Pi Sidecar。
8. Goal Loop 必须复用同一 Session 历史，不得为每轮创建无关联的新会话。
9. Goal 状态和迭代记录由 FastAPI 持久化。
10. Evaluation Harness 只评测单 Agent Strategy，不引入 Subagent。
11. `execution_status`、`outcome_status` 和 `gate_status` 必须分开。

