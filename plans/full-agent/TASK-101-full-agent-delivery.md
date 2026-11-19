# TASK-101 完全体 Agent 交付

## 1. 开发任务目标

交付可配置模型和 API Key、可与 Pi Agent 对话、可执行受控工具、可加载 Skill、可记忆并可视化完整轨迹的本地 Agent 工作台。

## 2. 工作包排序

| 序号 | 工作包 | 负责角色 | 依赖 |
|---|---|---|---|
| 1 | WP-001-基础工程与运行骨架 | 架构师/后端/前端 | 无 |
| 2 | WP-002-LLM Gateway 与 API Key | 后端 | WP-001 |
| 3 | WP-003-Pi Agent Runtime | 后端 | WP-002 |
| 4 | WP-004-会话与对话 API | 后端/前端 | WP-003 |
| 5 | WP-005-工具、沙箱与审批 | 后端/前端 | WP-003 |
| 6 | WP-010-Goal Loop | 后端/前端 | WP-003、WP-004 |
| 7 | WP-006-Skill、Context 与 Memory | 后端/前端 | WP-003、WP-005 |
| 8 | WP-007-Trace 与作业轨迹图 | 后端/前端 | WP-003、WP-005、WP-010 |
| 9 | WP-011-Skill 生命周期 | 后端/前端/测试 | WP-006 |
| 10 | WP-012-单 Agent Evaluation Harness | 后端/前端/测试 | WP-003、WP-005、WP-010 |
| 11 | WP-008-前端 Agent 工作台 | 前端 | WP-004、WP-006、WP-007、WP-010、WP-011、WP-012 |
| 12 | WP-009-质量与交付 | 测试/架构/运维 | WP-008、WP-011、WP-012 |

## 3. 风险与阻塞项

| 风险 | 影响 | 应对 |
|---|---|---|
| Pi RPC 协议变化 | 事件桥接失败 | 固定版本并增加适配测试 |
| Provider 工具调用差异 | 兼容性不足 | 第一版优先 OpenAI-compatible |
| Node/Python 双运行时 | 启动复杂 | 提供一键启动脚本 |
| 密钥安全 | 严重安全事故 | 加密、脱敏、运行时隔离 |

## 4. 交付物

- `deliverables/frontend/`
- `deliverables/backend/`
- `deliverables/agent-host/`
- `deliverables/ops/`
- README
- 示例数据
- 截图和录屏
- 方案说明

## 5. 验收

- [ ] 作业五 A-01 至 A-11 全部通过。
- [ ] 真实 Agent 对话可用。
- [ ] 同一对话可多次交流。
- [ ] 指定目标后可自动迭代。
- [ ] Skill 可版本化并验证实际生效。
- [ ] 可运行单 Agent Evaluation。
- [ ] API Key 可管理且安全。
- [ ] Trace 由真实运行产生。
- [ ] 质量门禁通过。

