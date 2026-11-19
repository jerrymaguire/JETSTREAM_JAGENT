# AgentShow 设计上下文

## 1. 事实表

### 1.1 业务功能

| 功能 | 概述 |
|---|---|
| 会话加载 | 打开内置示例或导入本地 Agent 轨迹 |
| 轨迹归一化 | 将不同来源格式转换为统一轨迹模型 |
| 会话总览 | 展示总运行时长、轮次、调用数、状态和 token |
| 时间轴总览 | 用轨道展示全部调用在统一时间尺度上的分布 |
| 调用瀑布 | 逐行展示每次调用的时间位置、层级、持续时长和摘要 |
| 轮次分析 | 按轮次分组、筛选、跳转和汇总 |
| 调用详情 | 查看概览、预览、原始内容、父子关系和时间字段 |
| 搜索筛选 | 按关键词、类型、状态、轮次快速定位 |
| 本地存储 | 保存最近打开的会话和用户视图偏好 |
| 导出演示 | 提供示例数据入口，支持截图和录屏交付 |

### 1.2 实体

| 实体 | 关键字段 |
|---|---|
| TraceSession | id、title、agent、model、startedAt、endedAt、status、source |
| TraceRound | id、index、startedAt、endedAt、status、summary |
| TraceCall | id、roundId、parentId、category、name、startedAt、endedAt、durationMs、status、summary |
| TraceTokenUsage | input、output、reasoning、total、cost |
| TraceError | code、message、stackPreview |
| ImportProfile | id、adapterId、fieldMapping、createdAt |
| ViewPreferences | theme、density、visibleColumns、zoomMode |

### 1.3 角色与权限

| 角色 | 权限 |
|---|---|
| 本地用户 | 导入、查看、筛选、删除本地会话 |

首版无登录、无远程权限、无多人协作。

### 1.4 业务流程

#### 加载会话

1. 用户打开示例或选择本地 JSON。
2. 系统检测 adapter。
3. adapter 转换原始数据。
4. 校验器检查必填字段、时间和关系。
5. 系统生成统一轨迹模型和派生指标。
6. 工作台展示会话。

#### 分析一次调用

1. 用户在总览轨道或瀑布行选择调用。
2. 系统同步选中状态。
3. 详情检查器显示调用摘要、时间、状态、token 和原始数据。
4. 用户可跳转父调用、同轮次调用或错误调用。

#### 按轮次分析

1. 用户切换到轮次视图或选择轮次筛选。
2. 系统按轮次聚合调用。
3. 时间轴显示轮次区间和轮内调用。
4. 用户可通过折叠组快速浏览。

### 1.5 输入输出要素

| 类别 | 输入 | 输出 |
|---|---|---|
| 会话 | 标准 JSON 或 adapter 可识别格式 | TraceSession |
| 轮次 | 轮次序号、时间、摘要 | TraceRound |
| 调用 | 类型、名称、开始、结束、状态、内容 | TraceCall |
| 指标 | 时间戳、token、状态 | 总时长、轮次、调用数、错误数、token 总量 |
| 视图 | 搜索词、筛选条件、选中项 | 过滤后的轨迹与详情 |

### 1.6 性能指标

- 示例数据：至少 500 次调用、10 个轮次。
- 设计上限：5,000 次调用。
- 首屏可用：2.5 秒内。
- 交互反馈：100 毫秒内开始响应。
- 页面不因字体、时间轴或详情面板造成布局跳动。

### 1.7 外部系统

- 本地文件系统：通过浏览器文件选择器读取 JSON。
- 浏览器 IndexedDB：保存本地会话和偏好。
- 无远程 API、无服务端、无第三方埋点。

## 2. 模块与决策摘要

- 模块边界见 `_module-split.md`。
- 关键技术决策见 `_technical-decisions.md`。
- 应用形态为单体前端工作台。
- 主视图为三栏：会话导航、轨迹画布、调用详情。
- 所有数据先归一化为 `TraceSession v1`。

## 3. 跨文档引用索引

| 概念 | 统一名称 | 定义位置 |
|---|---|---|
| 根对象 | `TraceSession` | `03-trace-data-model.md` |
| 轮次 | `TraceRound` | `03-trace-data-model.md` |
| 调用 | `TraceCall` | `03-trace-data-model.md` |
| 状态 | `TraceStatus` | `03-trace-data-model.md` |
| 类型 | `TraceCallCategory` | `03-trace-data-model.md` |
| 导入器 | `TraceAdapter` | `04-module-interface-design.md` |
| 指标计算 | `TraceAnalytics` | `04-module-interface-design.md` |
| 主画布 | `TraceWorkbench` | `05-frontend-ux-design.md` |

## 4. 文档进度看板

| 文档 | 状态 |
|---|---|
| 01-tech-stack | 已完成 |
| 02-system-architecture | 已完成 |
| 03-trace-data-model | 已完成 |
| 04-module-interface-design | 已完成 |
| 05-frontend-ux-design | 已完成 |
| 06-test-and-acceptance-design | 已完成 |
| 07-implementation-roadmap | 已完成 |

## 5. 待确认

- 第 4 点用户要求未完整输入，保留为空位。
- 首批是否必须接入某一种真实 Agent 导出格式，待实现前确认。
- 默认主题建议跟随系统，可手动切换；最终偏好可在实现阶段确认。

