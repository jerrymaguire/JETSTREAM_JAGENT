# WP-012 单 Agent Evaluation Harness

## 1. 目标

建立只评测当前单 Agent Strategy 的 Evaluation Harness，支持可重复 Trial、证据取证、评分和回归门禁。

## 2. 范围

- 包含：Task、Strategy、Experiment、Trial、Snapshot、Artifact、Program Grader、LLM Judge、Human Review、Gate。
- 不包含：Multi-Agent、Subagent、Agent 间协作评测。

## 3. 关键规则

- execution_status、outcome_status、gate_status 分离。
- 每次 Trial 从指定 Snapshot 和干净会话开始。
- 保存实际模型请求，而非仅保存聊天历史。
- 程序检查优先于语义评分。
- 人工通过不能覆盖执行错误或程序失败。
- 被评 Agent 不能修改评测脚本、参考答案或验收标准。

## 4. 数据对象

- EvaluationSuite
- Task
- Strategy
- Experiment
- Trial
- Grader
- Trace
- Outcome
- Review

## 5. 验收

- [ ] 能创建一个 Task。
- [ ] 能创建一个 Strategy。
- [ ] 能运行一次 Experiment。
- [ ] 能保存请求、响应、工具、产物和用量。
- [ ] 能运行 Program Grader。
- [ ] 能记录 unknown。
- [ ] 能生成 pass、hold、reject。
- [ ] 能比较新旧 Strategy 的逐题结果。

## 6. 负责角色

- 后端开发
- 前端开发
- 测试
- 架构师

