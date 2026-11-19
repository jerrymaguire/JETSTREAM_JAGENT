# 技术栈

## 1. 运行环境

| 项目 | 选型 | 说明 |
|---|---|---|
| Node.js | 22 LTS | 开发与构建环境 |
| 包管理器 | pnpm | 快速、锁文件稳定 |
| 浏览器 | 最新两个主版本 | Chrome、Edge、Firefox、Safari |

## 2. 前端框架

| 类别 | 技术 | 用途 |
|---|---|---|
| 框架 | Vue 3 | 页面与组件 |
| 语言 | TypeScript | 数据契约和类型安全 |
| 构建 | Vite | 开发服务器和静态构建 |
| 路由 | Vue Router | 工作台、导入向导、设置 |
| 状态 | Pinia | 会话、选中、筛选、偏好 |
| 组合工具 | VueUse | 键盘、存储、媒体查询等通用能力 |

## 3. UI 与可视化

| 类别 | 技术 | 用途 |
|---|---|---|
| 基础组件 | Element Plus | 输入、按钮、标签、弹窗、抽屉、提示 |
| 图标 | Lucide Vue Next | 统一图标族 |
| 时间比例尺 | d3-scale、d3-time-format | 时间轴刻度和格式化 |
| 虚拟列表 | @tanstack/vue-virtual | 大量调用行 |
| 可视化层 | SVG + DOM + CSS | 总览轨道、瀑布条、连线、选中态 |

不选择通用图表库作为主视图，原因如下：

- 轨迹需要高密度行、重叠、缩放、筛选和层级同时工作。
- 详情检查器需要与每一行共享 DOM 可访问语义。
- 通用甘特图对自定义分组、轮次轨道和可访问导航支持有限。

## 4. 数据与持久化

| 类别 | 技术 | 用途 |
|---|---|---|
| 校验 | Zod | JSON 导入运行时校验 |
| 本地数据库 | Dexie | IndexedDB 封装 |
| 日期 | 原生 Temporal 兼容层或 Day.js | 格式化与本地时区展示 |
| ID | crypto.randomUUID | 本地导入记录标识 |

## 5. 字体

| 用途 | 字体 |
|---|---|
| UI 正文 | IBM Plex Sans |
| 时间、数值、原始 JSON | IBM Plex Mono |

字体通过 `@fontsource` 自托管，避免生产环境依赖远程字体请求。

## 6. 测试与质量

| 类别 | 技术 |
|---|---|
| 单元测试 | Vitest |
| 组件测试 | Vue Testing Library |
| E2E | Playwright |
| 可访问性 | axe-core Playwright 集成 |
| 静态检查 | ESLint、Prettier、vue-tsc |
| 覆盖率 | Vitest coverage |

## 7. 建议依赖

```json
{
  "dependencies": {
    "vue": "^3.5",
    "vue-router": "^4.4",
    "pinia": "^2.2",
    "element-plus": "^2.8",
    "lucide-vue-next": "^0.468",
    "@vueuse/core": "^12.0",
    "@tanstack/vue-virtual": "^3.11",
    "d3-scale": "^4.0",
    "d3-time-format": "^4.1",
    "dexie": "^4.0",
    "zod": "^3.24",
    "dayjs": "^1.11"
  },
  "devDependencies": {
    "typescript": "^5.7",
    "vite": "^6.0",
    "vitest": "^2.1",
    "@vue/test-utils": "^2.4",
    "@testing-library/vue": "^8.1",
    "@playwright/test": "^1.49",
    "@axe-core/playwright": "^4.10",
    "eslint": "^9.0",
    "prettier": "^3.4",
    "vue-tsc": "^2.2"
  }
}
```

版本号在实现时通过锁文件固定，实际安装前检查兼容性。

## 8. 技术风险

| 风险 | 影响 | 对策 |
|---|---|---|
| 时间轴交互复杂 | 开发周期增加 | 先完成只读瀑布，再增加缩放和框选 |
| 大数据量行渲染 | 滚动卡顿 | 虚拟列表和时间分桶 |
| 多格式输入不稳定 | adapter 膨胀 | 先支持标准模型和手动字段映射 |
| 视觉信息过密 | 可读性下降 | 分层显示、默认摘要、详情按需展开 |

