<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import {
  AtSign,
  BookOpen,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  Circle,
  CornerDownLeft,
  Download,
  FolderPlus,
  FileDown,
  FileText,
  LoaderCircle,
  Paperclip,
  Send,
  Square,
  Target,
  UserRound,
  X,
} from "lucide-vue-next";
import { api } from "../api";
import type { Attachment, Goal, Message, Session, Skill } from "../types";

const props = defineProps<{
  session: Session | null;
  messages: Message[];
  goal?: Goal | null;
  streamingText: string;
  running: boolean;
  skills: Skill[];
  selectedSkillIds: string[];
}>();

const emit = defineEmits<{
  send: [content: string, attachments: Attachment[]];
  goal: [];
  pauseGoal: [];
  resumeGoal: [];
  cancelGoal: [];
  toggleSkill: [skillId: string];
  addSkillPath: [path: string];
}>();

const input = ref("");
const scroller = ref<HTMLElement | null>(null);
const skillOpen = ref(false);
const skillPath = ref("");
const attachments = ref<Attachment[]>([]);
const uploading = ref(false);
const uploadError = ref("");
const fileInput = ref<HTMLInputElement | null>(null);

const selectedSkills = computed(() =>
  props.skills.filter((skill) => props.selectedSkillIds.includes(skill.id)),
);

const mentionQuery = computed(() => {
  const match = input.value.match(/(?:^|\s)@([\w-]*)$/);
  return match ? match[1].toLowerCase() : null;
});

const mentionMatches = computed(() => {
  if (mentionQuery.value === null) return [];
  return props.skills
    .filter(
      (skill) =>
        skill.enabled &&
        (!mentionQuery.value ||
          skill.name.toLowerCase().includes(mentionQuery.value) ||
          skill.description.toLowerCase().includes(mentionQuery.value)),
    )
    .slice(0, 8);
});

watch(
  () => props.streamingText,
  async () => {
    await nextTick();
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight;
  },
);

watch(
  () => props.messages.length,
  async () => {
    if (!props.running) return;
    await nextTick();
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight;
  },
);

function send(): void {
  const value = input.value.trim() || (attachments.value.length ? "请分析以下附件内容" : "");
  if (!value || props.running) return;
  emit("send", value, attachments.value);
  input.value = "";
  attachments.value = [];
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    send();
  }
}

function applyMention(skill: Skill): void {
  if (!props.selectedSkillIds.includes(skill.id)) emit("toggleSkill", skill.id);
  input.value = input.value.replace(/(?:^|\s)@([\w-]*)$/, (match) => {
    const leading = match.startsWith(" ") ? " " : "";
    return `${leading}@${skill.name} `;
  });
}

function submitSkillPath(): void {
  const value = skillPath.value.trim();
  if (!value) return;
  emit("addSkillPath", value);
  skillPath.value = "";
  skillOpen.value = false;
}

function chooseFiles(): void {
  fileInput.value?.click();
}

async function handleFiles(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement;
  const files = Array.from(target.files ?? []);
  if (!files.length) return;
  uploading.value = true;
  uploadError.value = "";
  try {
    for (const file of files) {
      const attachment = await api.extractDocument(file);
      attachments.value.push(attachment);
    }
  } catch (cause) {
    uploadError.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    uploading.value = false;
    target.value = "";
  }
}

function removeAttachment(name: string): void {
  attachments.value = attachments.value.filter((item) => item.name !== name);
}

async function downloadMessage(message: Message, format: "md" | "docx" | "pdf"): Promise<void> {
  const blob = await api.exportDocument(
    format,
    `JAgent ${new Date(message.created_at).toLocaleDateString("zh-CN")}`,
    message.content,
  );
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `jagent-response.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}
</script>

<template>
  <div class="chat-panel">
    <div ref="scroller" class="message-scroller">
      <section v-if="goal" class="goal-banner">
        <div class="goal-main">
          <span class="goal-icon"><Target :size="18" stroke-width="1.8" /></span>
          <div class="goal-copy">
            <div class="goal-title-row">
              <strong>{{ goal.objective }}</strong>
              <span class="status-pill" :class="goal.status">{{ goal.status }}</span>
            </div>
            <p>{{ goal.progress_summary || "等待 Agent 推进下一轮。" }}</p>
          </div>
          <span class="iteration-counter">{{ goal.current_iteration }}/{{ goal.max_iterations }}</span>
        </div>
        <div class="goal-progress">
          <div class="goal-criterion" v-for="criterion in goal.criteria" :key="criterion">
            <CheckCircle2 v-if="goal.status === 'completed'" :size="13" />
            <Circle v-else :size="13" />
            {{ criterion }}
          </div>
        </div>
        <div class="goal-actions">
          <button
            v-if="goal.status === 'running' || goal.status === 'planning'"
            class="btn compact ghost"
            type="button"
            @click="emit('pauseGoal')"
          >
            暂停
          </button>
          <button v-if="goal.status === 'paused'" class="btn compact ghost" type="button" @click="emit('resumeGoal')">
            恢复
          </button>
          <button
            v-if="!['completed', 'cancelled'].includes(goal.status)"
            class="btn compact danger-ghost"
            type="button"
            @click="emit('cancelGoal')"
          >
            取消
          </button>
        </div>
      </section>

      <div v-if="messages.length === 0 && !streamingText" class="chat-empty">
        <div class="empty-icon"><Bot :size="24" stroke-width="1.6" /></div>
        <h2>开始一次 Agent 对话</h2>
        <p>对话会保存到本地。设置目标后，Agent 可以跨多轮持续工作。</p>
        <button class="btn secondary" type="button" @click="emit('goal')">
          <Target :size="16" stroke-width="1.8" />
          设定目标
        </button>
      </div>

      <article
        v-for="message in messages"
        :key="message.id"
        class="message-row"
        :class="message.role"
      >
        <div class="message-avatar">
          <UserRound v-if="message.role === 'user'" :size="17" stroke-width="1.8" />
          <Bot v-else :size="17" stroke-width="1.8" />
        </div>
        <div class="message-content">
          <div class="message-meta">
            <strong>{{ message.role === "user" ? "你" : session?.model_name || "Agent" }}</strong>
            <time>{{ formatTime(message.created_at) }}</time>
          </div>
          <p>{{ message.content }}</p>
          <div v-if="message.role === 'assistant'" class="message-export-actions">
            <button type="button" title="导出 Markdown" @click="downloadMessage(message, 'md')">
              <FileText :size="13" />
            </button>
            <button type="button" title="导出 Word" @click="downloadMessage(message, 'docx')">
              <FileDown :size="13" />
            </button>
            <button type="button" title="导出 PDF" @click="downloadMessage(message, 'pdf')">
              <Download :size="13" />
            </button>
          </div>
        </div>
      </article>

      <article v-if="streamingText" class="message-row assistant">
        <div class="message-avatar"><Bot :size="17" stroke-width="1.8" /></div>
        <div class="message-content">
          <div class="message-meta">
            <strong>{{ session?.model_name || "Agent" }}</strong>
            <span class="streaming-label"><LoaderCircle :size="12" class="spin" /> 正在生成</span>
          </div>
          <p>{{ streamingText }}<span class="caret" /></p>
        </div>
      </article>
      <article v-else-if="running" class="message-row assistant waiting-token">
        <div class="message-avatar"><Bot :size="17" stroke-width="1.8" /></div>
        <div class="message-content">
          <div class="message-meta">
            <strong>{{ session?.model_name || "Agent" }}</strong>
            <span class="streaming-label"><LoaderCircle :size="12" class="spin" /> 等待首个 token</span>
          </div>
          <p class="waiting-copy">Agent 正在连接模型和准备运行上下文。</p>
        </div>
      </article>
    </div>

    <footer class="composer-area">
      <div class="composer">
        <input
          ref="fileInput"
          class="hidden-file-input"
          type="file"
          accept=".md,.markdown,.txt,.docx,.pdf"
          multiple
          @change="handleFiles"
        />
        <div v-if="selectedSkills.length" class="selected-skills">
          <button
            v-for="skill in selectedSkills"
            :key="skill.id"
            class="skill-chip"
            type="button"
            :title="skill.description"
            @click="emit('toggleSkill', skill.id)"
          >
            <BookOpen :size="13" stroke-width="1.8" />
            {{ skill.name }}
            <X :size="12" />
          </button>
        </div>
        <div v-if="attachments.length" class="attached-documents">
          <button
            v-for="attachment in attachments"
            :key="attachment.name"
            class="document-chip"
            type="button"
            :title="`${attachment.kind} · ${Math.ceil(attachment.size / 1024)} KB`"
            @click="removeAttachment(attachment.name)"
          >
            <FileText :size="13" />
            <span class="ellipsis">{{ attachment.name }}</span>
            <X :size="12" />
          </button>
        </div>
        <textarea
          v-model="input"
          rows="3"
          placeholder="给 Agent 发消息，输入 @ 选择 Skill，或描述一个要持续完成的目标…"
          @keydown="handleKeydown"
        />
        <div v-if="mentionMatches.length" class="mention-popover">
          <div class="mention-heading">
            <AtSign :size="14" />
            选择 Skill
          </div>
          <button
            v-for="skill in mentionMatches"
            :key="skill.id"
            class="mention-item"
            type="button"
            @click="applyMention(skill)"
          >
            <span>
              <strong>{{ skill.name }}</strong>
              <small>{{ skill.description }}</small>
            </span>
            <Check v-if="selectedSkillIds.includes(skill.id)" :size="14" />
          </button>
        </div>
        <div v-if="skillOpen" class="skill-popover">
          <div class="mention-heading">
            <BookOpen :size="14" />
            可用 Skill
            <button class="icon-button mini" type="button" aria-label="关闭 Skill 面板" @click="skillOpen = false">
              <X :size="14" />
            </button>
          </div>
          <div class="skill-list">
            <button
              v-for="skill in skills"
              :key="skill.id"
              class="skill-option"
              :class="{ selected: selectedSkillIds.includes(skill.id) }"
              type="button"
              :disabled="!skill.enabled"
              @click="emit('toggleSkill', skill.id)"
            >
              <span class="skill-check">
                <Check v-if="selectedSkillIds.includes(skill.id)" :size="12" />
              </span>
              <span class="skill-option-copy">
                <strong>{{ skill.name }}</strong>
                <small>{{ skill.description }}</small>
              </span>
              <span class="skill-version">v{{ skill.version }}</span>
            </button>
          </div>
          <div class="skill-path-form">
            <label>
              <FolderPlus :size="14" />
              <input
                v-model="skillPath"
                placeholder="粘贴 SKILL.md 或 Skill 目录路径"
                @keydown.enter.prevent="submitSkillPath"
              />
            </label>
            <button class="btn compact secondary" type="button" :disabled="!skillPath.trim()" @click="submitSkillPath">
              加载
            </button>
          </div>
        </div>
        <div class="composer-toolbar">
          <div class="composer-tools">
            <button
              class="tool-button"
              type="button"
              :disabled="uploading"
              @click="chooseFiles"
            >
              <LoaderCircle v-if="uploading" :size="15" class="spin" />
              <Paperclip v-else :size="15" stroke-width="1.8" />
              {{ uploading ? "解析中" : "文件" }}
            </button>
            <button
              class="tool-button skill-trigger"
              :class="{ active: skillOpen }"
              type="button"
              @click="skillOpen = !skillOpen"
            >
              <AtSign :size="15" stroke-width="1.8" />
              Skill
              <span v-if="selectedSkillIds.length" class="skill-count">{{ selectedSkillIds.length }}</span>
              <ChevronDown :size="12" />
            </button>
            <button class="tool-button" type="button" @click="emit('goal')">
              <Target :size="15" stroke-width="1.8" />
              Goal
            </button>
          </div>
          <div class="composer-submit">
            <span class="composer-hint"><CornerDownLeft :size="12" /> Enter 发送</span>
            <button
              v-if="!running"
              class="send-button"
              type="button"
              :disabled="!input.trim() && attachments.length === 0"
              @click="send"
            >
              <Send :size="16" stroke-width="1.9" />
            </button>
            <button v-else class="send-button stop" type="button" aria-label="停止">
              <Square :size="14" fill="currentColor" />
            </button>
          </div>
        </div>
        <div v-if="uploadError" class="composer-error" role="alert">{{ uploadError }}</div>
      </div>
    </footer>
  </div>
</template>

