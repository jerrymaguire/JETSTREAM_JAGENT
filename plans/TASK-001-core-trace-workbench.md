# TASK-001 核心轨迹工作台

## 目标

实现作业五的核心可演示路径：加载一条包含多个轮次和调用的示例会话，并在三栏工作台中展示总时长、轮次、调用时间、持续时长和内容摘要。

## 输入

- `requirements/01-assignment-requirements.md`
- `design/02-system-architecture.md`
- `design/03-trace-data-model.md`
- `design/04-module-interface-design.md`
- `design/05-frontend-ux-design.md`

## 范围

### 包含

- Vue 3 + TypeScript + Vite 项目基线。
- 设计 token 和 AppShell。
- `TraceSession v1` 类型和 validator。
- 示例数据 adapter。
- 总览轨道。
- 瀑布时间轴。
- 调用详情检查器。
- KPI 摘要。
- 基础搜索和类型、状态筛选。

### 不包含

- 实时 Agent 接入。
- 云端存储和账号。
- 通用字段映射的完整高级交互。
- 历史会话同步。

## 产物

- `deliverables/frontend/`
- 示例会话 JSON。
- 运行中的工作台。
- 单元测试、组件测试和至少一条 E2E。
- 初步 README。

## 验收

- 页面显示总运行时长。
- 页面显示轮次数量。
- 每个调用显示开始时间、持续时长和摘要。
- 时间条位置与调用开始时间一致。
- 选择调用后详情面板正确联动。
- 1440px 桌面分辨率无文本重叠。
- `pnpm build` 和测试命令通过。

## 后续任务

- TASK-002：通用导入和字段映射。
- TASK-003：父子关系、错误详情和轮次增强。
- TASK-004：响应式、可访问性、主题和视觉回归。
- TASK-005：README、截图、录屏和交付说明。

