# 单 Agent Evaluation Harness 设计

## 1. 目标

评测当前单个 Agent 配置是否稳定完成任务，并证明 Prompt、Skill、工具或模型改动没有造成关键退化。

当前不评测 Multi-Agent、Subagent 或角色协作。

## 2. 对象模型

### EvaluationSuite

一组 Task。

### Task

```text
id
name
description
initial_snapshot_id
input
constraints
permissions
budget
graders[]
tags[]
required
version
```

### Strategy

Agent 执行配置：

- AgentProfile。
- Provider 和 Model。
- Prompt 版本。
- Skill 版本集合。
- Tool 集合和权限。
- Context 规则。
- 预算。
- 运行模式。

### Experiment

- 一个或多个 Strategy。
- Task 集合。
- Trial 次数。
- 环境配置。
- 判定规则。

### Trial

从指定 Snapshot 和干净会话执行一次 Task。

### Grader

一个维度或一组规则的评分器：

- Program Grader。
- Schema Grader。
- Contract Grader。
- LLM Judge。
- Human Review。

### Trace

实际执行过程。

### Outcome

执行结束后留下的实际产物与状态。

## 3. 状态分离

禁止用一个 `status` 同时表达执行和验收。

```text
execution_status:
  queued | running | completed | timed_out | cancelled | execution_error

outcome_status:
  pass | fail | unknown

gate_status:
  pass | hold | reject
```

规则：

- `execution_status=completed` 不代表 `outcome_status=pass`。
- 执行错误不能由人工评审覆盖。
- 程序失败不能由 Judge 覆盖。
- 证据不足使用 `unknown`。
- 关键未知可导致 `gate_status=hold`。

## 4. 最小闭环

```text
选择 Task 和 Strategy
  -> 创建 Snapshot 工作区
  -> 启动 Pi Sidecar
  -> 执行 Agent
  -> 保存实际请求、响应、工具和产物
  -> 运行 Program Grader
  -> 可选 LLM Judge
  -> 可选人工 Review
  -> 计算 outcome 和 gate
  -> 展示 Trace 与结果
```

第一版先打通一个 Task、一个 Strategy 和一次 Trial。

## 5. 环境

每次 Trial：

- 从规定 Snapshot 创建独立工作区。
- 使用独立 Session。
- 清理或记录长期记忆。
- 重置数据库和测试数据。
- 固定模型、Prompt、Skill 和工具版本。
- 固定预算。
- 记录缓存冷热条件。

原则：要么重置状态，要么把状态作为条件记录。

## 6. 实际请求取证

Trace 必须保存模型实际收到的请求，而不只是完整聊天历史。

每次模型调用保存：

- request id。
- messages。
- tool definitions。
- system prompt hash。
- Skill inventory hash。
- loaded Skill versions。
- memory digest hash。
- context compaction state。
- model parameters。
- provider and model。

这样可判断关键规则是否进入输入。

## 7. 运行包

```text
runs/<run_id>/
├─ manifest.json
├─ task.json
├─ strategy.json
├─ requests.jsonl
├─ responses.jsonl
├─ tools.jsonl
├─ events.jsonl
├─ artifacts/
├─ diff.patch
├─ test-results.json
├─ outcome.json
├─ grader-results.json
├─ judge-results.json
└─ review.json
```

数据库保存索引和摘要，大文件保存到受控 Artifact Store。

## 8. Program Grader

优先检查：

- 单元测试。
- 集成测试。
- 状态。
- 静态分析。
- 工具调用。
- 文件范围。
- Schema。
- Snapshot。
- 接口契约。

Program Grader 由评测方控制，被评 Agent 不能修改。

## 9. LLM Judge

适用：

- 说明是否准确。
- 验证声明是否有证据。
- 未知项是否披露。
- 报告是否覆盖要求。

输出必须包含：

```json
{
  "criterion": "verification_claim_supported",
  "verdict": "pass | fail | unknown",
  "evidence_refs": [],
  "reason": ""
}
```

证据引用必须指向本次运行包中的真实记录。

## 10. 人工 Review

人工负责：

- 确认业务规则。
- 校准 Judge。
- 复核分歧、未知和边界。
- 处理工程取舍。

保存原判、复核结论、证据、原因和时间。

## 11. 版本比较

固定：

- Task 与 Rubric。
- 初始 Snapshot。
- 环境。
- 模型。
- 工具和权限。
- Prompt 和 Skill。
- 预算。
- Trial 次数。

比较：

- 每道 Task 的逐次结果。
- 失败、未知和执行错误。
- 旧能力是否退化。
- 耗时、Token 和成本。

报告观测通过比例。只有满足独立性假设时才计算 pass@k 或 pass^k，并明确标注。

## 12. 回归门禁

门禁类型：

- 核心行为必过。
- 接口兼容必过。
- 修改边界必过。
- 关键旧能力不得退化。
- 安全规则必过。
- 其他质量项按 Rubric。

输出：

- `pass`：允许采用。
- `hold`：关键未知，补证据。
- `reject`：明确失败或关键退化。

只有报告，没有 CI 或采用阻断，不能形成真正门禁。

## 13. 取消与预算

- 取消必须传递到 Pi、模型流、工具和子进程。
- 本地取消不自动保证远端 Provider 停止计费，需标记未知。
- Agent、Judge、Grader 分别统计耗时和费用。
- 总预算包含所有 Trial 和评审。
- 失败、重试和未知 usage 同样记账。

## 14. 前端

新增 Eval 页面：

- Task 列表。
- Strategy 列表。
- Experiment。
- Trial 结果。
- Trace。
- Outcome。
- Grader 结果。
- Judge 和 Review。
- 版本比较。
- Gate 状态。

页面第一屏展示：

- Experiment 状态。
- 完成数与总数。
- pass、fail、unknown。
- 执行错误。
- 耗时和成本。

## 15. 当前不包含

- Multi-Agent 编排。
- Subagent 委托与聚合。
- Agent 间 Trace。
- 多角色争议仲裁。

