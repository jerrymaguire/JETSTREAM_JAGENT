import type {
  Attachment,
  Checkpoint,
  Goal,
  Message,
  Provider,
  Session,
  Skill,
  TraceData,
} from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  sessions: () => request<Session[]>("/api/sessions"),
  session: (id: string) =>
    request<Session & { messages: Message[]; goals: Goal[] }>(`/api/sessions/${id}`),
  createSession: (title = "新对话") =>
    request<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  renameSession: (id: string, title: string) =>
    request<Session>(`/api/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteSession: (id: string) =>
    request<{ ok: boolean }>(`/api/sessions/${id}`, { method: "DELETE" }),
  sendMessage: (id: string, content: string, skills: string[] = [], attachments: Attachment[] = []) =>
    request<{ accepted: boolean }>(`/api/sessions/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, skills, attachments }),
    }),
  warmupSession: (id: string) =>
    request<{ warmed: boolean; mode: string }>(`/api/sessions/${id}/warmup`, {
      method: "POST",
    }),
  trace: (id: string) => request<TraceData>(`/api/sessions/${id}/trace`),
  goals: (id: string) => request<Goal[]>(`/api/sessions/${id}/goals`),
  createGoal: (
    sessionId: string,
    objective: string,
    criteria: string[],
    constraints: string[],
    maxIterations: number,
    skills: string[] = [],
  ) =>
    request<{ id: string; status: string }>(`/api/sessions/${sessionId}/goals`, {
      method: "POST",
      body: JSON.stringify({
        objective,
        criteria,
        constraints,
        max_iterations: maxIterations,
        auto_start: true,
        skills,
      }),
    }),
  skills: () => request<Skill[]>("/api/skills"),
  scanSkills: () => request<Skill[]>("/api/skills/scan", { method: "POST" }),
  addSkillPath: (skillPath: string) =>
    request<{ root: string; skills: Skill[] }>("/api/skills/add-path", {
      method: "POST",
      body: JSON.stringify({ path: skillPath }),
    }),
  toggleSkill: (skillId: string, enabled: boolean) =>
    request<Skill>(`/api/skills/${encodeURIComponent(skillId)}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  extractDocument: async (file: File): Promise<Attachment> => {
    const body = new FormData();
    body.append("file", file);
    const response = await fetch("/api/documents/extract", { method: "POST", body });
    if (!response.ok) {
      let detail = "文件解析失败";
      try {
        detail = (await response.json()).detail || detail;
      } catch {
        detail = await response.text();
      }
      throw new Error(detail);
    }
    return response.json();
  },
  exportDocument: async (format: "md" | "docx" | "pdf", title: string, content: string) => {
    const response = await fetch("/api/documents/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, title, content }),
    });
    if (!response.ok) throw new Error(`导出失败: HTTP ${response.status}`);
    return response.blob();
  },
  goalAction: (goalId: string, action: "pause" | "resume" | "cancel") =>
    request<{ ok: boolean }>(`/api/goals/${goalId}/${action}`, { method: "POST" }),
  providers: () => request<Provider[]>("/api/providers"),
  createProvider: (payload: Record<string, unknown>) =>
    request<Provider>("/api/providers", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  saveCredential: (providerId: string, apiKey: string) =>
    request<Provider>(`/api/providers/${providerId}/credential`, {
      method: "PUT",
      body: JSON.stringify({ api_key: apiKey }),
    }),
  testProvider: (providerId: string) =>
    request<{ ok: boolean; message: string }>(`/api/providers/${providerId}/test`, {
      method: "POST",
    }),
  checkpoints: (sessionId: string) =>
    request<Checkpoint[]>(`/api/sessions/${sessionId}/checkpoints`),
  lookup: (id: string) =>
    request<{ entity: string; data: Record<string, unknown> }>(`/api/lookup/${id}`),
};

