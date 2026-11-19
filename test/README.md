# JAgent 工程测试

## 目录

```text
test/
├─ e2e/
│  └─ jagent.e2e.mjs
├─ reports/
├─ run-tests.ps1
└─ README.md
```

## 测试范围

### 后端

- 健康检查。
- 示例数据。
- Trace 汇总。
- Trace ID 查询。
- Provider API Key 掩码。
- 会话创建。
- 首条消息自动命名。
- 会话手动重命名。
- 会话删除。
- 示例会话删除后不重新生成。
- 默认 Skill 扫描。
- Skill 正文读取和启停。
- 自定义 Skill 路径加载。
- Skill 上下文注入。
- 文档导入和附件消息。
- Markdown、Word、PDF 导出。
- Token 使用速度。
- 会话预热接口。
- Python 覆盖率。
- 后端行覆盖率门禁：`80%`。

### Agent Host

- TypeScript 编译检查。

### 前端

- Vue TypeScript 类型检查。
- Vite 生产构建。

### 浏览器 E2E

- JAgent 品牌渲染。
- 新建测试会话。
- Demo Agent 对话。
- Trace 数据展示。
- Span 选择与详情检查器。
- 会话重命名。
- 会话删除。
- Skill 选择器和 `@skill-name` 提及。
- 文件导入入口。
- Markdown、Word、PDF 导出按钮。
- Token 使用速度指标。
- 移动端布局。
- 浏览器控制台错误检查。

## 执行

```powershell
cd AgentShow\test
.\run-tests.ps1
```

脚本会自动：

1. 检查或启动本地 FastAPI。
2. 执行后端 Pytest 和覆盖率。
3. 构建 Agent Host。
4. 构建前端。
5. 执行 Playwright E2E。
6. 把结果写入 `test/reports/`。

如果服务原本已运行，测试结束后不会关闭它。

