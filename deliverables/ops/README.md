# 运维说明

当前提交使用本地单机运行方式：

```powershell
.\run.ps1
```

服务默认只监听 `127.0.0.1:8000`。

运行数据：

- SQLite：`data/agentshow.db`
- 主密钥：`data/secrets/master.key`
- Agent 工作区：`workspace/`
- 日志：`data/*.log`

生产或容器部署前需要补充：

- HTTPS 和用户认证。
- 数据目录持久化。
- Node.js 与 Python 双运行时镜像。
- 日志轮转。
- 主密钥使用系统 Keyring 或外部 Secret Manager。

