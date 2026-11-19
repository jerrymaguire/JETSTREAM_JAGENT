# 流水线状态

| 阶段 | 状态 | 产物 |
|---|---|---|
| 阶段 0 环境准备 | 已完成 | 路径、参考代码评估、架构假设 |
| 阶段 1 需求拆分 | 已完成 | 作业需求和完全体 Agent 需求 |
| 阶段 2 开发任务计划 | 已完成设计阶段计划 | 12 个工作包和 TASK-101 |
| 阶段 3 系统设计 | 已完成 | `design/full-agent/` |
| 阶段 3 代码框架 | 已完成 | Vue、FastAPI、Pi Agent Host |
| 阶段 3 业务实现 | 已完成 | 对话、Goal、API Key、Trace、工具和 UI |
| 阶段 4 设计符合性审查 | 已完成 | 设计能力已落到代码 |
| 阶段 5 代码质量审查 | 已完成 | TypeScript 构建和 Python 语法检查通过 |
| 阶段 6 测试与覆盖率 | 已完成 | Pytest 4 passed、Playwright 页面无错误 |
| 阶段 7 交付汇总 | 已完成 | README、示例、截图和说明齐备 |

## 当前权威设计

`design/full-agent/` 取代早期纯前端轨迹查看器设计。

## 运行入口

- URL：`http://127.0.0.1:8000`
- 启动：`.\run.ps1`
- 数据：`data/`
- 前端：`deliverables/frontend/`
- 后端：`deliverables/backend/`
- Agent Host：`deliverables/agent-host/`

