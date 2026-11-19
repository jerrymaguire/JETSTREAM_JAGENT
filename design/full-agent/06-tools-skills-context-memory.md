# 工具、Skill、Context 与 Memory

## 1. Tool Runtime

### 1.1 目标

工具必须同时满足：

- 模型可发现。
- 参数可校验。
- 权限可控制。
- 风险可审批。
- 执行可取消。
- 结果可审计。
- 大输出可截断。
- 来源可扩展。

### 1.2 工具元数据

```python
class ToolDefinition(BaseModel):
    name: str
    description: str
    version: str
    input_schema: dict
    executor: Literal["node_local", "fastapi_service"]
    category: Literal["filesystem", "execution", "git", "memory", "rag", "web", "system"]
    risk: Literal["read", "write", "high"]
    permissions: list[str]
    requires_confirmation: bool
    timeout_ms: int
    max_retries: int
    idempotent: bool
    sensitive_fields: list[str]
    enabled: bool
```

### 1.3 第一版工具

| 工具 | 类别 | 风险 | 审批 |
|---|---|---|---|
| `list_files` | filesystem | read | 否 |
| `read_directory` | filesystem | read | 否 |
| `read_file` | filesystem | read | 否 |
| `search_code` | filesystem | read | 否 |
| `write_file` | filesystem | write | 是 |
| `apply_patch` | filesystem | write | 是 |
| `run_command` | execution | high | 是 |
| `run_test` | execution | high | 由策略决定 |
| `git_status` | git | read | 否 |
| `git_diff` | git | read | 否 |
| `memory_search` | memory | read | 否 |
| `memory_get` | memory | read | 否 |
| `memory_write` | memory | write | 是 |
| `rag_query` | rag | read | 否 |
| `web_search` | web | read | P1 |
| `goal_report` | system | read | 否 |

`goal_report` 只上报目标迭代进度、证据、剩余工作和阻塞点，不修改工作区。详细结构见 `02A-goal-loop.md`。

### 1.4 工具调用状态机

```text
proposed
  -> invalid
  -> denied
  -> awaiting_approval -> rejected
                       -> approved -> running
  -> running -> success
             -> failed
             -> cancelled
```

### 1.5 参数校验

- Node 工具使用 TypeBox。
- FastAPI 工具使用 Pydantic。
- `prepare` 阶段同时执行 schema 校验和业务契约校验。
- 校验失败必须返回字段级说明，并把可修复信息回灌模型。

### 1.6 权限模型

三组规则叠加：

1. Agent 工具 allowlist。
2. 用户角色权限。
3. workspace sandbox。

plan 模式额外规则：

- 只允许 `risk=read`。
- 禁止写文件。
- 禁止执行会修改状态的命令。
- 禁止长期记忆写入。

### 1.7 审批

审批单绑定：

- tool name
- tool call id
- 参数 canonical hash
- session id
- run id
- workspace id
- 风险等级
- 请求原因

批准：

- 参数发生变化时失效。
- 一次性消费。
- 执行前再次检查策略。

拒绝：

- 返回给模型可理解的拒绝原因。
- 模型可以调整参数后重新请求。

超时：

- 默认审批等待 120 秒。
- 超时后工具调用取消，Run 暂停或结束，由策略决定。

### 1.8 Sandbox

Node 本地工具必须检查：

- 路径位于 workspace root。
- realpath 不跳出 root。
- `deny_read`。
- `deny_write`。
- `allow_write` 例外。
- 二进制文件不可用文本读取。
- 命令环境移除密钥变量。
- 命令有 timeout 和 kill grace。
- stdout/stderr 有采集上限。

### 1.9 输出截断

两种输出：

- 给模型：控制在上下文预算内，提供继续读取指引。
- 给审计：保留头部、行数、字符数和全文哈希。

## 2. Skill 系统

### 2.1 标准目录

```text
my-skill/
├─ SKILL.md
├─ references/
├─ scripts/
└─ assets/
```

### 2.2 加载顺序

1. 内置 Skill。
2. AgentShow 管理 Skill。
3. 用户 Skill：`~/.agents/skills`。
4. 项目 Skill：`<workspace>/.agents/skills`。

冲突规则：

- 项目级覆盖同名的较低优先级 Skill。
- 名称冲突产生诊断，不静默混用。
- 受信任工作区才加载项目 Skill。

### 2.3 渐进式披露

启动：

- 加载 `name`、`description`、`path`、`source`。
- 写入系统提示词的 Skill 索引。

运行时：

- 模型匹配后读取 `SKILL.md`。
- 用户可显式 `/skill:name`。
- `disable-model-invocation` 只允许显式调用。

### 2.4 管理

UI 展示：

- 名称
- 描述
- 来源
- 路径
- 是否启用
- 是否可信
- 诊断
- 可显式调用

### 2.5 安全

- Skill 属于受信任指令，但不是最高系统策略。
- Skill 中的脚本必须通过工具权限执行。
- 项目 Skill 首次出现时要求信任工作区。
- Skill 不可直接读取 API Key。

## 3. Context 系统

### 3.1 Context 组成

```text
系统安全与工具规则
  + AgentProfile
  + 工作区上下文文件
  + Skill 索引
  + 长期记忆摘要
  + Pi 活动分支
  + 当前用户输入
  + 当前工具结果
```

### 3.2 优先级

1. 平台安全策略。
2. 显式用户设置。
3. 工作区 Agent 配置。
4. Skill 指令。
5. 长期记忆。
6. 会话内容。

外部文档和记忆是参考信息，不允许覆盖安全策略。

### 3.3 上下文预算

配置项：

- 模型 context window。
- system prompt 预算。
- Skill 索引预算。
- Memory digest 预算。
- keep recent tokens。
- reserve tokens。
- tool output 预算。
- audit 截断预算。

### 3.4 压缩

- Pi 自动 compaction。
- FastAPI 只记录压缩事件和前后 token。
- 不自行删除 Pi 原始会话条目。
- 用户可手动触发 compact。

### 3.5 可观测

每次模型请求记录：

- request id
- model id
- message count
- estimated input tokens
- actual usage
- cache tokens
- compaction event
- skill index hash
- memory digest hash

## 4. Memory 系统

### 4.1 记忆分层

| 层 | 内容 | 存储 |
|---|---|---|
| Working Memory | 当前 Run 的临时事实 | Sidecar 内存 |
| Session Memory | 会话历史和分支 | Pi JSONL |
| Project Memory | 项目偏好、决策、长期事实 | SQLite + Markdown/OKF |
| User Memory | 跨项目偏好 | SQLite，默认关闭 |

### 4.2 第一版长期记忆

复用参考项目的 OKF 设计：

- 目录。
- Markdown 概念文件。
- YAML frontmatter。
- `index.md`。
- `log.md`。

概念字段：

```yaml
type: decision
title: Provider 密钥不进入 Pi
description: 上游密钥只由 FastAPI 解密
tags: [security, llm-gateway]
resource: backend/app/llm
generated:
  by: agentshow/1.0
  at: 2026-11-19T12:00:00Z
sources:
  - session_id: sess_...
    message_id: msg_...
```

### 4.3 召回

系统提示词只注入：

- title
- id
- type
- 一句描述

全文由 `memory_get` 按需读取。

### 4.4 写入

- 用户手动添加可直接写入。
- Agent 写入需要审批。
- 必须带来源。
- 冲突时保留两条并标注冲突，不静默覆盖。
- 支持删除和禁用。

### 4.5 检索

第一版：

- 标题、描述、标签、正文关键词。
- SQLite FTS5 可选。

第二版：

- 本地 embedding。
- 向量召回与关键词混合。

不把完整记忆写入每次上下文。

