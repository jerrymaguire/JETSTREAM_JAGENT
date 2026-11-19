# WP-004 会话与对话 API

## 1. 目标

提供多会话、多消息、流式事件和模型切换。

## 2. 范围

- 包含：会话 CRUD、消息发送、事件订阅、模型切换、重命名和恢复。
- 不包含：完整 fork/clone UI。

## 3. 关键规则

- 一个会话同时只有一个 active Run。
- Pi JSONL 是消息事实源。
- SQLite 只保存索引和投影。
- WebSocket 支持 `after_seq` 回放。

## 4. 主要接口

| 方法 | 路径 |
|---|---|
| GET/POST | `/api/v1/sessions` |
| GET/PATCH/DELETE | `/api/v1/sessions/{id}` |
| POST | `/api/v1/sessions/{id}/messages` |
| POST | `/api/v1/sessions/{id}/abort` |
| WS | `/api/v1/ws/sessions/{id}` |

## 5. 验收

- [ ] 新建会话可加载。
- [ ] 消息可流式显示。
- [ ] 断线后可回放事件。
- [ ] 会话重启后恢复。
- [ ] 模型切换写入事件。

## 6. 负责角色

- 后端开发
- 前端开发

