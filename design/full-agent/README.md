# 完全体 Agent 设计

本目录是 AgentShow 的权威设计，取代早期“纯前端轨迹查看器”方案。

## 系统构成

```text
Vue 3 Frontend
      |
      | REST + WebSocket
      v
FastAPI Control Plane
  ├─ Session Service
  ├─ LLM Gateway
  ├─ API Key Vault
  ├─ Tool/Skill/Memory Services
  ├─ Trace Service
  └─ Pi Process Manager
          |
          | JSONL RPC over stdio
          v
Pi Agent Sidecar
  ├─ Agent Loop
  ├─ Session Tree
  ├─ Context Assembly
  ├─ Skill Discovery
  ├─ Tool Calls
  └─ Event Stream
          |
          | OpenAI-compatible internal HTTPS
          v
FastAPI LLM Gateway
          |
          v
DeepSeek / OpenAI / OpenRouter / Ollama / custom endpoint
```

## 文档索引

| 文档 | 内容 |
|---|---|
| `01-product-design.md` | 产品范围、角色和核心流程 |
| `02-system-architecture.md` | 分层、进程、组件和时序 |
| `02A-goal-loop.md` | 会话、目标和跨 Run 自动迭代 |
| `03-pi-agent-runtime.md` | Pi RPC、扩展、事件和会话 |
| `04-llm-gateway-and-key-vault.md` | 统一模型服务和 API Key |
| `05-fastapi-contracts.md` | 外部 API、内部 API 和事件协议 |
| `06-tools-skills-context-memory.md` | 工具、Skill、Context、Memory |
| `07-sessions-traces-and-storage.md` | 数据模型、数据库和 Trace |
| `08-frontend-workspace.md` | 对话、轨迹、设置和审批界面 |
| `09-security-and-deployment.md` | 安全、沙箱和部署 |
| `10-implementation-plan.md` | 实施阶段、TASK 和门禁 |
| `11-skill-lifecycle.md` | Skill 版本、加载、验证和变更回归 |
| `12-single-agent-evaluation.md` | 单 Agent 评测闭环和采用门禁 |

## 架构选择

- 形态：模块化单体控制平面 + 本地 Pi Sidecar。
- 前端：Vue 3 + TypeScript + Vite。
- 控制平面：Python 3.12 + FastAPI + SQLAlchemy + SQLite。
- Agent 引擎：Node.js 22 + Pi Coding Agent。
- 通信：REST、WebSocket/SSE、Pi JSONL RPC。
- 存储：SQLite、Pi JSONL、工作区文件、Skill/Memory 目录。
- 部署：本地 Web 应用，默认只监听回环地址。

当前不包含 Multi-Agent、Subagent 和角色编排。

## 两级循环

- Inner Loop：Pi 在一次 Agent Run 内执行模型、工具、结果和继续判断。
- Outer Goal Loop：FastAPI 在同一会话中连续发起多次 Pi Run，直到目标完成或停止。

