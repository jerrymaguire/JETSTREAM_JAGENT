# Goal Loop 设计

## 1. 核心模型

AgentShow 采用两级循环：

```text
Conversation
└─ Goal
   ├─ Iteration 1 -> Pi Run 1 -> Inner Loop
   ├─ Iteration 2 -> Pi Run 2 -> Inner Loop
   ├─ Iteration 3 -> Pi Run 3 -> Inner Loop
   └─ Verification
```

- `Inner Loop`：Pi 在一次 Run 内完成模型请求、工具调用、工具结果回灌和下一轮模型请求。
- `Outer Goal Loop`：FastAPI 在同一个会话内发起多次 Pi Run，根据进度和验收结果决定是否继续。

FastAPI 不替代 Pi 的 Inner Loop，Pi 也不负责跨 Run 的目标状态机。

## 2. 会话与目标

### Conversation

- 用户点击“新对话”创建。
- 一个对话可包含多次用户消息和 Agent 回答。
- Pi JSONL 保存完整会话历史。
- 同一时间最多有一个活跃 Goal。

### Goal

```text
Goal
  id
  session_id
  objective
  completion_criteria[]
  constraints[]
  acceptance_mode
  status
  current_iteration
  max_iterations
  budget
  progress_summary
  created_at
  started_at
  ended_at
```

### GoalCriterion

```text
GoalCriterion
  id
  goal_id
  description
  type
  required
  status
  evidence
```

类型：

- `file_exists`
- `command_success`
- `test_success`
- `content_check`
- `model_judge`
- `user_confirm`
- `manual`

### GoalIteration

```text
GoalIteration
  id
  goal_id
  iteration_no
  planned_action
  run_id
  result_summary
  progress_delta
  evidence[]
  verdict
  next_action
  started_at
  ended_at
```

`verdict`：

- `continue`
- `replan`
- `wait_user`
- `completed`
- `blocked`
- `no_progress`
- `failed`

## 3. 状态机

```text
draft
  -> planning
  -> running
  -> verifying
       -> running
       -> waiting_user -> running
       -> paused -> running
       -> completed
       -> blocked
       -> budget_exhausted
       -> cancelled
       -> failed
```

规则：

- 只有 `planning`、`running`、`verifying` 可以自动推进。
- `waiting_user` 必须等待用户输入、审批或决策。
- `paused` 不自动启动新 Run。
- `completed`、`cancelled`、`blocked` 是终态，除非用户显式重新开启。

## 4. Goal Supervisor

FastAPI 新增 `GoalSupervisor`。

职责：

1. 解析目标与完成标准。
2. 创建第一轮计划。
3. 调用 Session Service 启动 Pi Run。
4. 接收本轮的模型、工具和审批事件。
5. 生成本轮结果摘要和证据。
6. 执行完成验证。
7. 判断继续、重规划、等待或结束。
8. 持久化 Goal、Iteration 和证据。
9. 处理暂停、恢复、取消和预算耗尽。

GoalSupervisor 是控制状态机，不直接调用模型 Provider。

## 5. 单轮算法

```text
for iteration in remaining_iterations:
  1. check_goal_state
  2. check_total_budget
  3. build_iteration_brief
  4. persist iteration.started
  5. start Pi Run
  6. stream and persist events
  7. wait for run settlement
  8. collect evidence
  9. evaluate criteria
  10. classify progress
  11. persist iteration.completed
  12. if completed -> stop
  13. if blocked -> wait_user
  14. if no progress limit reached -> block
  15. if budget exhausted -> stop
  16. else continue or replan
```

## 6. 每轮输入

GoalSupervisor 向 Pi 发送结构化目标提示：

```json
{
  "goal": "完成 AgentShow 轨迹图页面",
  "completion_criteria": [
    "可以打开示例会话",
    "轨迹展示总时长、轮次、调用开始时间、持续时长和摘要",
    "构建和测试通过"
  ],
  "constraints": [
    "不修改用户工作区之外的路径",
    "不暴露 API Key"
  ],
  "current_iteration": 2,
  "previous_progress": "已经完成数据模型和时间轴组件",
  "last_blocker": null,
  "next_action_hint": "实现详情面板并补测试"
}
```

提示必须明确：

- 本轮只处理最有价值的一步。
- 不要声称完成未验证的事项。
- 使用 `goal_report` 工具返回结构化结果。
- 如果需要用户决策，必须说明阻塞点。

## 7. goal_report 工具

新增受控工具：

```json
{
  "status": "in_progress",
  "summary": "完成时间轴基础组件",
  "progress": [
    "新增时间比例尺",
    "渲染调用条形"
  ],
  "evidence": [
    {
      "type": "test",
      "path": "tests/trace.spec.ts",
      "result": "passed"
    }
  ],
  "remaining": [
    "详情面板",
    "移动端布局"
  ],
  "blocker": null,
  "requested_next_action": "实现详情面板"
}
```

`goal_report` 是元数据工具，不直接修改工作区。它的输出进入 GoalIteration。

如果模型没有调用 `goal_report`：

- 仍可从消息和工具事件生成摘要。
- 标记 `report_missing` 警告。
- 不因此自动判定目标完成。

## 8. 完成验证

按优先级执行：

1. 确定性检查。
   - 文件存在。
   - 命令退出码。
   - 测试通过。
   - JSON/配置校验。
2. 内容检查。
   - 指定文本或结构存在。
3. 用户确认。
4. 模型评估。

模型评估只能用于无法机械验证的语义目标，且：

- 必须提供评估理由。
- 必须引用证据。
- 不得覆盖失败的确定性检查。

所有 required criteria 通过才标记 `completed`。

## 9. 进度判断

每轮计算：

- 新增完成标准数量。
- 新增文件或修改数量。
- 测试状态变化。
- 工具成功数量。
- 是否存在新的 blocker。
- 与上一轮摘要的相似度。

无进展：

- 连续 2 轮无新增证据。
- 连续重复同一失败。
- 连续要求同一审批但未获批准。

达到阈值后：

- 状态变为 `blocked` 或 `waiting_user`。
- 停止自动发起新 Run。

## 10. 预算

### 总预算

- 最大迭代数。
- 最大总时长。
- 最大总 token。
- 最大成本。
- 最大工具调用数。

### 单轮预算

- 单轮时长。
- 单轮 token。
- 单轮工具调用数。
- 单轮重复工具次数。

任何预算耗尽：

- 停止当前 Run。
- 保存进度。
- Goal 状态为 `budget_exhausted`。
- UI 显示已完成部分和剩余工作。

## 11. 暂停、恢复、取消

### 暂停

- 当前 Run 若在运行，等待安全点或中止。
- 状态改为 `paused`。
- 不再自动启动下一轮。

### 恢复

- 读取最后 GoalIteration。
- 从下一轮继续。
- 不重复已完成的标准。

### 取消

- 中止当前 Run。
- 取消待审批。
- 状态改为 `cancelled`。
- 禁止后续自动启动。

## 12. 事件

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

## 13. Trace 映射

```text
TraceSession
├─ goal
│  ├─ iteration 1
│  │  ├─ planning
│  │  ├─ pi run
│  │  │  ├─ llm calls
│  │  │  └─ tool calls
│  │  └─ verification
│  ├─ iteration 2
│  └─ final verification
```

作业五的“轮次”可展示：

- 会话轮次。
- Goal 迭代轮次。
- Pi Agent turns。

默认显示 Goal 迭代轮次，并允许切换。

## 14. 前端表现

Goal 卡片固定在对话顶部：

- 目标。
- 状态。
- 当前迭代。
- 完成标准进度。
- 已用时间、token 和成本。
- Pause、Resume、Cancel。

消息流中每个迭代显示：

- Iteration 标题。
- 本轮计划。
- Run 摘要。
- 证据。
- 判定。

轨迹页把 Iteration 作为一级分组。

## 15. 示例

用户输入：

```text
目标：完成作业五的 Agent 轨迹可视化页面。
完成标准：
1. 能打开一次真实对话的轨迹。
2. 展示总时长和轮次。
3. 展示每次调用的开始时间、持续时长和摘要。
4. 构建、测试和 README 完成。
```

GoalSupervisor：

1. 规划数据模型和 UI。
2. 执行第一轮实现。
3. 运行测试，发现详情面板未完成。
4. 继续第二轮。
5. 验证全部标准。
6. 标记 `completed`。

