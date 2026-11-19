# 会话、Trace 与存储

## 1. 事实源

| 数据 | 事实源 |
|---|---|
| Agent 消息、分支、压缩 | Pi JSONL |
| 会话索引、模型、工作区映射 | SQLite |
| Trace 事件和 Span | SQLite |
| Provider 和 Model 配置 | SQLite |
| API Key | SQLite 密文 |
| Tool 审批 | SQLite |
| Skill 文件 | 文件系统 |
| 长期记忆 | SQLite + Markdown |
| 工作区文件 | 文件系统 |

## 2. 数据库表

### 2.1 workspaces

```text
id
name
root_path
trusted
created_at
updated_at
```

### 2.2 agent_profiles

```text
id
name
system_prompt
default_model_id
tool_policy_json
context_rules_json
budget_json
created_at
updated_at
```

### 2.3 sessions

```text
id
workspace_id
agent_profile_id
title
pi_session_file
status
current_model_id
created_at
updated_at
last_opened_at
archived
```

### 2.4 runs

```text
id
session_id
trigger_message_id
status
stop_reason
started_at
ended_at
model_id
budget_json
usage_json
error_code
```

### 2.4.1 goals

```text
id
session_id
objective
constraints_json
budget_json
acceptance_mode
status
current_iteration
max_iterations
progress_summary
started_at
ended_at
stop_reason
created_at
updated_at
```

唯一约束：

- 同一 `session_id` 最多一个状态不属于终态的 Goal。

### 2.4.2 goal_criteria

```text
id
goal_id
description
type
required
config_json
status
evidence_json
verified_at
```

### 2.4.3 goal_iterations

```text
id
goal_id
iteration_no
planned_action
run_id
result_summary
progress_delta
verdict
next_action
started_at
ended_at
```

### 2.4.4 goal_evidence

```text
id
goal_id
iteration_id
type
source
summary
payload_json
created_at
```

### 2.5 trace_events

```text
id
session_id
run_id
seq
event_type
span_id
parent_span_id
timestamp
payload_json
redaction_state
```

索引：

- `(session_id, seq)`
- `(run_id, timestamp)`
- `(span_id)`
- `(event_type)`

### 2.6 trace_spans

```text
id
session_id
run_id
parent_span_id
kind
name
started_at
ended_at
duration_ms
status
summary
input_json
output_json
error_json
usage_json
```

### 2.7 tool_calls

```text
id
session_id
run_id
span_id
tool_name
args_json
args_digest
status
risk
executor
approval_id
started_at
ended_at
duration_ms
result_summary
error_code
```

### 2.8 approvals

```text
id
session_id
run_id
tool_call_id
tool_name
args_json
args_digest
risk
status
requested_at
expires_at
decided_at
decided_by
feedback
```

### 2.9 provider_profiles / model_profiles / credentials

见 `04-llm-gateway-and-key-vault.md`。

### 2.10 skills

```text
id
name
description
scope
path
enabled
trusted
disable_model_invocation
diagnostics_json
last_scanned_at
version
content_hash
owner
reviewed_at
```

### 2.10.1 skill_versions

```text
id
skill_id
version
content_hash
source_path
owner
changed_files_json
reviewed_at
created_at
```

运行和评测记录保存实际加载的 `skill_version_id`。

### 2.11 memories

```text
id
workspace_id
concept_id
type
title
description
body_path
sources_json
status
created_at
updated_at
```

### 2.12 model_requests

```text
id
session_id
run_id
request_no
model_id
system_prompt_hash
skill_inventory_hash
memory_digest_hash
message_count
request_json_path
request_sha256
response_json_path
response_sha256
usage_json
started_at
ended_at
status
error_code
```

`request_json_path` 指向受控 Artifact Store。数据库保存 hash 和索引。

### 2.13 snapshots

```text
id
name
workspace_id
kind
manifest_path
content_hash
created_at
```

### 2.14 artifacts

```text
id
run_id
trial_id
kind
path
sha256
size
created_at
```

### 2.15 evaluation_tasks

```text
id
name
description
initial_snapshot_id
input_json
constraints_json
permissions_json
budget_json
tags_json
required
version
created_at
```

### 2.16 evaluation_strategies

```text
id
name
agent_profile_id
provider_id
model_id
prompt_version
skill_versions_json
tool_policy_json
context_rules_json
budget_json
version
created_at
```

### 2.17 evaluation_experiments

```text
id
name
task_ids_json
strategy_ids_json
trial_count
environment_json
grader_policy_json
status
created_at
started_at
ended_at
```

### 2.18 evaluation_trials

```text
id
experiment_id
task_id
strategy_id
trial_no
snapshot_id
session_id
run_id
execution_status
outcome_status
gate_status
stop_reason
started_at
ended_at
```

### 2.19 grader_results

```text
id
trial_id
grader_type
grader_name
verdict
score
evidence_json
reason
created_at
```

### 2.20 reviews

```text
id
trial_id
reviewer
verdict
evidence_json
reason
created_at
```

## 3. Pi 事件到 Trace 的映射

| Pi 事件 | Trace 事件 |
|---|---|
| `session_start` | `session.started` |
| `agent_start` | `run.started` |
| `turn_start` | `turn.started` |
| `message_start` | `message.started` |
| `message_update` | `message.delta` |
| `message_end` | `message.completed` |
| `tool_execution_start` | `tool.started` |
| `tool_execution_update` | `tool.delta` |
| `tool_execution_end` | `tool.completed` / `tool.failed` |
| `turn_end` | `turn.completed` |
| `agent_end` | `run.loop_ended` |
| `agent_settled` | `run.completed` |
| `compaction_start` | `context.compaction_started` |
| `compaction_end` | `context.compaction_completed` |
| `auto_retry_*` | `model.retry` |
| `goal.iteration.started` | `goal.iteration` Span 开始 |
| `goal.iteration.completed` | `goal.iteration` Span 结束 |
| `goal.verification.completed` | `goal.verification` Span |

AgentShow 额外事件：

- `tool.proposed`
- `tool.awaiting_approval`
- `approval.updated`
- `skill.inventory.updated`
- `context.rendered`
- `budget.updated`
- `goal.iteration.reported`
- `goal.blocked`
- `goal.no_progress`

## 4. TraceSession v1

作业五展示模型：

```text
TraceSession
├─ session metadata
├─ rounds[]
├─ calls[]
└─ metrics
```

实时 Agent 与外部导入统一使用该结构。

### Round 定义

- 用户提交一条 prompt 后到 Agent 给出该轮最终回答，算一个产品轮次。
- Pi 的低层 turn 保留在 call 父子关系中。
- UI 可切换“用户轮次”和“Agent turns”。

### Call 类型

- `llm`
- `tool`
- `approval`
- `compaction`
- `system`
- `error`

### 必填

- id
- roundId
- startedAt
- durationMs
- status
- summary
- category

## 5. Span 构建

```text
session
├─ goal
│  ├─ iteration 1
│  │  ├─ planning
│  │  ├─ run
│  │  │  ├─ llm_call
│  │  │  ├─ tool_call
│  │  │  │  ├─ approval
│  │  │  │  └─ tool execution
│  │  │  └─ answer
│  │  └─ verification
│  ├─ iteration 2
│  └─ final verification
└─ compaction
```

Span 时间必须来自原始事件时间，而不是前端到达时间。

### 5.1 实际请求与 Outcome

完整聊天历史不能替代模型实际请求。每轮必须保存：

- 实际 messages。
- tool definitions。
- system prompt hash。
- Skill inventory 和实际加载版本。
- memory digest hash。
- context compaction 状态。
- 模型参数。

Outcome 单独保存：

- 最终文件。
- Diff。
- 新增文件。
- 工作区内容指纹。
- 测试命令、退出码和断言。
- 受控验收后的业务状态。

Trace 只是过程，Outcome 才能证明最终产物。测试结果必须绑定最终工作区指纹，测试后再次修改代码会使旧证据失效。

## 6. 事件持久化

写入策略：

- 先写 `trace_events`。
- 批量更新 `trace_spans`。
- 再广播 WebSocket。
- 写入失败不阻塞 Pi 主循环，但必须告警。
- 事件保留原始 `payload_json`，敏感字段先脱敏。

## 7. 数据目录

```text
AgentShow/
├─ data/
│  ├─ app.db
│  ├─ secrets/
│  ├─ pi-agent/
│  ├─ sessions/
│  │  └─ <workspace-id>/*.jsonl
│  ├─ skills/
│  └─ memory/
├─ workspaces/
└─ logs/
```

日志和数据目录必须被 `.gitignore` 排除。

## 8. 保留策略

- 默认永久保留本地会话。
- 用户可删除会话。
- 事件日志可按大小滚动归档。
- 原始工具输出可只保留摘要和哈希。
- 密钥删除后旧 Trace 仍保留脱敏事件。

## 9. 导入与导出

导出：

- Pi JSONL。
- TraceSession JSON。
- Markdown 说明。
- HTML 截图包，P2。

导入：

- 标准 TraceSession。
- Pi JSONL。
- 外部 Agent adapter。

导入的外部 Trace 为只读，不能直接继续运行。

