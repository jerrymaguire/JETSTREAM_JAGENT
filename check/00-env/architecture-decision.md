# 架构类型决策

- 状态：设计阶段暂定
- 决策：`modular-monolith-with-sidecar`
- 控制平面：FastAPI 模块化单体
- Agent 引擎：Pi Node.js Sidecar
- 前端：Vue 3 单页应用
- 存储：SQLite + Pi JSONL + 本地文件

## 决策依据

- 单用户本地部署，不需要拆分微服务。
- FastAPI 负责统一模型网关、API Key、会话、工具审批和 Trace。
- Pi 已提供成熟 Agent Loop、Session Tree、Context 和 Skill 机制。
- Node Sidecar 提供进程隔离，FastAPI 可以使用 JSONL RPC 控制。
- 模块化单体保留清晰边界，同时降低运行和调试成本。

## 关键边界

1. Pi 不持有上游 Provider API Key。
2. FastAPI 不重写 Agent Loop。
3. 所有模型请求经过 FastAPI LLM Gateway。
4. 所有工具调用经过统一治理。
5. Pi JSONL 是 Agent 会话事实源。

## 重新评估条件

- 需要公网多租户和团队协作。
- 需要多个独立 Agent 服务横向扩展。
- 需要将模型网关、工具服务或 Trace 服务独立扩容。
- 需要跨设备同步和集中审计。

