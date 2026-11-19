# 模块拆分

## 1. 拆分原则

- 数据输入与可视化解耦。
- adapter 与业务 UI 解耦。
- 派生指标只通过数据层计算。
- 主画布与详情检查器通过选中状态联动。
- 本地持久化不侵入会话模型。

## 2. 模块清单

| 模块 | 标识 | 职责 | 关键输出 |
|---|---|---|---|
| 应用外壳 | `M01-app-shell` | 顶栏、三栏布局、主题、全局状态 | AppShell |
| 会话导航 | `M02-session-center` | 打开示例、导入、最近会话、删除 | SessionNavigator |
| 轨迹输入 | `M03-trace-ingestion` | adapter 检测、归一化、字段映射 | TraceAdapterRegistry |
| 轨迹模型 | `M04-trace-model` | 类型、校验、时间与关系不变量 | TraceSession v1 |
| 指标分析 | `M05-trace-analytics` | 总时长、轮次、调用数、错误率、活跃时间 | TraceSummary |
| 轨迹画布 | `M06-trace-canvas` | 时间比例尺、总览轨道、瀑布行 | TraceWorkbench |
| 调用详情 | `M07-call-inspector` | 概览、预览、原始内容、关联跳转 | CallInspector |
| 检索筛选 | `M08-trace-query` | 搜索、类型、状态、轮次筛选 | TraceViewState |
| 本地存储 | `M09-local-store` | IndexedDB、最近会话、视图偏好 | PersistenceGateway |
| 通用组件 | `M10-design-system` | 按钮、标签、空状态、对话框、快捷键提示 | UI primitives |
| 质量保障 | `M11-quality` | 单元、组件、E2E、视觉回归、可访问性 | Test suite |

## 3. 业务功能映射

| 业务功能 | 模块 |
|---|---|
| 打开示例 | M02、M03、M09 |
| 导入 JSON | M02、M03、M04 |
| 总览指标 | M04、M05 |
| 时间轴和瀑布 | M05、M06 |
| 轮次分析 | M05、M06、M08 |
| 调用详情 | M06、M07 |
| 搜索筛选 | M08 |
| 响应式和主题 | M01、M10 |
| 隐私与脱敏 | M03、M09、M11 |

## 4. 依赖关系

```text
M01 App Shell
├─ M02 Session Center
│  ├─ M03 Trace Ingestion
│  └─ M09 Local Store
├─ M06 Trace Canvas
│  ├─ M04 Trace Model
│  ├─ M05 Trace Analytics
│  └─ M08 Trace Query
├─ M07 Call Inspector
│  └─ M04 Trace Model
└─ M10 Design System

M11 Quality 横切所有模块
```

## 5. 实施边界

- `M03` 只负责输入转换，不计算 UI 展示格式。
- `M05` 只返回数据结果，不包含组件状态。
- `M06` 不直接读取原始 import 数据。
- `M07` 不重复计算指标，只读取选中调用和派生摘要。
- `M09` 不保存不必要的敏感原文，只保存用户明确导入的数据。

