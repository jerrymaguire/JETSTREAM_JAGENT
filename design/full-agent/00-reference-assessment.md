# 参考代码评估

## 1. 参考项目

路径：

`D:\wj\projects\AI\GeekAgent\gitstore\ai-agent-fullstack-training\course_code\week05\5-5\EvalLab\codebase`

技术栈：

- TypeScript。
- Node.js 22。
- `@earendil-works/pi-agent-core`
- `@earendil-works/pi-ai`
- `@earendil-works/pi-coding-agent`
- TypeBox。
- Vitest。

## 2. 可复用设计

| 参考模块 | 能力 | AgentShow 处理 |
|---|---|---|
| `src/pi/agent-runner.ts` | 使用 Pi Agent Loop、事件观察、上下文渲染、工具调用 | 改为 RPC Runtime Adapter |
| `src/pi/coding-agent-extension.ts` | Pi 扩展、工具注册、事件钩子 | 改造为 AgentShow Sidecar 扩展 |
| `src/pi/provider.ts` | OpenAI-compatible Provider | 保留思路，但请求改发 FastAPI LLM Gateway |
| `src/runtime.ts` | 参数校验、策略、审批、重试、审计 | 拆为 FastAPI Tool Governance Service + Sidecar Executor |
| `src/registry.ts` | 工具注册和可见性 | 改造为持久化 Tool Registry |
| `src/policy.ts` | RBAC、工具白名单、沙箱和审批 | 作为 P0 权限模型 |
| `src/sandbox.ts` | 路径边界、命令环境清理、超时 | 作为 P0 本地工具边界 |
| `src/loop-guard.ts` | 轮次、token、成本、重复调用预算 | 保留并扩展为 Run Budget |
| `src/context-budget.ts` | 上下文统计、工具输出截断 | 保留并接入 Trace |
| `src/memory.ts` | OKF Markdown 长期记忆 | 作为 P1 长期记忆方案 |
| `src/store.ts` | 审计、Trace、审批表 | 扩展为 FastAPI SQLite Schema |
| `.pi/agents/*.md` | 子 Agent 角色 | 当前版本不引入，只保留为未来可能方向 |
| `.pi/prompts/*.md` | Prompt Template | 作为 Agent 配置资源 |

## 3. 不直接照搬的部分

1. 参考项目是 CLI 和仓库编码 Agent，本项目需要通用对话工作台。
2. 参考项目的 Provider 直接访问 DeepSeek，本项目需要 FastAPI 统一模型网关和密钥管理。
3. 参考项目主要依赖本地 SQLite，本项目需要前端实时事件流和可恢复协议。
4. 参考项目没有完整的浏览器 UI 和 API Key 设置流程。
5. 参考项目没有多会话进程编排，需要增加 Pi Sidecar 生命周期管理。

## 4. 关键结论

- Agent Loop 应由 Pi 负责，不再手写一套。
- FastAPI 是控制平面，不是 Agent Loop 本身。
- Pi 通过 OpenAI-compatible 内网端点访问 FastAPI LLM Gateway。
- 所有工具调用必须进入统一授权和审计链。
- Skill 使用 Pi 标准发现机制，FastAPI 负责管理、信任和展示。
- Context 由 Pi 活动分支和压缩机制主导，FastAPI 补充策略、记忆和观测。
- Trace 从 Pi 事件流和 FastAPI 内部事件共同生成。
- 当前范围保持单 Agent，不实现 Subagent 和角色编排。

