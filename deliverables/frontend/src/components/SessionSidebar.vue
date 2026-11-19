<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Check,
  MessageSquare,
  Orbit,
  Pencil,
  Plus,
  Search,
  Settings,
  Target,
  Trash2,
  X,
} from "lucide-vue-next";
import type { Session } from "../types";

const props = defineProps<{
  sessions: Session[];
  currentId: string;
}>();

const emit = defineEmits<{
  select: [id: string];
  create: [];
  settings: [];
  rename: [id: string, title: string];
  delete: [id: string];
}>();

const search = ref("");
const editingId = ref("");
const draftTitle = ref("");

const filtered = computed(() => {
  const query = search.value.trim().toLowerCase();
  if (!query) return props.sessions;
  return props.sessions.filter(
    (session) =>
      session.title.toLowerCase().includes(query) ||
      session.model_name.toLowerCase().includes(query),
  );
});

function formatTime(value: string): string {
  const date = new Date(value);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  return sameDay
    ? date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

function startRename(session: Session): void {
  editingId.value = session.id;
  draftTitle.value = session.title;
}

function saveRename(): void {
  const title = draftTitle.value.trim();
  if (editingId.value && title) emit("rename", editingId.value, title);
  editingId.value = "";
}

function cancelRename(): void {
  editingId.value = "";
  draftTitle.value = "";
}
</script>

<template>
  <aside class="session-sidebar">
    <div class="brand">
      <div class="brand-mark"><Orbit :size="19" stroke-width="1.5" /></div>
      <div>
        <strong>JAgent</strong>
        <span>Agent Trace Workbench</span>
      </div>
    </div>

    <button class="new-session-btn" type="button" @click="emit('create')">
      <Plus :size="17" stroke-width="1.8" />
      新建对话
    </button>

    <label class="search-box">
      <Search :size="15" stroke-width="1.8" />
      <input v-model="search" placeholder="搜索对话" aria-label="搜索对话" />
      <kbd>⌘K</kbd>
    </label>

    <div class="sidebar-section-title">
      <span>对话</span>
      <span>{{ filtered.length }}</span>
    </div>

    <div class="session-list">
      <div
        v-for="session in filtered"
        :key="session.id"
        class="session-item"
        :class="{ active: session.id === currentId }"
      >
        <button
          class="session-select"
          type="button"
          @click="editingId !== session.id && emit('select', session.id)"
        >
          <span class="session-icon">
            <Target v-if="session.id.includes('demo')" :size="15" stroke-width="1.8" />
            <MessageSquare v-else :size="15" stroke-width="1.8" />
          </span>
          <span class="session-copy">
            <span v-if="editingId !== session.id" class="session-title">{{ session.title }}</span>
            <span class="session-meta">
              {{ session.model_name }}
              <span v-if="session.id === 'sess_demo_001'" class="demo-badge">示例</span>
              <i v-if="session.status === 'running'" class="live-dot" />
            </span>
          </span>
          <time :class="{ hidden: editingId === session.id }">{{ formatTime(session.updated_at) }}</time>
        </button>
        <input
          v-if="editingId === session.id"
          v-model="draftTitle"
          class="session-title-input"
          maxlength="60"
          @click.stop
          @keydown.enter.stop="saveRename"
          @keydown.esc.stop="cancelRename"
        />
        <span v-if="editingId === session.id" class="session-actions visible" @click.stop>
          <button class="session-action" type="button" aria-label="保存名称" @click="saveRename">
            <Check :size="13" />
          </button>
          <button class="session-action" type="button" aria-label="取消重命名" @click="cancelRename">
            <X :size="13" />
          </button>
        </span>
        <span v-else class="session-actions" @click.stop>
          <button class="session-action" type="button" aria-label="重命名对话" @click="startRename(session)">
            <Pencil :size="13" />
          </button>
          <button class="session-action danger" type="button" aria-label="删除对话" @click="emit('delete', session.id)">
            <Trash2 :size="13" />
          </button>
        </span>
      </div>

      <div v-if="filtered.length === 0" class="sidebar-empty">
        没有匹配的对话
      </div>
    </div>

    <div class="sidebar-footer">
      <div class="workspace-label">
        <span class="workspace-dot" />
        <span class="ellipsis">local workspace</span>
      </div>
      <button class="icon-button" type="button" aria-label="设置" @click="emit('settings')">
        <Settings :size="17" stroke-width="1.8" />
      </button>
    </div>
  </aside>
</template>

