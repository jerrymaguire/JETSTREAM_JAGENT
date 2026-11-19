<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  Activity,
  ChevronRight,
  KeyRound,
  Menu,
  MessageSquare,
  Moon,
  PanelRight,
  Settings2,
  Sun,
  Target,
  Waypoints,
} from "lucide-vue-next";
import { api } from "./api";
import ChatPanel from "./components/ChatPanel.vue";
import GoalDialog from "./components/GoalDialog.vue";
import ProviderDialog from "./components/ProviderDialog.vue";
import SessionSidebar from "./components/SessionSidebar.vue";
import SpanInspector from "./components/SpanInspector.vue";
import TracePanel from "./components/TracePanel.vue";
import type {
  Checkpoint,
  Attachment,
  Goal,
  Message,
  Provider,
  Session,
  Skill,
  Span,
  TraceData,
} from "./types";

const sessions = ref<Session[]>([]);
const currentId = ref("");
const currentSession = ref<Session | null>(null);
const messages = ref<Message[]>([]);
const goals = ref<Goal[]>([]);
const trace = ref<TraceData | null>(null);
const providers = ref<Provider[]>([]);
const skills = ref<Skill[]>([]);
const selectedSkillIds = ref<string[]>([]);
const checkpoints = ref<Checkpoint[]>([]);
const activeTab = ref<"chat" | "trace">("chat");
const selectedSpanId = ref("");
const streamingText = ref("");
const loading = ref(true);
const error = ref("");
const goalOpen = ref(false);
const providerOpen = ref(false);
const sidebarOpen = ref(false);
const inspectorOpen = ref(window.innerWidth >= 1180);
const theme = ref<"light" | "dark">(
  (localStorage.getItem("agentshow-theme") as "light" | "dark") || "dark",
);

let socket: WebSocket | null = null;
let refreshTimer = 0;

const currentGoal = computed(() => goals.value[0] || null);
const selectedSpan = computed(
  () => trace.value?.spans.find((span) => span.id === selectedSpanId.value) || null,
);
const selectedToolCall = computed(
  () => trace.value?.tool_calls.find((call) => call.span_id === selectedSpanId.value) || null,
);
const running = computed(
  () => Boolean(streamingText.value) || currentSession.value?.status === "running",
);

function toggleTheme(): void {
  theme.value = theme.value === "light" ? "dark" : "light";
  localStorage.setItem("agentshow-theme", theme.value);
}

async function loadSessions(preferredId?: string): Promise<void> {
  sessions.value = await api.sessions();
  const target =
    preferredId ||
    sessions.value.find((item) => item.id === "sess_demo_001")?.id ||
    sessions.value[0]?.id;
  if (target) await selectSession(target);
}

async function selectSession(id: string): Promise<void> {
  currentId.value = id;
  activeTab.value = "chat";
  selectedSpanId.value = "";
  streamingText.value = "";
  error.value = "";
  const detail = await api.session(id);
  currentSession.value = detail;
  messages.value = detail.messages;
  await Promise.all([loadTrace(), loadGoals(), loadCheckpoints()]);
  connectSocket(id);
  void api.warmupSession(id).catch(() => {
    // Warmup is best effort. The normal send path still reports real failures.
  });
}

async function loadTrace(): Promise<void> {
  if (!currentId.value) return;
  try {
    trace.value = await api.trace(currentId.value);
    if (!selectedSpanId.value && trace.value.spans.length) {
      selectedSpanId.value =
        trace.value.spans.find((span) => span.kind === "tool" && span.status === "success")?.id ||
        trace.value.spans[0].id;
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  }
}

async function loadGoals(): Promise<void> {
  if (!currentId.value) return;
  goals.value = await api.goals(currentId.value);
}

async function loadCheckpoints(): Promise<void> {
  if (!currentId.value) return;
  checkpoints.value = await api.checkpoints(currentId.value);
}

function connectSocket(sessionId: string): void {
  socket?.close();
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${location.host}/api/ws/sessions/${sessionId}`);
  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "assistant.delta") {
      streamingText.value += payload.delta || "";
      return;
    }
    if (payload.type === "message.started" && payload.data?.role === "user") {
      const message = payload.data;
      if (!messages.value.some((item) => item.id === message.message_id)) {
        messages.value.push({
          id: message.message_id,
          session_id: sessionId,
          role: "user",
          content: message.content,
          created_at: new Date().toISOString(),
        });
      }
      return;
    }
    if (payload.type === "run.completed" || payload.type === "run.failed") {
      streamingText.value = "";
    }
    if (payload.type === "session.updated" && currentSession.value) {
      currentSession.value = {
        ...currentSession.value,
        title: payload.data?.title || currentSession.value.title,
      };
      sessions.value = sessions.value.map((session) =>
        session.id === sessionId
          ? { ...session, title: payload.data?.title || session.title }
          : session,
      );
    }
    scheduleRefresh();
  };
  socket.onerror = () => {
    error.value = "实时事件连接已断开，页面将在下一次操作时重新同步。";
  };
}

function scheduleRefresh(): void {
  window.clearTimeout(refreshTimer);
  refreshTimer = window.setTimeout(async () => {
    if (!currentId.value) return;
    const detail = await api.session(currentId.value);
    currentSession.value = detail;
    messages.value = detail.messages;
    await Promise.all([loadTrace(), loadGoals(), loadCheckpoints()]);
    sessions.value = await api.sessions();
  }, 220);
}

async function createSession(): Promise<void> {
  const session = await api.createSession();
  sidebarOpen.value = false;
  await loadSessions(session.id);
}

async function renameSession(id: string, title: string): Promise<void> {
  const updated = await api.renameSession(id, title);
  sessions.value = sessions.value.map((session) => (session.id === id ? updated : session));
  if (currentSession.value?.id === id) {
    currentSession.value = { ...currentSession.value, title: updated.title };
  }
}

async function deleteSession(id: string): Promise<void> {
  const session = sessions.value.find((item) => item.id === id);
  if (!window.confirm(`删除对话“${session?.title || id}”？此操作不可撤销。`)) return;
  await api.deleteSession(id);
  const remaining = sessions.value.filter((item) => item.id !== id);
  sessions.value = remaining;
  if (currentId.value === id) {
    if (remaining[0]) {
      await selectSession(remaining[0].id);
    } else {
      currentId.value = "";
      currentSession.value = null;
      messages.value = [];
      trace.value = null;
      goals.value = [];
      checkpoints.value = [];
    }
  }
}

async function sendMessage(content: string, attachments: Attachment[] = []): Promise<void> {
  if (!currentId.value) return;
  const displayContent =
    content +
    (attachments.length
      ? `\n\n附件：${attachments.map((item) => item.name).join("、")}`
      : "");
  const optimistic: Message = {
    id: `local_${Date.now()}`,
    session_id: currentId.value,
    role: "user",
    content: displayContent,
    created_at: new Date().toISOString(),
  };
  messages.value.push(optimistic);
  currentSession.value = currentSession.value
    ? { ...currentSession.value, status: "running" }
    : currentSession.value;
  const mentionedSkills = skills.value
    .filter((skill) => content.includes(`@${skill.name}`))
    .map((skill) => skill.id);
  const requestedSkills = Array.from(new Set([...selectedSkillIds.value, ...mentionedSkills]));
  try {
    await api.sendMessage(currentId.value, content, requestedSkills, attachments);
  } catch (cause) {
    messages.value = messages.value.filter((item) => item.id !== optimistic.id);
    error.value = cause instanceof Error ? cause.message : String(cause);
  }
}

async function createGoal(payload: {
  objective: string;
  criteria: string[];
  constraints: string[];
  maxIterations: number;
}): Promise<void> {
  if (!currentId.value) return;
  await api.createGoal(
    currentId.value,
    payload.objective,
    payload.criteria,
    payload.constraints,
    payload.maxIterations,
    selectedSkillIds.value,
  );
  goalOpen.value = false;
  await loadGoals();
  activeTab.value = "chat";
}

async function goalAction(action: "pause" | "resume" | "cancel"): Promise<void> {
  if (!currentGoal.value) return;
  await api.goalAction(currentGoal.value.id, action);
  await loadGoals();
}

async function createProvider(payload: Record<string, unknown>): Promise<void> {
  await api.createProvider(payload);
  providers.value = await api.providers();
}

async function saveKey(id: string, key: string): Promise<void> {
  await api.saveCredential(id, key);
  providers.value = await api.providers();
}

async function testProvider(id: string): Promise<void> {
  try {
    const result = await api.testProvider(id);
    error.value = "";
    window.alert(result.message);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  }
}

function toggleSkill(skillId: string): void {
  selectedSkillIds.value = selectedSkillIds.value.includes(skillId)
    ? selectedSkillIds.value.filter((id) => id !== skillId)
    : [...selectedSkillIds.value, skillId];
}

async function addSkillPath(skillPath: string): Promise<void> {
  try {
    const result = await api.addSkillPath(skillPath);
    skills.value = await api.skills();
    for (const skill of result.skills) {
      if (!selectedSkillIds.value.includes(skill.id)) {
        selectedSkillIds.value.push(skill.id);
      }
    }
    error.value = "";
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  }
}

function selectSpan(span: Span): void {
  selectedSpanId.value = span.id;
  inspectorOpen.value = true;
}

onMounted(async () => {
  try {
    providers.value = await api.providers();
    skills.value = await api.skills();
    await loadSessions();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    loading.value = false;
  }
});

onBeforeUnmount(() => {
  socket?.close();
  window.clearTimeout(refreshTimer);
});
</script>

<template>
  <div class="app-shell" :data-theme="theme">
    <header class="topbar">
      <div class="topbar-left">
        <button class="icon-button mobile-only" type="button" aria-label="打开会话栏" @click="sidebarOpen = true">
          <Menu :size="18" stroke-width="1.8" />
        </button>
        <div class="topbar-title">
          <span class="product-word">JAGENT</span>
          <ChevronRight :size="14" class="crumb-separator" />
          <span class="session-heading">{{ currentSession?.title || "Agent Trace Workbench" }}</span>
        </div>
      </div>
      <div class="topbar-center">
        <span class="provider-pill">
          <Activity :size="14" />
          {{ currentSession?.model_name || "Demo Agent" }}
        </span>
        <span class="status-pill" :class="currentSession?.status || 'idle'">
          {{ running ? "运行中" : currentSession?.status === "error" ? "错误" : "空闲" }}
        </span>
      </div>
      <div class="topbar-actions">
        <button class="tool-button subtle" type="button" @click="providerOpen = true">
          <KeyRound :size="15" stroke-width="1.8" />
          API Keys
        </button>
        <button class="icon-button" type="button" aria-label="切换主题" @click="toggleTheme">
          <Sun v-if="theme === 'dark'" :size="17" />
          <Moon v-else :size="17" />
        </button>
        <button
          class="icon-button desktop-only"
          type="button"
          aria-label="切换详情栏"
          @click="inspectorOpen = !inspectorOpen"
        >
          <PanelRight :size="17" />
        </button>
      </div>
    </header>

    <div v-if="error" class="error-banner" role="alert">
      {{ error }}
      <button type="button" @click="error = ''">关闭</button>
    </div>

    <main class="workspace-shell" :class="{ 'sidebar-open': sidebarOpen, 'inspector-closed': !inspectorOpen }">
      <div class="mobile-scrim" :class="{ visible: sidebarOpen }" @click="sidebarOpen = false" />
      <SessionSidebar
        :sessions="sessions"
        :current-id="currentId"
        @select="selectSession($event); sidebarOpen = false"
        @create="createSession"
        @settings="providerOpen = true"
        @rename="renameSession"
        @delete="deleteSession"
      />

      <section class="main-panel">
        <nav class="view-tabs" aria-label="工作区视图">
          <button :class="{ active: activeTab === 'chat' }" type="button" @click="activeTab = 'chat'">
            <MessageSquare :size="15" stroke-width="1.8" />
            对话
          </button>
          <button :class="{ active: activeTab === 'trace' }" type="button" @click="activeTab = 'trace'">
            <Waypoints :size="15" stroke-width="1.8" />
            轨迹
            <span class="tab-count">{{ trace?.summary.call_count || 0 }}</span>
          </button>
          <span class="view-tabs-spacer" />
          <button class="goal-button" type="button" @click="goalOpen = true">
            <Target :size="15" stroke-width="1.8" />
            设定目标
          </button>
        </nav>

        <div v-if="loading" class="loading-shell">
          <div class="skeleton wide" />
          <div class="skeleton" />
          <div class="skeleton short" />
        </div>
        <ChatPanel
          v-else-if="activeTab === 'chat'"
          :session="currentSession"
          :messages="messages"
          :goal="currentGoal"
          :streaming-text="streamingText"
          :running="running"
          :skills="skills"
          :selected-skill-ids="selectedSkillIds"
          @send="sendMessage"
          @goal="goalOpen = true"
          @pause-goal="goalAction('pause')"
          @resume-goal="goalAction('resume')"
          @cancel-goal="goalAction('cancel')"
          @toggle-skill="toggleSkill"
          @add-skill-path="addSkillPath"
        />
        <TracePanel
          v-else
          :trace="trace"
          :selected-span-id="selectedSpanId"
          @select-span="selectSpan"
        />
      </section>

      <SpanInspector
        v-if="inspectorOpen"
        :session="currentSession"
        :trace="trace"
        :span="selectedSpan"
        :tool-call="selectedToolCall"
        :checkpoints="checkpoints"
      />
    </main>

    <GoalDialog :open="goalOpen" @close="goalOpen = false" @submit="createGoal" />
    <ProviderDialog
      :open="providerOpen"
      :providers="providers"
      @close="providerOpen = false"
      @create="createProvider"
      @save-key="saveKey"
      @test="testProvider"
    />
  </div>
</template>

