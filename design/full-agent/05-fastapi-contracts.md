# FastAPI 接口与事件契约

## 1. API 版本

- 用户 API：`/api/v1`
- 内部 API：`/internal`
- 实时事件：`/api/v1/ws/sessions/{session_id}`
- 健康检查：`/health`

## 2. 会话接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/workspaces` | 工作区列表 |
| POST | `/api/v1/workspaces` | 添加工作区 |
| GET | `/api/v1/sessions` | 会话列表 |
| POST | `/api/v1/sessions` | 新建会话 |
| GET | `/api/v1/sessions/{id}` | 会话详情 |
| PATCH | `/api/v1/sessions/{id}` | 重命名、归档 |
| DELETE | `/api/v1/sessions/{id}` | 删除会话 |
| POST | `/api/v1/sessions/{id}/messages` | 发送消息 |
| POST | `/api/v1/sessions/{id}/abort` | 中止当前 Run |
| POST | `/api/v1/sessions/{id}/fork` | 从历史点分叉 |
| POST | `/api/v1/sessions/{id}/switch-model` | 切换模型 |

### 2.1 目标接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/sessions/{id}/goals` | 为当前会话创建目标 |
| GET | `/api/v1/sessions/{id}/goals` | 目标列表 |
| GET | `/api/v1/goals/{goal_id}` | 目标详情 |
| PATCH | `/api/v1/goals/{goal_id}` | 更新目标说明或完成标准 |
| POST | `/api/v1/goals/{goal_id}/start` | 开始自动迭代 |
| POST | `/api/v1/goals/{goal_id}/pause` | 暂停 |
| POST | `/api/v1/goals/{goal_id}/resume` | 恢复 |
| POST | `/api/v1/goals/{goal_id}/cancel` | 取消 |
| GET | `/api/v1/goals/{goal_id}/iterations` | 迭代记录 |
| POST | `/api/v1/goals/{goal_id}/criteria/{criterion_id}/confirm` | 人工确认验收项 |

创建目标请求：

```json
{
  "objective": "完成 AgentShow 轨迹可视化页面",
  "completion_criteria": [
    {
      "description": "项目构建通过",
      "type": "command_success",
      "required": true,
      "config": {
        "command": "pnpm build"
      }
    },
    {
      "description": "轨迹展示总时长、轮次和调用信息",
      "type": "user_confirm",
      "required": true
    }
  ],
  "constraints": [
    "不暴露 API Key"
  ],
  "budget": {
    "max_iterations": 10,
    "max_duration_ms": 3600000,
    "max_total_tokens": 500000,
    "max_cost_usd": 5
  },
  "auto_start": true
}
```

创建成功返回 `goal_id` 和当前状态。`auto_start=true` 时立即进入 `planning`。

消息请求：

```json
{
  "content": "分析这个仓库并写一份说明",
  "attachments": [],
  "mode": "prompt",
  "model_id": "deepseek-default",
  "thinking_level": "medium"
}
```

`mode` 取值：

- `prompt`
- `steer`
- `follow_up`

发送成功返回：

```json
{
  "accepted": true,
  "session_id": "sess_...",
  "run_id": "run_...",
  "event_stream": "/api/v1/ws/sessions/sess_..."
}
```

## 3. 事件接口

WebSocket 客户端连接：

```text
GET /api/v1/ws/sessions/{session_id}?after_seq=120
```

服务端事件：

```json
{
  "seq": 121,
  "event_id": "evt_...",
  "session_id": "sess_...",
  "run_id": "run_...",
  "type": "message.delta",
  "timestamp": "2026-11-19T12:30:01.123Z",
  "payload": {
    "message_id": "msg_...",
    "delta": "正在读取"
  }
}
```

事件类型：

- `session.updated`
- `run.started`
- `run.completed`
- `run.failed`
- `run.aborted`
- `message.started`
- `message.delta`
- `message.completed`
- `tool.proposed`
- `tool.awaiting_approval`
- `tool.started`
- `tool.delta`
- `tool.completed`
- `tool.failed`
- `model.request.started`
- `model.request.completed`
- `context.rendered`
- `context.compacted`
- `skill.inventory.updated`
- `trace.updated`
- `approval.updated`
- `goal.created`
- `goal.started`
- `goal.iteration.started`
- `goal.iteration.updated`
- `goal.iteration.completed`
- `goal.verification.started`
- `goal.verification.completed`
- `goal.waiting_user`
- `goal.paused`
- `goal.resumed`
- `goal.completed`
- `goal.blocked`
- `goal.budget_exhausted`
- `goal.cancelled`
- `goal.failed`

事件不包含 API Key、Authorization Header 和未经脱敏的环境变量。

## 4. Provider 与密钥接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/providers` | Provider 列表 |
| POST | `/api/v1/providers` | 新建 Provider |
| PATCH | `/api/v1/providers/{id}` | 更新配置 |
| DELETE | `/api/v1/providers/{id}` | 删除 Provider |
| PUT | `/api/v1/providers/{id}/credential` | 保存或轮换密钥 |
| DELETE | `/api/v1/providers/{id}/credential` | 删除密钥 |
| POST | `/api/v1/providers/{id}/test` | 测试连接 |
| GET | `/api/v1/models` | 模型列表 |
| POST | `/api/v1/models` | 注册模型 alias |
| PATCH | `/api/v1/models/{id}` | 更新模型 |
| POST | `/api/v1/models/{id}/test` | 测试模型 |

凭据响应：

```json
{
  "credential_id": "cred_...",
  "provider_id": "deepseek-main",
  "masked_hint": "sk-...a91f",
  "status": "active",
  "last_tested_at": "2026-11-19T12:00:00Z"
}
```

任何接口都不返回完整密钥。

## 5. 工具接口

用户 API：

- `GET /api/v1/tools`
- `PATCH /api/v1/tools/{name}` 启用或配置策略
- `GET /api/v1/sessions/{id}/tool-calls`

内部 API：

- `POST /internal/tools/prepare`
- `POST /internal/tools/authorize`
- `POST /internal/tools/complete`
- `POST /internal/tools/execute`
- `GET /internal/tools/registry`

`prepare` 请求：

```json
{
  "session_id": "sess_...",
  "run_id": "run_...",
  "tool_call_id": "call_...",
  "tool_name": "write_file",
  "arguments": {}
}
```

`prepare` 响应：

```json
{
  "decision": "confirm",
  "approval_id": "apr_...",
  "code": "APPROVAL_REQUIRED",
  "reason": "写入工作区需要批准"
}
```

`decision` 取值：

- `allow`
- `deny`
- `confirm`

## 6. 审批接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/approvals?status=pending` | 审批列表 |
| GET | `/api/v1/approvals/{id}` | 审批详情 |
| POST | `/api/v1/approvals/{id}/approve` | 批准 |
| POST | `/api/v1/approvals/{id}/reject` | 拒绝 |

批准时绑定：

- `approval_id`
- `tool_call_id`
- 参数 canonical hash
- session/run/workspace
- 用户身份

批准后参数变化则审批失效。

## 7. Skill 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/skills` | 已发现 Skill |
| GET | `/api/v1/skills/{name}` | Skill 详情 |
| POST | `/api/v1/skills/reload` | 重新扫描 |
| PATCH | `/api/v1/skills/{name}` | 启用或禁用 |
| GET | `/api/v1/skills/{name}/versions` | Skill 版本 |
| POST | `/api/v1/skills/{name}/validate` | 校验目录和 frontmatter |
| POST | `/api/v1/skills/{name}/test-load` | 验证显式加载 |
| GET | `/api/v1/workspaces/{id}/trust` | 工作区信任状态 |
| POST | `/api/v1/workspaces/{id}/trust` | 信任项目资源 |

Skill 响应包含：

- name
- description
- scope
- path
- enabled
- trusted
- diagnostics
- disable_model_invocation
- version
- content_hash
- owner
- source
- actual_loaded_at

## 8. 记忆接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/workspaces/{id}/memories` | 记忆列表 |
| GET | `/api/v1/memories/{id}` | 记忆正文 |
| POST | `/api/v1/workspaces/{id}/memories` | 手动新增 |
| PATCH | `/api/v1/memories/{id}` | 修改 |
| DELETE | `/api/v1/memories/{id}` | 删除 |

Agent 内部通过 `/internal/memory/search`、`/internal/memory/get`、`/internal/memory/write` 使用记忆。

## 9. Trace 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/sessions/{id}/trace` | 完整 Trace |
| GET | `/api/v1/sessions/{id}/trace/summary` | KPI 汇总 |
| GET | `/api/v1/traces/{run_id}` | 单 Run Trace |
| GET | `/api/v1/traces/{run_id}/events` | 原始事件 |
| GET | `/api/v1/traces/import` | 导入外部 Trace |

Trace 响应使用 `TraceSession v1` 或 `TraceRun v1`。

### 9.1 单 Agent Evaluation 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/api/v1/evaluation/tasks` | Task 列表和创建 |
| GET/POST | `/api/v1/evaluation/strategies` | Strategy 列表和创建 |
| POST | `/api/v1/evaluation/experiments` | 创建实验 |
| GET | `/api/v1/evaluation/experiments/{id}` | 实验详情 |
| POST | `/api/v1/evaluation/experiments/{id}/run` | 启动实验 |
| POST | `/api/v1/evaluation/experiments/{id}/cancel` | 取消实验 |
| GET | `/api/v1/evaluation/trials/{id}` | Trial 详情 |
| GET | `/api/v1/evaluation/trials/{id}/trace` | 真实 Trace |
| GET | `/api/v1/evaluation/trials/{id}/outcome` | Outcome |
| GET | `/api/v1/evaluation/trials/{id}/graders` | Grader 结果 |
| POST | `/api/v1/evaluation/trials/{id}/reviews` | 人工复核 |
| GET | `/api/v1/evaluation/compare` | 新旧 Strategy 对比 |
| POST | `/api/v1/evaluation/release-gate` | 生成采用门禁 |

实验响应必须分开：

```json
{
  "execution_status": "completed",
  "outcome_status": "unknown",
  "gate_status": "hold",
  "reason": "关键验收证据缺失"
}
```

禁止用一个状态字段把“执行结束”和“任务通过”混为一谈。

## 10. 内部 LLM 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/internal/llm/v1/chat/completions` | Pi 模型请求 |
| GET | `/internal/llm/v1/models` | Pi 可用模型 |
| GET | `/internal/health` | Sidecar 健康检查 |

内部认证：

- Header：`Authorization: Bearer <SIDECAR_SERVICE_TOKEN>`
- token 绑定 session、run 和过期时间。
- token 不支持刷新为上游 Provider 密钥。

## 11. 错误格式

```json
{
  "error": {
    "code": "APPROVAL_TIMEOUT",
    "message": "等待人工审批超时",
    "retryable": false,
    "details": {}
  }
}
```

## 12. OpenAPI

- FastAPI 自动生成 OpenAPI。
- Provider、Session、Message、Trace 和 Approval schema 由 Pydantic 定义。
- 内部 API 在开发环境可见，生产环境可隐藏或限制来源。

