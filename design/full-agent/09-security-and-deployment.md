# 安全与部署设计

## 1. 威胁模型

主要风险：

- API Key 泄漏。
- Agent 执行危险命令。
- 路径穿越。
- 项目 Skill 恶意指令。
- Prompt Injection。
- 工具结果包含敏感信息。
- Trace 保存完整请求内容。
- 本地服务被其他进程访问。
- Provider 自定义 URL 导致 SSRF。

## 2. 安全边界

### FastAPI

- 默认绑定 `127.0.0.1`。
- 用户 API 可选本地密码。
- 内部 API 使用短期 service token。
- CORS 默认关闭。
- Provider Base URL 由用户显式添加和信任。

### Pi Sidecar

- 不持有上游 API Key。
- 只持有 session 级内部 token。
- 只访问内部 FastAPI。
- 运行在独立子进程。
- 标准输出仅用于 RPC 协议，日志写 stderr。

### Workspace

- 工具限制在 workspace root。
- realpath 检查防止符号链接逃逸。
- deny_read / deny_write。
- 命令去除密钥环境变量。
- 命令超时和输出上限。

## 3. API Key

- 只在前端提交时短暂出现。
- 传输要求 HTTPS 或 localhost。
- 数据库仅存密文。
- 前端永远不接受完整密钥回显。
- 日志和 Trace 有统一 redaction。

## 4. Prompt Injection

外部文件、网页和 RAG 内容视为不可信：

- 不作为系统指令。
- 与系统策略和开发者配置分层显示。
- 工具输出中标注来源。
- 高风险工具始终走策略和审批，不因文档指令而放行。

## 5. Skill 信任

- 用户目录 Skill 由用户主动管理。
- 项目 Skill 随工作区来源变化。
- 首次打开新项目显示信任提示。
- 信任只对当前 workspace root 生效。
- Skill 变更后可要求重新扫描。

## 6. 工具审批

必须审批：

- 写入文件。
- apply patch。
- 执行任意命令。
- 修改记忆。
- 外发网络请求，P1。

批准绑定参数指纹，不能用于同一工具的另一个参数。

## 7. 数据脱敏

敏感键：

- `api_key`
- `apikey`
- `token`
- `secret`
- `password`
- `authorization`
- `cookie`

规则：

- 日志中替换为 `***`。
- Trace 中保存掩码。
- 原始请求只保留哈希或安全片段。
- 错误响应不包含上游 Authorization。

## 8. SSRF 防护

自定义 Provider：

- 只允许 HTTP 和 HTTPS。
- 禁止 file、gopher、ftp。
- 禁止 link-local 和云元数据地址。
- 默认允许 loopback，因为 Ollama 需要本地端点。
- 远程地址需要用户显式信任。
- 每次重定向重新校验目标。

## 9. 部署形态

### 开发

```text
pnpm dev
uvicorn app.main:app --reload
node agent-host
```

FastAPI 自动启动 Sidecar，不需要单独运行。

### 生产

- 前端构建为静态资源。
- FastAPI 提供静态文件和 API。
- Node 与 Pi CLI 随应用分发。
- SQLite 和数据目录位于用户数据目录。
- 默认打开 `http://127.0.0.1:<port>`。

### Docker，可选

单容器运行：

- Python 3.12
- Node.js 22
- 构建后的 Vue
- Pi CLI

工作区和数据目录通过 volume 挂载。

## 10. 端口

| 服务 | 默认端口 | 可见性 |
|---|---|---|
| FastAPI 用户 API | 8000 | localhost |
| FastAPI 内部 API | 8000 | localhost |
| Vite 开发 | 5173 | localhost |

## 11. 启动顺序

1. FastAPI 启动。
2. 加载数据库和迁移。
3. 初始化 CredentialVault。
4. 校验应用数据目录权限。
5. 启动 Sidecar Manager。
6. 提供前端。
7. 用户创建会话后按需启动 Pi。

## 12. 关闭顺序

1. 停止接收新消息。
2. 中止活跃 Run。
3. 等待 Sidecar 保存会话。
4. 关闭 SQLite WAL。
5. 退出进程。

## 13. 备份

需要备份：

- `app.db`
- sessions JSONL
- skills
- memory
- 配置

不需要备份：

- 临时日志。
- node_modules。
- build cache。

备份中可能包含对话内容，导出前必须提示隐私风险。

