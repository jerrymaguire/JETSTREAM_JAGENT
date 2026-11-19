# WP-010 Goal Loop

## 1. 目标

实现一个对话内多次交流、指定目标后自动迭代直至验收完成的外层 Goal Loop。

## 2. 范围

- 包含：Goal、Criterion、Iteration、GoalSupervisor、验收、暂停恢复取消、预算和无进展检测。
- 不包含：跨会话共享目标和云端调度。

## 3. 关键规则

- Pi 负责一次 Run 内的 Inner Loop。
- FastAPI GoalSupervisor 负责跨 Run 的 Outer Loop。
- 同一会话最多一个 active Goal。
- Agent 不得仅凭自然语言自述完成目标。
- required criteria 全部通过才可完成。
- 无进展、预算耗尽或阻塞时停止。

## 4. 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/sessions/{id}/goals` | 创建目标 |
| POST | `/api/v1/goals/{id}/start` | 启动 |
| POST | `/api/v1/goals/{id}/pause` | 暂停 |
| POST | `/api/v1/goals/{id}/resume` | 恢复 |
| POST | `/api/v1/goals/{id}/cancel` | 取消 |
| GET | `/api/v1/goals/{id}/iterations` | 查看迭代 |

## 5. 验收

- [ ] 同一对话可继续多次交流。
- [ ] 可指定目标、完成标准和预算。
- [ ] 自动创建多轮 GoalIteration。
- [ ] 每轮共享同一 Pi Session。
- [ ] 每轮有证据和判定。
- [ ] 完成标准通过后才结束。
- [ ] 暂停和恢复不重复消费审批。
- [ ] 轨迹页按 Goal 和 Iteration 分组。

## 6. 负责角色

- 后端开发
- 前端开发
- 测试
- 架构师

