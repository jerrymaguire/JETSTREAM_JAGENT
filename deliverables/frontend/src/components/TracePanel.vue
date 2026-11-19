<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Activity,
  AlertTriangle,
  Bot,
  Clock3,
  Filter,
  Gauge,
  Layers3,
  Search,
  Target,
  Wrench,
} from "lucide-vue-next";
import type { Span, TraceData } from "../types";

const props = defineProps<{
  trace: TraceData | null;
  selectedSpanId?: string;
}>();

const emit = defineEmits<{
  selectSpan: [span: Span];
}>();

const query = ref("");
const kindFilter = ref("all");

const kindLabels: Record<string, string> = {
  run: "Agent",
  llm: "LLM",
  tool: "Tool",
  approval: "Approval",
  compaction: "Context",
  system: "System",
};

const domain = computed(() => {
  const spans = props.trace?.spans ?? [];
  if (!spans.length) return { start: Date.now(), end: Date.now() + 1 };
  const starts = spans.map((span) => new Date(span.started_at).getTime()).filter(Number.isFinite);
  const ends = spans
    .map((span) => new Date(span.ended_at || span.started_at).getTime())
    .filter(Number.isFinite);
  return { start: Math.min(...starts), end: Math.max(...ends) };
});

const totalMs = computed(() =>
  Math.max(1, domain.value.end - domain.value.start, props.trace?.summary.total_duration_ms || 0),
);

const filteredSpans = computed(() => {
  const spans = props.trace?.spans ?? [];
  const search = query.value.trim().toLowerCase();
  return spans.filter((span) => {
    if (kindFilter.value !== "all" && span.kind !== kindFilter.value) return false;
    if (!search) return true;
    return [span.id, span.name, span.summary, span.kind, span.run_id]
      .join(" ")
      .toLowerCase()
      .includes(search);
  });
});

const overviewGroups = computed(() => {
  const spans = props.trace?.spans ?? [];
  const kinds = ["run", "llm", "tool", "approval", "compaction"];
  return kinds
    .map((kind) => ({
      kind,
      label: kindLabels[kind] || kind,
      spans: spans.filter((span) => span.kind === kind),
    }))
    .filter((group) => group.spans.length > 0);
});

function barStyle(span: Span): Record<string, string> {
  const start = new Date(span.started_at).getTime();
  const end = new Date(span.ended_at || span.started_at).getTime();
  const left = Math.max(0, ((start - domain.value.start) / totalMs.value) * 100);
  const width = Math.max(0.7, ((end - start) / totalMs.value) * 100);
  return { left: `${left}%`, width: `${Math.min(width, 100 - left)}%` };
}

function markerStyle(span: Span): Record<string, string> {
  const start = new Date(span.started_at).getTime();
  const left = Math.max(0, ((start - domain.value.start) / totalMs.value) * 100);
  return { left: `${left}%` };
}

function formatDuration(ms: number | null | undefined): string {
  const value = ms || 0;
  if (value < 1000) return `${value}ms`;
  if (value < 60_000) return `${(value / 1000).toFixed(2)}s`;
  return `${Math.floor(value / 60_000)}m ${Math.round((value % 60_000) / 1000)}s`;
}

function formatClock(value: string): string {
  return new Date(value).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3,
  });
}

function categoryIcon(kind: string) {
  if (kind === "llm") return Bot;
  if (kind === "tool") return Wrench;
  if (kind === "run") return Target;
  if (kind === "compaction") return Layers3;
  return Gauge;
}
</script>

<template>
  <div class="trace-panel">
    <div class="trace-content">
      <section class="metrics-strip">
        <div class="metric">
          <Clock3 :size="15" />
          <span>总运行时长</span>
          <strong>{{ formatDuration(trace?.summary.total_duration_ms) }}</strong>
        </div>
        <div class="metric">
          <Layers3 :size="15" />
          <span>轮次</span>
          <strong>{{ trace?.summary.round_count || 0 }}</strong>
        </div>
        <div class="metric">
          <Gauge :size="15" />
          <span>调用</span>
          <strong>{{ trace?.summary.call_count || 0 }}</strong>
        </div>
        <div class="metric">
          <AlertTriangle :size="15" />
          <span>错误</span>
          <strong>{{ trace?.summary.error_count || 0 }}</strong>
        </div>
        <div class="metric">
          <Bot :size="15" />
          <span>Tokens</span>
          <strong>{{ trace?.summary.total_tokens || 0 }}</strong>
        </div>
        <div class="metric">
          <Activity :size="15" />
          <span>Token 速度</span>
          <strong>{{ trace?.summary.tokens_per_second || 0 }} tok/s</strong>
        </div>
      </section>

      <section class="trace-toolbar">
        <div class="trace-view-title">
          <strong>调用轨迹</strong>
          <span>按真实时间定位模型、工具和审批调用</span>
        </div>
        <div class="trace-controls">
          <label class="trace-search">
            <Search :size="14" />
            <input v-model="query" placeholder="搜索名称、摘要或 span_id" />
          </label>
          <label class="filter-select">
            <Filter :size="14" />
            <select v-model="kindFilter" aria-label="筛选调用类型">
              <option value="all">全部类型</option>
              <option value="llm">LLM</option>
              <option value="tool">Tool</option>
              <option value="approval">Approval</option>
              <option value="compaction">Context</option>
            </select>
          </label>
        </div>
      </section>

      <section class="overview-card">
        <div class="overview-title-row">
          <div>
            <span class="eyebrow">OVERVIEW</span>
            <strong>会话密度</strong>
          </div>
          <span>{{ filteredSpans.length }} spans</span>
        </div>
        <div class="overview-lanes">
          <div v-for="group in overviewGroups" :key="group.kind" class="overview-lane">
            <span class="lane-label">{{ group.label }}</span>
            <div class="lane-track">
              <button
                v-for="span in group.spans"
                :key="span.id"
                class="overview-mark"
                :class="[span.kind, span.status]"
                :style="markerStyle(span)"
                type="button"
                :aria-label="`${span.name} ${formatDuration(span.duration_ms)}`"
                @click="emit('selectSpan', span)"
              />
            </div>
          </div>
        </div>
        <div class="overview-axis">
          <span>0s</span>
          <span>{{ formatDuration(totalMs / 2) }}</span>
          <span>{{ formatDuration(totalMs) }}</span>
        </div>
      </section>

      <section class="waterfall">
        <div class="waterfall-header">
          <span>调用</span>
          <span>开始时间</span>
          <span>持续时长</span>
          <span class="timeline-header">时间轴</span>
        </div>
        <button
          v-for="span in filteredSpans"
          :key="span.id"
          class="trace-row"
          :class="{ selected: span.id === selectedSpanId, error: span.status === 'error' }"
          type="button"
          @click="emit('selectSpan', span)"
        >
          <span class="trace-call">
            <span class="call-icon" :class="span.kind">
              <component :is="categoryIcon(span.kind)" :size="14" stroke-width="1.8" />
            </span>
            <span class="call-copy">
              <strong>{{ span.name }}</strong>
              <small>{{ span.summary }}</small>
            </span>
          </span>
          <time>{{ formatClock(span.started_at) }}</time>
          <span class="duration-cell">{{ formatDuration(span.duration_ms) }}</span>
          <span class="timeline-cell">
            <span class="timeline-grid" />
            <span class="trace-bar" :class="[span.kind, span.status]" :style="barStyle(span)" />
          </span>
        </button>
        <div v-if="filteredSpans.length === 0" class="trace-empty">
          没有匹配的调用
        </div>
      </section>
    </div>
  </div>
</template>

