# 测试结果

## 后端

命令：

```powershell
python -m pytest -q
```

结果：

```text
21 passed
```

覆盖：

- 健康检查。
- 示例会话 Trace。
- 总时长、轮次、调用数。
- ID 查询。
- Provider 密钥掩码。
- 会话创建与数据库初始化。
- 首条消息自动命名。
- 会话手动重命名和删除。
- 示例会话删除后不重新生成。
- Agent Manager Demo 路径。
- Agent Manager Pi 分支桥接。
- Goal Loop Demo 完成路径。
- LLM Gateway Demo 流式响应。
- Event Broker 发布与退订。
- 数据库 JSON 和路由辅助函数。
- 默认 Skill 扫描和正文读取。
- Skill 启停。
- 自定义 Skill 路径加载。
- Skill 上下文注入。
- Word 和 Markdown 文档导入。
- Markdown、Word 和 PDF 导出。
- 附件消息与 Token 速度统计。
- Agent 会话预热接口。

## 后端覆盖率

```text
Required test coverage of 80% reached.
Total coverage: 81.16%
```

## 前端

命令：

```powershell
npm run build
```

结果：

- `vue-tsc --noEmit` 通过。
- Vite 生产构建通过。

## Agent Host

命令：

```powershell
npm run build
```

结果：

- TypeScript 构建通过。

## 浏览器验证

Playwright 验证：

- 桌面 1440 x 900。
- 桌面浅色主题。
- 移动端 390 x 844。
- 对话页、轨迹页和详情检查器均正常。
- 会话重命名和删除交互正常。
- 自动创建 E2E 测试会话。
- Trace 调用数和 Span 详情检查。
- 测试会话删除。
- Skill 选择器、`@skill-name` 提及和路径输入入口。
- 文件导入入口。
- 助手消息 Markdown、Word、PDF 导出按钮。
- Token 使用速度指标。
- 浏览器控制台无错误。

## Pi 集成验证

通过本地 Mock OpenAI-compatible 服务验证：

- FastAPI 内部模型网关。
- Pi Agent Loop。
- `list_files` 工具调用。
- 工具结果回灌模型。
- 第二轮模型回答。
- Trace Span 与 Tool Call 记录。

