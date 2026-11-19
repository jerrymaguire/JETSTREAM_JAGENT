<script setup lang="ts">
import { ref } from "vue";
import { CircleHelp, Target, X } from "lucide-vue-next";

defineProps<{
  open: boolean;
  busy?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  submit: [
    payload: {
      objective: string;
      criteria: string[];
      constraints: string[];
      maxIterations: number;
    },
  ];
}>();

const objective = ref("");
const criteria = ref("完成核心功能\n通过构建与测试\n提供 README 和演示材料");
const constraints = ref("不修改工作区之外的路径\n不输出 API Key");
const maxIterations = ref(5);

function submit(): void {
  const text = objective.value.trim();
  if (!text) return;
  emit("submit", {
    objective: text,
    criteria: criteria.value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
    constraints: constraints.value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
    maxIterations: maxIterations.value,
  });
}
</script>

<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <section class="modal goal-modal" role="dialog" aria-modal="true" aria-labelledby="goal-title">
      <header class="modal-header">
        <div class="modal-title">
          <span class="modal-icon"><Target :size="18" stroke-width="1.8" /></span>
          <div>
            <h2 id="goal-title">设定目标</h2>
            <p>Agent 会持续迭代，直到完成标准通过或触发停止条件。</p>
          </div>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">
          <X :size="18" stroke-width="1.8" />
        </button>
      </header>

      <div class="modal-body goal-form">
        <label class="field">
          <span>目标</span>
          <textarea
            v-model="objective"
            rows="3"
            placeholder="例如：完成作业五的 Agent 轨迹可视化页面，并提交可运行演示。"
          />
        </label>
        <div class="form-grid">
          <label class="field">
            <span>完成标准，每行一条</span>
            <textarea v-model="criteria" rows="5" />
          </label>
          <label class="field">
            <span>约束，每行一条</span>
            <textarea v-model="constraints" rows="5" />
          </label>
        </div>
        <label class="field compact-field">
          <span>最大迭代轮次</span>
          <input v-model.number="maxIterations" type="number" min="1" max="20" />
        </label>
        <div class="inline-note">
          <CircleHelp :size="15" stroke-width="1.8" />
          每轮完成后会保存 Goal checkpoint，未完成时继续下一轮。
        </div>
      </div>

      <footer class="modal-footer">
        <button class="btn ghost" type="button" @click="emit('close')">取消</button>
        <button class="btn primary" type="button" :disabled="busy || !objective.trim()" @click="submit">
          <Target :size="16" stroke-width="1.8" />
          启动 Goal Loop
        </button>
      </footer>
    </section>
  </div>
</template>

