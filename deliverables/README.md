# AgentShow 可运行实现

## 运行环境

- Node.js 22 或更高版本
- Python 3.12 或更高版本
- 现代 Chrome、Edge 或其他 Chromium 浏览器

## 1. 安装

```powershell
cd D:\wj\projects\AI\GeekAgent\Week5\AgentShow\deliverables\agent-host
npm install
npm run build

cd ..\frontend
npm install
npm run build

cd ..\backend
python -m pip install -r requirements.txt
```

## 2. 启动

```powershell
cd D:\wj\projects\AI\GeekAgent\Week5\AgentShow\deliverables\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开：

`http://127.0.0.1:8000`

也可以从 AgentShow 根目录运行：

```powershell
.\run.ps1
```

## 3. 使用方式

### 示例轨迹

页面首次打开会自动选择“支付文档整理与回归检查”示例。

点击“轨迹”可以查看：

- 总运行时长。
- 对话轮次。
- 调用数、错误数和 Token。
- 每次调用的开始时间、持续时长和摘要。
- 调用类型、状态和父子关系。
- Span ID、Tool Call ID、Run ID。
- 工具参数和输出预览。

### 新对话

点击“新建对话”，可以直接使用 Demo Agent。

配置真实模型：

1. 点击右上角 `API Keys`。
2. 添加 Provider。
3. 填写 Base URL、模型 ID 和 API Key。
4. 测试连接。
5. 新建对话并发送消息。

### Goal Loop

点击“设定目标”：

1. 输入目标。
2. 每行填写一条完成标准。
3. 设置最大迭代轮次。
4. 点击“启动 Goal Loop”。

Demo 模式会完成一轮演示。真实 Provider 模式会启动 Pi Agent，并通过 `finish_goal` 工具报告每轮状态。

## 4. 已实现能力

- 新建对话、多会话、多轮交流。
- Demo Agent 与 Pi Agent 两种运行模式。
- 对话流式输出。
- Goal Loop 与 GoalIteration。
- 真实 Pi Agent Tool Loop。
- 文件读取、文件写入、文件列表、文本搜索和命令执行工具。
- OpenAI-compatible Provider 和加密 API Key。
- Trace 事件、Span、Tool Call 和 Checkpoint。
- Trace 总览轨道、瀑布时间轴和详情检查器。
- 按 `session_id`、`run_id`、`span_id`、`tool_call_id` 查询。
- 桌面与移动端布局。
- 浅色与深色主题。

## 5. 架构

```text
Vue 3 Workbench
      |
      | REST + WebSocket
      v
FastAPI Control Plane
  ├─ Sessions / Messages
  ├─ Goals
  ├─ Providers / API Key Vault
  ├─ LLM Gateway
  ├─ Trace + Checkpoints
  └─ Pi Process Manager
          |
          | JSONL stdin/stdout
          v
Pi Agent Host
  ├─ Pi Agent Loop
  ├─ Tool Calls
  └─ Streaming Events
          |
          | internal OpenAI-compatible API
          v
FastAPI LLM Gateway
          |
          v
DeepSeek / OpenAI-compatible Provider
```

## 6. 验证

```powershell
cd D:\wj\projects\AI\GeekAgent\Week5\AgentShow\deliverables\backend
python -m pytest -q

cd ..\frontend
npm run build

cd ..\agent-host
npm run build
```

截图位于：

`D:\wj\projects\AI\GeekAgent\Week5\AgentShow\screenshots`

