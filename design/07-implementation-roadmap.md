# 实施路线

## 1. 当前阶段

当前只完成架构设计，不生成业务代码和脚手架。

## 2. Skill 使用顺序

### 第 1 步：PM

目标：

- 把本设计中的需求拆成工作包。
- 生成正式 TASK 文件。
- 明确每个 TASK 的输入、输出和验收门禁。

建议命令：

```text
/software-delivery-pm
```

输入：

- `requirements/01-assignment-requirements.md`
- `design/05-frontend-ux-design.md`
- `design/07-implementation-roadmap.md`

### 第 2 步：架构师复核

目标：

- 确认架构假设。
- 确认 adapter 首批范围。
- 确认数据模型没有遗漏。
- 生成前端脚手架。

建议命令：

```text
/software-delivery-architect --arch=monolith
```

该步骤应在用户明确同意开始实现后执行。

### 第 3 步：前端开发

目标：

- 实现 Vue 工作台。
- 实现示例数据和导入流程。
- 完成时间轴、详情、筛选和响应式。

建议命令：

```text
/software-delivery-frontend
```

建议按 TASK 顺序执行，不要一次性实现全部功能。

### 第 4 步：测试

目标：

- 执行单元、组件、E2E、可访问性和视觉回归。
- 输出覆盖率与验收报告。

建议命令：

```text
/software-delivery-tester
```

### 第 5 步：架构师最终审查

目标：

- 检查实现与设计一致性。
- 检查代码质量。
- 检查 P0 需求覆盖率。

建议命令：

```text
/software-delivery-architect
```

### 第 6 步：运维，可选

目标：

- 生成静态构建说明。
- 可选生成 Docker 或演示站点配置。

建议命令：

```text
/software-delivery-ops
```

## 3. 建议 TASK 顺序

| TASK | 内容 | 依赖 | 主要产物 |
|---|---|---|---|
| TASK-001 | 项目基线与设计系统 | 无 | Vue 项目、token、布局壳 |
| TASK-002 | TraceSession v1 与校验 | TASK-001 | 类型、schema、validator |
| TASK-003 | 标准 adapter 与示例数据 | TASK-002 | 示例会话、adapter registry |
| TASK-004 | 指标与查询 | TASK-002 | summary、round groups、query |
| TASK-005 | 总览轨道 | TASK-003、TASK-004 | overview lanes |
| TASK-006 | 瀑布列表与缩放 | TASK-005 | timeline rows、zoom |
| TASK-007 | 详情检查器 | TASK-006 | overview、preview、raw tabs |
| TASK-008 | 导入向导与字段映射 | TASK-003 | import flow |
| TASK-009 | 持久化与设置 | TASK-002 | IndexedDB、theme、density |
| TASK-010 | 响应式与可访问性 | TASK-006、TASK-007 | mobile drawers、keyboard |
| TASK-011 | 测试、截图、录屏、README | 全部 | 验收包 |

## 4. 里程碑

### M1 数据可用

完成 TASK-001 至 TASK-004。

验收：

- 标准示例可加载。
- 总时长、轮次、调用数正确。
- 查询结果稳定。

### M2 轨迹可读

完成 TASK-005 至 TASK-007。

验收：

- 作业五全部 P0 字段可见。
- 时间和层级关系正确。

### M3 通用可演示

完成 TASK-008 至 TASK-011。

验收：

- 能导入标准 JSON。
- 移动端和深浅主题可用。
- README、截图、录屏和说明文档齐备。

## 5. 交付清单

```text
AgentShow/
├─ deliverables/
│  └─ frontend/
├─ requirements/
├─ design/
├─ plans/
├─ check/
├─ docs/
│  └─ solution-summary.md
└─ screenshots/
```

最终还需：

- README 运行说明。
- 示例数据入口。
- 至少一张桌面截图。
- 关键交互录屏。
- 轨迹信息、设计思路和实现方式说明。

## 6. 风险控制

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 主视图过度复杂 | 首屏无法直接找到总时长和轮次 | 先完成 P0 只读视图 |
| 通用 adapter 成本过高 | 每种格式都改 UI | 严格通过统一模型扩展 |
| 密集数据卡顿 | 1,000 条调用滚动掉帧 | 启用虚拟化和总览分桶 |
| 移动端信息挤压 | 文本和条形重叠 | 单列、抽屉和水平滚动 |
| 视觉过度模仿参考图 | 缺少自有分析与通用能力 | 保留结构，重做信息层级和交互 |
| 敏感数据进入交付物 | 示例出现路径或 token | 自动扫描和人工复核 |

