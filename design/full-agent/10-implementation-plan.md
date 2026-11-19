# 实施计划

## 1. 当前阶段

已完成：

- 参考代码评估。
- 完全体 Agent 需求梳理。
- 系统架构。
- Pi Runtime、LLM Gateway、API Key、工具、Skill、Context、Memory、Trace 和前端设计。

未完成：

- 代码脚手架。
- 业务实现。
- 测试。
- 截图和录屏。

## 2. 实施原则

1. 先打通最小真实 Agent Run。
2. 再补工具治理和审批。
3. 再补 Skill、Memory 和 Trace。
4. 最后完成 UI 打磨和交付文档。
5. 每个阶段都必须能独立演示。

## 3. 阶段划分

### Phase 1: 基础骨架与 LLM Gateway

内容：

- FastAPI 项目。
- SQLite 和迁移。
- Provider、Model、Credential。
- API Key 加密和测试连接。
- OpenAI-compatible 内部模型接口。
- Vue 项目壳。

验收：

- 可在设置页保存 DeepSeek 或兼容端点密钥。
- 可通过 FastAPI 发起一次流式模型请求。
- 密钥不回显。

### Phase 2: Pi Sidecar 与真实对话

内容：

- Pi RPC client。
- Sidecar 生命周期。
- Pi models.json 生成。
- 会话创建、消息发送、事件流。
- 前端流式聊天。
- 中止和恢复。

验收：

- 用户可在 UI 与 Agent 连续对话。
- Pi 模型请求经 FastAPI。
- 关闭并恢复会话后历史仍在。

### Phase 2A: Goal Loop

内容：

- Goal、GoalCriterion、GoalIteration 数据模型。
- GoalSupervisor 状态机。
- 目标规划、执行、验收和继续判断。
- 暂停、恢复、取消。
- `goal_report` 工具。
- 无进展和预算检测。

验收：

- 用户可在已有对话中设定目标。
- 同一 Goal 可自动发起多次 Pi Run。
- 每轮有进度、证据和判定。
- 只有完成标准通过后才完成。
- 预算耗尽或阻塞时停止。

### Phase 3: 工具与审批

内容：

- Tool Registry。
- TypeBox/Pydantic 参数校验。
- 文件、搜索、patch、命令和 Git 工具。
- 沙箱、输出截断、环境清理。
- 审批单和 UI 弹窗。
- 工具审计。

验收：

- Agent 可读工作区。
- 写文件需要批准。
- 命令有超时和取消。
- Trace 中能看到工具调用。

### Phase 4: Skill、Context 和 Memory

内容：

- Skill 发现、信任、启用和显式调用。
- Context 规则。
- Pi compaction 事件接入。
- 长期记忆。
- 记忆召回和写入审批。

验收：

- 项目 Skill 可控加载。
- 活动分支上下文正确。
- 记忆可检索和删除。
- 上下文压缩可在 Trace 中查看。

### Phase 4A: Skill 生命周期与单 Agent 评测

内容：

- Skill 版本、owner、content hash 和实际生效版本。
- 显式加载与自动选择验证。
- 反例、缺输入和执行失败测试。
- Task、Strategy、Experiment、Trial。
- execution_status、outcome_status、gate_status 分离。
- 实际模型请求快照。
- Program Grader、LLM Judge 和人工 Review。
- 版本比较与回归门禁。

验收：

- 能运行一个 Task、一个 Strategy 和一次 Trial。
- 能查看真实请求、工具、产物和 Outcome。
- 能区分完成、失败、未知和执行错误。
- 关键旧能力退化时，门禁可拒绝采用。

### Phase 5: Trace 与作业交付

内容：

- Trace 事件规范化。
- Span 构建。
- 总览泳道和瀑布图。
- 轮次、类型、状态和关键词筛选。
- 详情检查器。
- 示例会话和导出。

验收：

- 同时展示总时长、轮次、开始时间、持续时长和摘要。
- 实时轨迹和历史轨迹都可读。
- 5,000 个事件仍可操作。

### Phase 6: 硬化与验收

内容：

- E2E。
- 安全扫描。
- 性能测试。
- 可访问性。
- README。
- 截图和录屏。
- 简要说明文档。

## 4. 推荐 TASK

| TASK | 内容 | 依赖 |
|---|---|---|
| TASK-001 | FastAPI、SQLite 和前端骨架 | 无 |
| TASK-002 | Provider、Model、Credential 和 LLM Gateway | TASK-001 |
| TASK-003 | Pi RPC Sidecar 和流式对话 | TASK-002 |
| TASK-004 | 会话恢复、中止和多会话管理 | TASK-003 |
| TASK-010 | Goal Loop、完成验证和自动迭代 | TASK-003、TASK-004 |
| TASK-005 | Tool Registry、Sandbox 和审批 | TASK-003 |
| TASK-006 | Skill、Context 和 Memory | TASK-003、TASK-005 |
| TASK-011 | Skill 版本、加载验证和变更回归 | TASK-006 |
| TASK-012 | 单 Agent Evaluation Harness | TASK-003、TASK-005、TASK-010 |
| TASK-007 | Trace 采集、查询和可视化 | TASK-003、TASK-005、TASK-010、TASK-012 |
| TASK-008 | 设置、Skill、Memory、Goal、Eval 和 Trace 前端页面 | TASK-004、TASK-006、TASK-007、TASK-010、TASK-011、TASK-012 |
| TASK-009 | 测试、性能、安全、README 和演示 | TASK-008 |

## 5. 质量门禁

### 功能

- 真实模型对话通过 FastAPI。
- Pi 是唯一 Agent Loop。
- Goal Loop 不替代 Pi Inner Loop。
- 工具调用全部经过治理。
- Skill 按 Pi 标准加载。
- Trace 可由真实事件重建。
- 评测状态不能用一个字段混淆执行、结果和门禁。

### 安全

- 0 个 API Key 明文入库。
- 0 个密钥进入 Pi 环境。
- 0 个工作区路径逃逸。
- 0 个未审批高风险写入。

### 测试

- LLM Gateway mock 测试。
- Pi RPC 事件 fixture 测试。
- Tool Runtime 单元测试。
- WebSocket 重连测试。
- 桌面和移动视觉回归。

### 作业

- PC0 作业要求 100% 覆盖。
- README 可独立运行。
- 截图和录屏包含对话页和轨迹页。
- 简要说明文档完整。

## 6. 风险

| 风险 | 影响 | 对策 |
|---|---|---|
| Pi RPC 版本变化 | 事件字段变化 | 固定 Pi 版本并加协议适配测试 |
| Node/Python 双运行时 | 部署复杂 | 提供一键启动和容器 |
| 工具审批阻塞 | 对话体验变差 | 前端实时审批和超时提示 |
| Trace 数据量过大 | 数据库增长 | 摘要入库、原文按需加载 |
| 多 Provider 工具调用差异 | 兼容性 | 第一版优先 OpenAI-compatible |
| 密钥安全 | 严重 | Keyring、加密、脱敏和测试 |

## 7. 停止线

本轮只完成需求与设计。进入实现前需要用户确认：

1. 是否采用“模块化单体 FastAPI + Pi Sidecar”。
2. 首批 Provider 只需 OpenAI-compatible 和 DeepSeek，还是必须同时支持 Anthropic。
3. 长期记忆是否属于第一版必达。
4. 是否需要公网访问和登录。
5. 目标完成是否允许模型评估，还是必须全部使用确定性检查或用户确认。
6. 单 Agent Evaluation 是否进入第一版，还是作为第二阶段增强。

