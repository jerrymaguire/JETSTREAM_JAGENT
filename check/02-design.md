# 完全体 Agent 设计交付检查

## 产物检查

- [x] 参考代码评估
- [x] 作业五需求
- [x] 完全体 Agent 功能需求
- [x] 对话内目标循环
- [x] 关键规则提取
- [x] 产品设计
- [x] 系统架构
- [x] Pi Agent Runtime
- [x] Goal Loop
- [x] Skill 生命周期
- [x] 单 Agent Evaluation Harness
- [x] FastAPI 接口
- [x] 统一 LLM Gateway
- [x] API Key 管理
- [x] 工具与审批
- [x] Skill
- [x] Context
- [x] Memory
- [x] Session、Trace 和数据库
- [x] 前端工作台
- [x] 安全与部署
- [x] 实施路线
- [x] 工作包
- [x] 明确只设计不实现

## 一致性检查

- 系统名称统一为 `AgentShow`。
- Agent Loop 统一由 Pi 负责。
- 控制平面统一为 FastAPI。
- 模型请求统一经过 FastAPI LLM Gateway。
- Pi 不持有上游 API Key。
- 工具调用统一经过 Tool Governance。
- 会话事实源为 Pi JSONL。
- Trace 事实源为 SQLite 事件和 Span。
- 当前范围不包含 Multi-Agent 和 Subagent。

## 当前停止线

未创建代码、脚手架、依赖锁文件和运行产物。

## 进入实现前的待确认

1. 确认模块化单体 FastAPI + Pi Sidecar。
2. 确认第一版 Provider 范围。
3. 确认长期记忆是否属于第一版。
4. 确认是否需要公网访问。

