# 完全体 Agent 需求检查

## 需求统计

- 作业硬性要求：11 项
- 完全体 Agent 功能：63 项
- 目标循环需求：12 项
- Skill 生命周期需求：9 项
- 单 Agent 评测需求：14 项
- 非功能需求：10 项
- 关键控制规则：28 项

## 覆盖检查

- [x] 对话与会话
- [x] 目标驱动循环
- [x] Skill 生命周期
- [x] Pi Agent Loop
- [x] 统一 LLM Gateway
- [x] API Key 管理
- [x] 工具调用
- [x] Skill 加载
- [x] Context
- [x] Memory
- [x] 实时和历史 Trace
- [x] 单 Agent Evaluation Harness
- [x] 作业五轨迹图
- [x] 安全与部署

## 关键决策

- Pi 使用 RPC Sidecar，而不是重写 Agent Loop。
- FastAPI 作为控制平面和模型网关。
- Vue 作为用户工作台。
- SQLite + Pi JSONL 双层存储。
- 工具全部经过统一治理。

## 待确认

1. 是否确认模块化单体 FastAPI + Pi Sidecar。
2. Anthropic 是否属于第一版必达。
3. 长期记忆是否属于第一版必达。
4. 是否需要公网访问和账号系统。

