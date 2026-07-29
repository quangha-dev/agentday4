export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const AGENT_API_BASE = process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://localhost:8502";

export type DocumentItem = {
  id: string; title: string; original_filename: string; status: string; page_count: number;
  document_number: string; issued_date: string | null; effective_date: string | null;
  document_type: string; issuing_authority: string; signer: string; summary: string;
  version_number: number; previous_version_id: string | null;
  error_message: string | null; created_at: string; updated_at: string;
};

export type LegalMetadata = {
  document_number: string; issued_date: string; effective_date: string;
  document_type: string; issuing_authority: string; signer: string; summary: string;
};

export type PageItem = {
  id: string; document_id: string; page_number: number; classification: string;
  ocr_engine: string | null; ocr_languages: string | null;
  raw_text: string; cleaned_text: string | null; verified_text: string | null;
  canonical_text: string;
  confidence: number | null; bounding_boxes: unknown[]; is_verified: boolean; image_url: string | null;
};

export type LegalNode = {
  id: string; document_id: string; parent_id: string | null; node_type: string;
  marker: string | null; title: string | null; content: string; full_path: string;
  order_index: number; page_start: number; page_end: number; bbox_spans: unknown[]; children: LegalNode[];
};

export type SearchResult = Omit<LegalNode, "children" | "parent_id" | "order_index" | "bbox_spans"> & {
  document_title: string; legal_node_id: string; score: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? body?.message ?? `Yêu cầu thất bại (${response.status})`);
  }
  return response.json() as Promise<T>;
}

async function agentRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${AGENT_API_BASE}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Agent không khả dụng (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export type AgentToolEvent = {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
};

export type AgentChatResult = {
  status: string;
  mode?: "agent" | "unavailable";
  assistant_text: string;
  tool_events: AgentToolEvent[];
  artifact_version?: string;
  requested_version?: "v0" | "v1" | "v2";
  warning?: string;
  execution_plan?: Record<string, unknown> | null;
};

export type SystemReadiness = {
  contract_version: string;
  ready: boolean;
  ocr: {
    ready: boolean;
    engine: string;
    executable: string | null;
    required_languages: string[];
    available_languages: string[];
    error: { code: string; message: string } | null;
  };
  embedding: { ready: boolean; model: string; semantic: boolean; vector_size: number; collection: string };
};

export const api = {
  chat: (messages: Array<{ role: "user" | "assistant"; content: string }>, artifactVersion: "v0" | "v1" | "v2" = "v2") => agentRequest<AgentChatResult>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, artifact_version: artifactVersion }),
  }),
  documents: () => request<DocumentItem[]>("/documents"),
  document: (id: string) => request<DocumentItem>(`/documents/${id}`),
  readiness: () => request<SystemReadiness>("/system/readiness"),
  upload: (file: File, metadata: LegalMetadata) => {
    const body = new FormData();
    body.append("file", file);
    Object.entries(metadata).forEach(([key, value]) => body.append(key, value));
    return request<DocumentItem>("/documents/upload", { method: "POST", body });
  },
  deleteDocument: (id: string) => request<{ message: string }>(`/documents/${id}`, { method: "DELETE" }),
  process: (id: string) => request<{ id: string }>(`/documents/${id}/process`, { method: "POST" }),
  job: (id: string) => request<{ status: string; progress: number; message: string | null }>(`/jobs/${id}`),
  pages: (id: string) => request<PageItem[]>(`/documents/${id}/pages`),
  cleanPage: (id: string) => request<PageItem>(`/pages/${id}/clean`, { method: "POST" }),
  cleanPageWithLlm: (id: string) => request<{ page: PageItem; method: string; warning: string | null }>(`/pages/${id}/clean/llm`, { method: "POST" }),
  cleanDocument: (id: string) => request<{ message: string }>(`/documents/${id}/clean`, { method: "POST" }),
  saveText: (id: string, content: string) => request<PageItem>(`/pages/${id}/text`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) }),
  verify: (id: string, content: string) => request<PageItem>(`/pages/${id}/verify`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) }),
  parse: (id: string) => request<{ message: string; node_count: number }>(`/documents/${id}/parse`, { method: "POST" }),
  index: (id: string) => request<{ message: string; indexed_articles: number; indexed_chunks: number; chunk_strategy: string; model: string }>(`/documents/${id}/index`, { method: "POST" }),
  tree: (id: string) => request<LegalNode[]>(`/documents/${id}/tree`),
  search: (query: string, mode: string, document_id?: string) => request<SearchResult[]>("/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, mode, document_id: document_id || null, limit: 15 }) }),
  fileUrl: (id: string, page = 1) => `${API_BASE}/documents/${id}/file#page=${page}&view=FitH`,
  exportUrl: (id: string) => `${API_BASE}/documents/${id}/export/json`,
};
