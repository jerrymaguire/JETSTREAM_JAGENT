# 系统架构

## 1. 架构概览

AgentShow 采用单体、纯前端、分层架构。

```text
File / Demo Input
       |
       v
TraceAdapterRegistry
       |
       v
Canonical TraceSession v1
       |
       +--> Validator
       +--> Analytics
       +--> Query / Filter
       |
       v
Pinia Application State
       |
       +--> Session Navigator
       +--> Trace Workbench
       +--> Call Inspector
       |
       v
IndexedDB Local Store
```

## 2. 分层

### 2.1 输入层

- 内置示例 JSON。
- 本地文件选择。
- 粘贴 JSON。
- 导入向导中的字段映射。

### 2.2 归一化层

- adapter 检测。
- adapter 转换。
- Zod 校验。
- 警告和错误汇总。
- 原始数据保留。

### 2.3 领域层

- `TraceSession`、`TraceRound`、`TraceCall`。
- 时间不变量和父子关系。
- 派生指标。
- 查询和筛选。

### 2.4 应用层

- Pinia stores。
- 路由状态。
- 本地持久化。
- 主题、密度和视图偏好。

### 2.5 表现层

- 应用外壳。
- 会话导航。
- 总览轨道。
- 瀑布时间轴。
- 调用详情检查器。
- 导入向导和错误状态。

## 3. 页面路由

| 路由 | 页面 | 说明 |
|---|---|---|
| `/` | Workbench | 打开最近会话或示例 |
| `/import` | Import Wizard | 导入、检测、映射、校验 |
| `/session/:id` | Session Workbench | 查看指定会话 |
| `/settings` | Settings | 主题、密度、本地数据管理 |

查询参数：

- `round`：当前轮次。
- `call`：当前选中调用。
- `type`：调用类型筛选。
- `status`：状态筛选。
- `q`：搜索关键词。

## 4. 目录建议

```text
deliverables/frontend/
├─ src/
│  ├─ app/
│  │  ├─ App.vue
│  │  ├─ router.ts
│  │  └─ providers/
│  ├─ components/
│  │  ├─ layout/
│  │  ├─ trace/
│  │  ├─ inspector/
│  │  ├─ import/
│  │  └─ common/
│  ├─ features/
│  │  ├─ adapters/
│  │  ├─ trace-model/
│  │  ├─ analytics/
│  │  ├─ query/
│  │  └─ persistence/
│  ├─ stores/
│  ├─ styles/
│  │  ├─ tokens.css
│  │  ├─ reset.css
│  │  └─ utilities.css
│  ├─ data/
│  │  └─ sample-session.json
│  ├─ test/
│  └─ main.ts
├─ tests/
│  └─ e2e/
├─ package.json
└─ vite.config.ts
```

## 5. 核心数据流

### 5.1 导入

1. `ImportWizard` 接收文件或文本。
2. `TraceAdapterRegistry.detect` 选择 adapter。
3. adapter 返回 `NormalizeResult`。
4. `TraceValidator` 返回 errors 和 warnings。
5. 无阻断错误时写入 IndexedDB。
6. 系统跳转到 `/session/:id`。

### 5.2 展示

1. `sessionStore` 读取会话。
2. `TraceAnalytics` 计算摘要。
3. `queryStore` 应用搜索和筛选。
4. `TraceWorkbench` 计算时间比例尺和行布局。
5. `selectionStore` 保存选中调用。
6. `CallInspector` 从同一模型读取详情。

### 5.3 时间定位

1. 会话时间范围 = 最早开始时间到最晚结束时间。
2. 每行条形位置由开始时间和总范围映射。
3. 宽度由持续时长映射，并保留最小可点击宽度。
4. 缩放只改变可见域，不改变实际时间数据。
5. 总览轨道显示完整域，并通过窗口框表示当前可见域。

## 6. 关键算法

### 6.1 总运行时长

```text
sessionDuration = max(call.endedAt) - min(call.startedAt)
```

若调用缺失有效结束时间，使用会话 `endedAt`；仍缺失时标记数据不完整。

### 6.2 轮次

```text
roundCount = distinct valid roundId count
```

若输入只提供 `roundIndex`，按最大序号计算，并报告缺口 warning。

### 6.3 活跃时长

对所有调用区间求并集，得到非重叠活跃时长。该指标是加分项，不与总运行时长混淆。

### 6.4 父子关系

- `parentId` 必须指向同一会话内的调用。
- 环形关系为阻断错误。
- UI 按 parent chain 计算缩进层级。
- 总览轨道不展开完整树，只显示调用类别泳道。

### 6.5 密集聚合

当同一像素区间内条形重叠过多时：

- 总览轨道按时间桶聚合数量和失败数。
- 主瀑布仍保留单调用行。
- 仅在用户放大后恢复可辨认的单条汇总条形。

## 7. 性能设计

- 会话加载后只做一次归一化和基础校验。
- 筛选结果使用 memoized selector。
- 瀑布行虚拟化。
- 时间比例尺和行高在缩放时复用。
- 文本预览限制长度，原始 JSON 按需展开。
- IndexedDB 批量写入，避免逐行事务。

## 8. 错误与降级

| 错误 | 处理 |
|---|---|
| 无法识别格式 | 进入手动字段映射 |
| 必填字段缺失 | 阻止导入，显示具体路径 |
| 时间不合法 | 阻止导入或标记为不可绘制调用 |
| 父调用缺失 | warning，条目显示为孤立调用 |
| 轮次缺口 | warning，不阻断 |
| 过大文件 | 提示预计调用数量，建议分批导入 |
| IndexedDB 不可用 | 改为内存模式，并提示关闭页面会丢失数据 |

## 9. 隐私边界

- 所有解析在浏览器内完成。
- 不请求远程 API。
- 不加载远程字体。
- 示例数据必须通过敏感字段扫描。
- 原始内容查看默认折叠，并显示脱敏提示。

## 10. 架构结论

该架构能覆盖作业五全部 P0 要求，并为通用 Agent adapter、轮次分析、父子关系和错误分析保留清晰扩展点。

