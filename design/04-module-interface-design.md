# 模块接口设计

## 1. 输入接口

### 1.1 TraceAdapter

```ts
interface TraceAdapter {
  id: string
  version: string
  label: string
  detect(input: ImportInput): AdapterDetection
  normalize(input: ImportInput): NormalizeResult
}

interface ImportInput {
  fileName?: string
  text: string
  parsed?: unknown
}

interface AdapterDetection {
  matched: boolean
  confidence: number
  reason: string
}

interface NormalizeResult {
  session?: TraceSession
  errors: TraceIssue[]
  warnings: TraceIssue[]
}
```

约束：

- `detect` 不抛普通业务错误，返回置信度和原因。
- `normalize` 不直接写 store 或 IndexedDB。
- adapter 可以保留原始数据，但必须返回统一模型。

### 1.2 字段映射配置

```ts
interface FieldMappingProfile {
  id: string
  name: string
  rootPath?: string
  callListPath: string
  fields: {
    id: string
    roundId?: string
    parentId?: string
    name: string
    summary?: string
    startedAt: string
    endedAt?: string
    category?: string
    status?: string
  }
}
```

映射配置支持保存到本地，便于重复导入同一格式。

## 2. 校验接口

```ts
interface TraceValidator {
  validate(session: TraceSession): ValidationReport
}

interface ValidationReport {
  errors: TraceIssue[]
  warnings: TraceIssue[]
  normalizedSession?: TraceSession
}

interface TraceIssue {
  code: string
  path: string
  message: string
  severity: 'error' | 'warning' | 'info'
}
```

## 3. 分析接口

```ts
interface TraceAnalytics {
  summarize(session: TraceSession): TraceSummary
  groupByRound(session: TraceSession): TraceRoundGroup[]
  findCriticalPath(session: TraceSession): TraceCall[]
  getCallRelations(session: TraceSession, callId: string): CallRelations
}

interface TraceSummary {
  totalDurationMs: number
  activeDurationMs?: number
  roundCount: number
  callCount: number
  errorCount: number
  successRate: number
  tokenTotal?: number
  startedAt: string
  endedAt?: string
}

interface CallRelations {
  parent?: TraceCall
  children: TraceCall[]
  previous?: TraceCall
  next?: TraceCall
}
```

## 4. 查询接口

```ts
interface TraceQuery {
  keyword: string
  roundIds: string[]
  categories: TraceCallCategory[]
  statuses: TraceStatus[]
}

interface QueryEngine {
  apply(session: TraceSession, query: TraceQuery): FilteredTrace
}

interface FilteredTrace {
  calls: TraceCall[]
  matchedCallIds: Set<string>
  hiddenByRoundCount: number
  activeFilterCount: number
}
```

搜索命中范围：

- `name`
- `summary`
- `toolName`
- `model`
- `error.message`
- `inputPreview`
- `outputPreview`

默认不搜索完整 raw JSON，避免高成本和敏感内容意外暴露。

## 5. 时间布局接口

```ts
interface TimeLayoutEngine {
  createDomain(session: TraceSession): TimeDomain
  createScale(domain: TimeDomain, viewport: Viewport): TimeScale
  layoutCalls(calls: TraceCall[], scale: TimeScale): TraceBarLayout[]
  createOverviewBins(calls: TraceCall[], width: number): OverviewBin[]
}

interface TraceBarLayout {
  callId: string
  x: number
  width: number
  lane: TraceCallCategory
  depth: number
}
```

布局层不修改调用数据，只返回绘制坐标。

## 6. 持久化接口

```ts
interface PersistenceGateway {
  listSessions(): Promise<SessionListItem[]>
  getSession(id: string): Promise<TraceSession | undefined>
  saveSession(session: TraceSession): Promise<void>
  deleteSession(id: string): Promise<void>
  clearAll(): Promise<void>
  getPreferences(): Promise<ViewPreferences | undefined>
  savePreferences(preferences: ViewPreferences): Promise<void>
}
```

保存策略：

- 会话正文与最近打开列表分开存储。
- 大字段 raw 可单独存表和延迟加载。
- 删除会话必须同时删除其 raw 数据。

## 7. Stores

### 7.1 sessionStore

职责：

- 当前会话。
- 会话列表。
- 加载、导入、删除状态。
- 错误状态。

### 7.2 selectionStore

职责：

- 当前选中调用。
- hover 调用。
- 选中来源，用于总览与瀑布联动。

### 7.3 queryStore

职责：

- 关键词。
- 轮次筛选。
- 类型筛选。
- 状态筛选。
- 计算后过滤结果。

### 7.4 viewStore

职责：

- 主题。
- 密度。
- 左栏和右栏展开状态。
- 当前视图模式。
- 时间缩放。

## 8. UI 事件契约

| 事件 | 发起方 | 接收方 | 结果 |
|---|---|---|---|
| `call:select` | 总览轨道、瀑布行 | 全工作台 | 同步选中和详情 |
| `call:hover` | 总览轨道、瀑布行 | 全工作台 | 临时高亮 |
| `round:focus` | 轮次视图、筛选 | 瀑布和总览 | 滚动到轮次 |
| `filter:change` | 工具栏 | 查询和画布 | 更新过滤结果 |
| `import:complete` | 导入向导 | 会话导航和路由 | 打开新会话 |
| `theme:change` | 设置或顶栏 | 根节点 | 切换 token |

## 9. 路由契约

- 选中调用写入 `call` 查询参数，支持分享本地会话视图。
- 筛选条件可写入查询参数，但会话数据本身不入 URL。
- 刷新页面后从本地库恢复会话。
- 找不到本地会话时显示可恢复空状态。

## 10. 错误契约

| 层 | 错误表现 |
|---|---|
| adapter | 导入向导内联错误和可映射字段提示 |
| validator | 错误列表，显示 JSON path 和建议修复 |
| persistence | 顶部持久化警告，降级到内存模式 |
| visualization | 行级占位，不阻断其他调用 |
| route | 会话不存在或本地数据已删除 |

