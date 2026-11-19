# WP-003 Pi Agent Runtime

## 1. 目标

通过 Pi RPC Sidecar 运行真实 Agent Loop，并与 FastAPI 完成消息和事件桥接。

## 2. 范围

- 包含：Sidecar 进程管理、JSONL RPC、models.json、会话启动、事件转发、中止。
- 不包含：子 Agent 和复杂分支 UI。

## 3. 关键规则

- Pi 是 Agent Loop 的事实实现。
- FastAPI 不重写 ReAct 循环。
- Sidecar 从 stdin 接收命令，从 stdout 接收 JSONL。
- stderr 只作诊断日志。

## 4. 事件

- `run.started`
- `message.delta`
- `message.completed`
- `tool.proposed`
- `tool.completed`
- `run.completed`
- `run.failed`

## 5. 验收

- [ ] 能创建 Pi 会话。
- [ ] 能发送 prompt 并流式返回。
- [ ] 能中止 Run。
- [ ] 能恢复历史会话。
- [ ] Sidecar 崩溃不拖垮 FastAPI。

## 6. 负责角色

- 后端开发
- 前端开发
- 架构师

