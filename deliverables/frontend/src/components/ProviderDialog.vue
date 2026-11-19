<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Check, KeyRound, Plus, ServerCog, X } from "lucide-vue-next";
import type { Provider } from "../types";

const props = defineProps<{
  open: boolean;
  providers: Provider[];
}>();

const emit = defineEmits<{
  close: [];
  create: [payload: Record<string, unknown>];
  saveKey: [id: string, key: string];
  test: [id: string];
}>();

const selectedId = ref("");
const apiKey = ref("");
const showCreate = ref(false);
const name = ref("DeepSeek");
const baseUrl = ref("https://api.deepseek.com");
const model = ref("deepseek-chat");
const newKey = ref("");
const testing = ref(false);

const selected = computed(() => props.providers.find((item) => item.id === selectedId.value));

watch(
  () => props.providers,
  (items) => {
    if (!selectedId.value && items.length) selectedId.value = items[0].id;
  },
  { immediate: true },
);

function create(): void {
  emit("create", {
    name: name.value,
    protocol: "openai-compatible",
    base_url: baseUrl.value,
    model: model.value,
    api_key: newKey.value || null,
    is_default: true,
  });
  showCreate.value = false;
}

function saveKey(): void {
  if (!selected.value || !apiKey.value) return;
  emit("saveKey", selected.value.id, apiKey.value);
  apiKey.value = "";
}

function test(): void {
  if (!selected.value) return;
  testing.value = true;
  emit("test", selected.value.id);
  window.setTimeout(() => {
    testing.value = false;
  }, 1200);
}
</script>

<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <section class="modal provider-modal" role="dialog" aria-modal="true" aria-labelledby="provider-title">
      <header class="modal-header">
        <div class="modal-title">
          <span class="modal-icon"><KeyRound :size="18" stroke-width="1.8" /></span>
          <div>
            <h2 id="provider-title">模型与 API Key</h2>
            <p>密钥只保存在本地，使用后不会再次明文返回。</p>
          </div>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">
          <X :size="18" stroke-width="1.8" />
        </button>
      </header>

      <div class="provider-layout">
        <aside class="provider-list">
          <button
            v-for="provider in providers"
            :key="provider.id"
            class="provider-item"
            :class="{ active: provider.id === selectedId }"
            type="button"
            @click="selectedId = provider.id"
          >
            <ServerCog :size="16" stroke-width="1.8" />
            <span>
              <strong>{{ provider.name }}</strong>
              <small>{{ provider.model }}</small>
            </span>
            <Check v-if="provider.api_key_set || provider.protocol === 'demo'" :size="14" />
          </button>
          <button class="provider-add" type="button" @click="showCreate = !showCreate">
            <Plus :size="15" stroke-width="1.8" />
            添加 Provider
          </button>
        </aside>

        <div class="provider-detail">
          <template v-if="showCreate">
            <div class="form-grid">
              <label class="field"><span>名称</span><input v-model="name" /></label>
              <label class="field"><span>模型 ID</span><input v-model="model" /></label>
            </div>
            <label class="field"><span>Base URL</span><input v-model="baseUrl" /></label>
            <label class="field"><span>API Key</span><input v-model="newKey" type="password" /></label>
            <button class="btn primary" type="button" @click="create">
              <Plus :size="16" stroke-width="1.8" />
              创建 Provider
            </button>
          </template>

          <template v-else-if="selected">
            <div class="provider-summary">
              <div>
                <span class="eyebrow">当前 Provider</span>
                <h3>{{ selected.name }}</h3>
              </div>
              <span class="status-pill" :class="{ good: selected.api_key_set || selected.protocol === 'demo' }">
                {{ selected.api_key_set || selected.protocol === "demo" ? "可用" : "待配置" }}
              </span>
            </div>
            <dl class="detail-list">
              <div><dt>协议</dt><dd>{{ selected.protocol }}</dd></div>
              <div><dt>Base URL</dt><dd>{{ selected.base_url || "本地 Demo" }}</dd></div>
              <div><dt>模型</dt><dd>{{ selected.model }}</dd></div>
              <div><dt>密钥</dt><dd>{{ selected.api_key_hint || "未配置" }}</dd></div>
            </dl>
            <div v-if="selected.protocol !== 'demo'" class="key-form">
              <label class="field">
                <span>保存或轮换 API Key</span>
                <input v-model="apiKey" type="password" placeholder="sk-..." />
              </label>
              <button class="btn secondary" type="button" :disabled="!apiKey" @click="saveKey">
                保存密钥
              </button>
              <button class="btn ghost" type="button" :disabled="testing" @click="test">
                {{ testing ? "测试中" : "测试连接" }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </section>
  </div>
</template>

