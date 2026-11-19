# Pi Agent Runtime 设计

## 1. 选型

Pi 负责 `Inner Loop`，即一次 Run 内的模型、工具和结果循环。跨 Run 的目标推进由 FastAPI `GoalSupervisor` 负责，详见 `02A-goal-loop.md`。

### 采用

`@earendil-works/pi-coding-agent` RPC 模式。

理由：

- FastAPI 是 Python，使用 RPC 避免跨语言 SDK 绑定。
- Pi 子进程与 FastAPI 隔离，崩溃不会拖垮 API。
- RPC 支持长生命周期、多命令和完整事件流。
- Pi 已实现 Agent Loop、Session Tree、Context、Skill 发现和工具执行。
- RPC 支持恢复会话、切换模型、中止、队列和压缩。

### 不采用

- 不手写 Agent Loop。
- 不把 Pi Coding Agent 的源码复制进 FastAPI。
- 不把每个用户消息都启动成一次性 CLI。

## 2. Sidecar 启动

FastAPI 的 `PiProcessManager` 负责生成启动参数和环境变量。

```text
argv:
  node
  <bundled-pi-cli>
  --mode rpc
  --no-extensions
  --extension <agent-show-extension.js>
  --session-dir <APP_DATA_DIR>/sessions/<workspace_id>
  --provider agent-show
  --model <selected_model_alias>

env:
  PI_CODING_AGENT_DIR=<APP_DATA_DIR>/pi-agent
  PI_AGENT_SESSION_ID=<agent_show_session_id>
  PI_AGENT_RUN_ID=<current_run_id>
  AGENTSHOW_INTERNAL_BASE_URL=http://127.0.0.1:<port>/internal
  AGENTSHOW_SERVICE_TOKEN=<short-lived internal token>
```

禁止传入上游 Provider 的 API Key。

## 3. AgentShow Pi Extension

扩展负责三件事：

1. 注册 AgentShow 工具。
2. 将工具调用送入 FastAPI 治理。
3. 发出运行快照和资源状态。

### 3.1 注册工具

工具组：

| 工具 | 执行位置 |
|---|---|
| `list_files` | Node Sidecar |
| `read_file` | Node Sidecar |
| `search_code` | Node Sidecar |
| `write_file` | Node Sidecar |
| `apply_patch` | Node Sidecar |
| `run_command` | Node Sidecar |
| `run_test` | Node Sidecar |
| `git_status` | Node Sidecar |
| `git_diff` | Node Sidecar |
| `memory_search` | FastAPI |
| `memory_get` | FastAPI |
| `memory_write` | FastAPI |
| `rag_query` | FastAPI |
| `web_search` | FastAPI，P1 |

### 3.2 工具调用链

```text
Model emits tool call
       |
       v
Pi custom tool execute
       |
       v
POST /internal/tools/prepare
       |
       +--> invalid -> return validation error
       +--> deny -> return denial reason
       +--> confirm -> create approval and wait
       +--> allow -> continue
       |
       v
Executor = node_local or fastapi_service
       |
       v
POST /internal/tools/complete
       |
       v
return result to Pi
```

### 3.3 事件钩子

Pi RPC 自身会输出会话事件。扩展补充：

- `agent_show.skill_inventory`
- `agent_show.tool_registry`
- `agent_show.context_policy`
- `agent_show.project_trust`
- `agent_show.budget_snapshot`

这些事件由 FastAPI 记录，不直接写入 Pi 的标准消息历史。

## 4. Session

Pi 使用 JSONL 会话文件保存消息和执行事件。

FastAPI 映射：

| 字段 | 存储 |
|---|---|
| `session_id` | SQLite |
| `pi_session_file` | SQLite |
| `workspace_id` | SQLite |
| `agent_profile_id` | SQLite |
| `current_model` | SQLite 投影 + Pi session |
| `last_event_seq` | SQLite |
| 消息和分支结构 | Pi JSONL |

原则：

- Pi 是 Agent 会话事实源。
- SQLite 保存可查询投影和 UI 索引。
- 不尝试把 Pi 分支树改写成 FastAPI 自己的消息树。

## 5. Run

一次用户提交对应一个 Run，除非用户发送 steer 或 follow-up。

在 Goal 模式下，每个 GoalIteration 会创建一次独立 Pi Run。所有 Run 共享同一个 Pi Session，按顺序执行。

Run 字段：

- `run_id`
- `session_id`
- `trigger_message_id`
- `started_at`
- `ended_at`
- `status`
- `stop_reason`
- `model_alias`
- `max_turns`
- `max_tool_calls`
- `max_tokens`
- `max_cost`
- `max_duration`

Run 结束后保存预算快照。

## 6. Loop Guard

即使 Pi 自己会循环，FastAPI 和 Sidecar 仍需要双层预算。

### Sidecar 层

- 在工具执行前检查重复调用和次数。
- 把 Pi 事件中的 usage 记录到当前 Run。
- 超过限制时通过 extension 阻止下一次工具调用。

### FastAPI 层

- 监控 Run 时长。
- 监控 token 和成本。
- 接收中止命令后调用 Pi RPC `abort`。
- 防止用户无限重试。

预算项：

- `max_turns`
- `max_tool_calls`
- `max_repeated_call`
- `max_input_tokens`
- `max_output_tokens`
- `max_total_tokens`
- `max_cost_usd`
- `max_duration_ms`

## 7. Context

Pi 负责活动分支和自动压缩。AgentShow 补充以下内容：

1. 固定安全策略。
2. AgentProfile 系统提示词。
3. 工作区上下文文件。
4. Skill 名称和描述。
5. 长期记忆摘要。
6. 当前用户消息。

优先级：

1. 平台安全策略。
2. 用户显式设置。
3. 项目级 Agent 配置。
4. Skill 指示。
5. 长期记忆。
6. 会话历史。

长期记忆和外部文档属于不可信参考，不能覆盖平台安全策略。

## 8. Skill 加载

Pi 标准机制：

- 启动时扫描配置目录。
- 在系统提示词中加入每个 Skill 的 `name`、`description` 和路径。
- 需要时由模型读取完整 `SKILL.md`。
- 支持 `/skill:name` 显式调用。

AgentShow 设置：

```text
~/.agents/skills/                 user skills
<workspace>/.agents/skills/       project skills
<APP_DATA_DIR>/skills/            managed skills
```

FastAPI 在启动 Sidecar 前检查工作区信任状态。未信任时不启用项目 Skills。

## 9. 模型接入

Pi 看到的 Provider：

```json
{
  "providers": {
    "agent-show": {
      "baseUrl": "http://127.0.0.1:8000/internal/llm/v1",
      "api": "openai-completions",
      "apiKey": "${AGENTSHOW_SERVICE_TOKEN}",
      "models": [
        {
          "id": "deepseek-default",
          "name": "DeepSeek Default",
          "contextWindow": 128000,
          "maxTokens": 8192
        }
      ]
    }
  }
}
```

FastAPI 根据 `deepseek-default` 这个 alias 找到实际 Provider、模型和加密凭据。

模型配置发生变化时：

1. FastAPI 重新生成 Sidecar `models.json`。
2. 活跃会话通过 RPC `set_model` 切换。
3. 新会话启动时读取最新配置。

## 10. 中止与终止

- 用户点击停止：FastAPI 发送 `abort`。
- 工具执行中：向工具 AbortSignal 传递取消。
- 审批等待中：关闭审批单并返回 `cancelled`。
- Sidecar 不响应：超时后终止进程树。
- 所有路径均写入 `run.aborted` Trace 事件。

Goal 模式额外规则：

- 暂停 Goal 时，在安全点停止当前 Run。
- 恢复 Goal 时从下一 Iteration 开始，不重放已消费的审批。
- 取消 Goal 时，中止当前 Run 并清除自动继续标记。

## 11. 单 Agent 边界

当前版本只运行一个主 Agent：

- 不注册 subagent 工具。
- 不加载 `.pi/agents/*.md` 作为运行角色。
- 不做父子 Agent Trace 关联。
- 不做多 Agent 日程、冲突和聚合。

Pi 的 Agent Loop、Session Tree、Skill 和工具仍在 Single Agent 内完整使用。

