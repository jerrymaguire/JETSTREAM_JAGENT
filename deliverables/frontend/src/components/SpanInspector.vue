<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Check,
  Clipboard,
  Clock3,
  Database,
  GitBranch,
  Info,
  Layers3,
  Tag,
  Wrench,
} from "lucide-vue-next";
import type { Checkpoint, Session, Span, ToolCall, TraceData } from "../types";

const props = defineProps<{
  session: Session | null;
  trace: TraceData | null;
  span: Span | null;
  toolCall: ToolCall | null;
  checkpoints: Checkpoint[];
}>();

const tab = ref<"overview" | "raw">("overview");
const copied = ref("");

const duration = computed(() => {
  const value = props.span?.duration_ms || 0;
  return value < 1000 ? `${value}ms` : `${(value / 1000).toFixed(2)}s`;
});

const raw = computed(() =>
  JSON.stringify(
    {
      span: props.span,
      tool_call: props.toolCall,
    },
    null,
    2,
  ),
);

async function copy(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
  copied.value = value;
  window.setTimeout(() => {
    if (copied.value === value) copied.value = "";
  }, 1200);
}
</script>

<template>
  <aside class="inspector">
    <template v-if="span">
      <header class="inspector-header">
        <div>
          <span class="eyebrow">{{ span.kind.toUpperCase() }}</span>
          <h3>{{ span.name }}</h3>
        </div>
        <span class="status-pill" :class="span.status">
          {{ span.status }}
        </span>
      </header>

      <div class="inspector-tabs">
        <button :class="{ active: tab === 'overview' }" type="button" @click="tab = 'overview'">
          <Info :size="14" />
          概览
        </button>
        <button :class="{ active: tab === 'raw' }" type="button" @click="tab = 'raw'">
          <Database :size="14" />
          原始内容
        </button>
      </div>

      <div v-if="tab === 'overview'" class="inspector-body">
        <section class="summary-block">
          <p>{{ span.summary }}</p>
        </section>

        <dl class="detail-list inspector-details">
          <div>
            <dt><Clock3 :size="13" /> 开始时间</dt>
            <dd>{{ new Date(span.started_at).toLocaleString("zh-CN") }}</dd>
          </div>
          <div>
            <dt><Clock3 :size="13" /> 持续时长</dt>
            <dd>{{ duration }}</dd>
          </div>
          <div>
            <dt><Tag :size="13" /> 状态</dt>
            <dd>{{ span.status }}</dd>
          </div>
          <div>
            <dt><Layers3 :size="13" /> Run</dt>
            <dd class="mono">{{ span.run_id }}</dd>
          </div>
          <div>
            <dt><GitBranch :size="13" /> Parent</dt>
            <dd class="mono">{{ span.parent_span_id || "root" }}</dd>
          </div>
          <div>
            <dt><Tag :size="13" /> Span ID</dt>
            <dd class="id-cell">
              <code>{{ span.id }}</code>
              <button class="mini-icon-button" type="button" aria-label="复制 Span ID" @click="copy(span.id)">
                <Check v-if="copied === span.id" :size="13" />
                <Clipboard v-else :size="13" />
              </button>
            </dd>
          </div>
        </dl>

        <section v-if="toolCall" class="inspector-section">
          <div class="section-heading">
            <Wrench :size="15" />
            <strong>工具调用</strong>
          </div>
          <dl class="detail-list compact">
            <div><dt>Tool</dt><dd>{{ toolCall.tool_name }}</dd></div>
            <div><dt>状态</dt><dd>{{ toolCall.status }}</dd></div>
            <div>
              <dt>Tool Call ID</dt>
              <dd class="mono">{{ toolCall.id }}</dd>
            </div>
            <div>
              <dt>Args Digest</dt>
              <dd class="mono truncate">{{ toolCall.args_digest }}</dd>
            </div>
          </dl>
          <pre class="code-preview">{{ JSON.stringify(JSON.parse(toolCall.args_json || "{}"), null, 2) }}</pre>
        </section>

        <section v-if="span.output" class="inspector-section">
          <div class="section-heading">
            <Database :size="15" />
            <strong>输出预览</strong>
          </div>
          <pre class="code-preview">{{ JSON.stringify(span.output, null, 2) }}</pre>
        </section>

        <section v-if="span.error" class="inspector-section error-section">
          <div class="section-heading">
            <Info :size="15" />
            <strong>错误</strong>
          </div>
          <pre class="code-preview">{{ JSON.stringify(span.error, null, 2) }}</pre>
        </section>
      </div>

      <div v-else class="inspector-body">
        <pre class="raw-json">{{ raw }}</pre>
      </div>
    </template>

    <template v-else>
      <section class="inspector-empty">
        <div class="empty-icon small"><Layers3 :size="20" stroke-width="1.7" /></div>
        <h3>调用详情</h3>
        <p>选择时间轴中的任一调用，查看开始时间、时长、ID、参数和输出。</p>
      </section>
      <section class="session-facts">
        <span class="eyebrow">SESSION</span>
        <h4>{{ session?.title || "未选择会话" }}</h4>
        <dl class="detail-list compact">
          <div><dt>模型</dt><dd>{{ session?.model_name || "-" }}</dd></div>
          <div><dt>状态</dt><dd>{{ session?.status || "-" }}</dd></div>
          <div><dt>消息</dt><dd>{{ trace?.messages.length || 0 }}</dd></div>
          <div><dt>Checkpoint</dt><dd>{{ checkpoints.length }}</dd></div>
        </dl>
      </section>
    </template>
  </aside>
</template>

