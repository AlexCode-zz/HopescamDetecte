import type { AnalysisResult, PatientRecord, ChatMessage } from "@/types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function json<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const res = await fetch(input, {
    headers: { "Accept": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body.detail || body.message || "";
    } catch {
      detail = res.statusText;
    }
    throw new Error(detail || `Error ${res.status}`);
  }
  return (await res.json()) as T;
}

export type { AnalysisResult, PatientRecord, ChatMessage };

export const api = {
  health: () => json<{ ok: boolean; model_ready: boolean; search_enabled: boolean; chat_available: boolean }>("/api/health"),

  demoImage: () => json<{ image_b64: string; label: string }>("/api/demo/image"),

  analyze: async (form: FormData): Promise<AnalysisResult> => {
    return json<AnalysisResult>("/api/analyze", { method: "POST", body: form });
  },

  patientLogin: async (password: string) => {
    return json<{ authenticated: boolean; token: string }>("/api/patients/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
  },

  patientLogout: async (token: string) => {
    return json<{ ok: boolean }>("/api/patients/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: token }),
    });
  },

  patientSearch: async (token: string, q: string): Promise<{ results: PatientRecord[]; count: number }> => {
    const url = new URL("/api/patients/search", BASE || window.location.origin);
    if (q) url.searchParams.set("q", q);
    url.searchParams.set("token", token);
    return json(url.toString());
  },

  chat: async (body: {
    question: string;
    history?: ChatMessage[];
    last_result?: AnalysisResult | null;
  }) => {
    return json<{
      text: string;
      sources: { title: string; doc_id: string; snippet: string; score: number }[];
      kind: string;
      used_llm: boolean;
      disclaimer: string;
    }>("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },
};
