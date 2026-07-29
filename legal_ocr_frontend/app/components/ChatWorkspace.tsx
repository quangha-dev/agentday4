"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Bell, Bot, ChevronLeft, ChevronRight, CircleUserRound, History,
  LibraryBig, LoaderCircle, Menu, MessageSquarePlus, Paperclip, Send, Settings, Trash2,
} from "lucide-react";
import { api, AgentToolEvent } from "../lib/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  toolEvents?: AgentToolEvent[];
  fallback?: boolean;
  responseMode?: "agent" | "unavailable";
  artifactVersion?: string;
};
type Conversation = { id: string; title: string; createdAt: string; updatedAt: string; messages: ChatMessage[] };

const STORAGE_KEY = "lexflow.local-conversations.ver2";
const VERSION_KEY = "lexflow.selected-agent-version";
const UNAVAILABLE_REPLY = "Không thể kết nối LexFlow Agent ver2. Hãy kiểm tra Agent API, OCR backend và khóa model provider; hệ thống không tự tạo câu trả lời thay thế.";
const suggestions = ["Quy định về hợp đồng lao động", "Luật doanh nghiệp mới nhất", "Thủ tục đăng ký sở hữu trí tuệ"];

function newId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}

export default function ChatWorkspace() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [hydrated, setHydrated] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<"v0" | "v1" | "v2">("v2");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        const parsed = stored ? JSON.parse(stored) as Conversation[] : [];
        setConversations(parsed);
        setActiveId(parsed[0]?.id ?? null);
        const savedVersion = localStorage.getItem(VERSION_KEY);
        if (savedVersion === "v0" || savedVersion === "v1" || savedVersion === "v2") setSelectedVersion(savedVersion);
      } catch { setConversations([]); }
      setHydrated(true);
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations, hydrated]);

  const active = useMemo(() => conversations.find((item) => item.id === activeId) ?? null, [conversations, activeId]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [active?.messages.length]);

  const startNew = () => { setActiveId(null); setInput(""); };
  const switchVersion = (version: "v0" | "v1" | "v2") => {
    if (sending) return;
    setSelectedVersion(version);
    localStorage.setItem(VERSION_KEY, version);
    setActiveId(null);
    setInput("");
  };
  const removeConversation = (id: string) => {
    setConversations((items) => items.filter((item) => item.id !== id));
    if (activeId === id) setActiveId(null);
  };

  const sendMessage = async (event?: FormEvent, preset?: string) => {
    event?.preventDefault();
    const content = (preset ?? input).trim();
    if (!content || sending) return;
    const now = new Date().toISOString();
    const userMessage: ChatMessage = { id: newId(), role: "user", content, createdAt: now };
    const conversationId = active?.id ?? newId();
    const history = active?.messages ?? [];
    if (!active) {
      const conversation: Conversation = {
        id: conversationId, title: content.slice(0, 54), createdAt: now, updatedAt: now,
        messages: [userMessage],
      };
      setConversations((items) => [conversation, ...items]);
      setActiveId(conversation.id);
    } else {
      setConversations((items) => items.map((item) => item.id === active.id ? { ...item, updatedAt: now, messages: [...item.messages, userMessage] } : item));
    }
    setInput("");
    setSending(true);
    let assistantMessage: ChatMessage;
    try {
      const messages = [...history, userMessage]
        .filter((message) => !message.fallback)
        .slice(-12)
        .map(({ role, content: messageContent }) => ({ role, content: messageContent }));
      const result = await api.chat(messages, selectedVersion);
      assistantMessage = {
        id: newId(),
        role: "assistant",
        createdAt: new Date().toISOString(),
        content: result.assistant_text || UNAVAILABLE_REPLY,
        toolEvents: result.tool_events ?? [],
        fallback: !result.assistant_text,
        responseMode: result.mode ?? "agent",
        artifactVersion: result.artifact_version ?? result.requested_version ?? selectedVersion,
      };
    } catch {
      assistantMessage = {
        id: newId(),
        role: "assistant",
        content: UNAVAILABLE_REPLY,
        createdAt: new Date().toISOString(),
        fallback: true,
      };
    } finally {
      setSending(false);
    }
    setConversations((items) => items.map((item) => item.id === conversationId ? {
      ...item,
      updatedAt: assistantMessage.createdAt,
      messages: [...item.messages, assistantMessage],
    } : item));
  };

  return <div className="chat-app">
    <div className="chat-atmosphere" aria-hidden="true" />
    <header className="design-header">
      <div className="header-brand-group">
        <button className="plain-icon blue" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Đóng mở thanh điều hướng"><Menu size={22}/></button>
        <Link href="/" className="design-brand"><span>L</span><div><strong>LexFlow</strong><small>LEGAL INTELLIGENCE</small></div></Link>
      </div>
      <div className="header-actions">
        <div className="version-switch" aria-label="Chọn phiên bản agent">
          {(["v0", "v1", "v2"] as const).map((version) => <button key={version} type="button" disabled={sending} aria-pressed={selectedVersion === version} className={selectedVersion === version ? "active" : ""} onClick={() => switchVersion(version)}>{version.toUpperCase()}</button>)}
        </div>
        <span className="api-badge"><i/> {selectedVersion.toUpperCase()} · RAG Agent</span>
        <button className="plain-icon" aria-label="Thông báo"><Bell size={20}/></button>
        <button className="plain-icon" aria-label="Tài khoản"><CircleUserRound size={22}/></button>
      </div>
    </header>

    <div className="chat-body">
      <aside className={`design-sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <nav>
          <button className="sidebar-item active" onClick={startNew}><MessageSquarePlus size={20}/><span>Hỏi đáp mới</span></button>
          <button className="sidebar-item" onClick={() => setHistoryOpen(!historyOpen)}><History size={20}/><span>Lịch sử hội thoại</span>{historyOpen ? <ChevronLeft className="nav-caret" size={14}/> : <ChevronRight className="nav-caret" size={14}/>}</button>
          {historyOpen && <div className="conversation-list">
            {conversations.map((item) => <button key={item.id} className={activeId === item.id ? "selected" : ""} onClick={() => setActiveId(item.id)}><span>{item.title}</span><i onClick={(event) => { event.stopPropagation(); removeConversation(item.id); }} title="Xóa hội thoại"><Trash2 size={13}/></i></button>)}
            {conversations.length === 0 && <small>Chưa có hội thoại</small>}
          </div>}
          <Link className="sidebar-item" href="/library/documents"><LibraryBig size={20}/><span>Thư viện văn bản</span></Link>
          <button className="sidebar-item settings-item"><Settings size={20}/><span>Cài đặt</span></button>
        </nav>
      </aside>

      <main className={`chat-main ${active ? "has-messages" : ""}`}>
        {active ? <div className="message-scroll">
          <div className="chat-thread-title"><span>HỘI THOẠI CỤC BỘ</span><h1>{active.title}</h1></div>
          {active.messages.map((message) => <div key={message.id} className={`message-row ${message.role}`}>
            {message.role === "assistant" && <span className="assistant-avatar"><Bot size={17}/></span>}
            <div className="message-bubble">
              {message.content}
              {message.role === "assistant" && <small>{message.fallback ? "Không thể kết nối Agent API" : message.responseMode === "unavailable" ? "Provider chưa sẵn sàng · không tạo câu trả lời thay thế" : `${message.artifactVersion ?? selectedVersion} · Đã dùng ${message.toolEvents?.length ?? 0} tool call`}</small>}
              {message.toolEvents && message.toolEvents.length > 0 && <details className="tool-trace"><summary>Căn cứ và tool đã gọi</summary>{message.toolEvents.map((toolEvent, index) => <div key={`${toolEvent.tool}-${index}`}><b>{toolEvent.tool}</b><code>{JSON.stringify(toolEvent.args)}</code></div>)}</details>}
            </div>
          </div>)}
          {sending && <div className="message-row assistant"><span className="assistant-avatar"><Bot size={17}/></span><div className="message-bubble agent-thinking"><LoaderCircle className="spin" size={16}/> Đang tra cứu và kiểm chứng căn cứ…</div></div>}
          <div ref={bottomRef}/>
        </div> : <div className="chat-welcome">
          <span className="welcome-kicker">TRỢ LÝ PHÁP LÝ</span>
          <h1>Tôi có thể giúp gì cho bạn?</h1>
          <p>Hỏi đáp pháp luật, tra cứu văn bản hoặc đưa tài liệu mới vào thư viện.</p>
        </div>}

        <div className={`chat-composer-area ${active ? "docked" : "centered"}`}>
          <form className="chat-composer" onSubmit={sendMessage}>
            <Link href="/library/upload" className="composer-attach" aria-label="Tải tài liệu"><Paperclip size={21}/></Link>
            <textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} placeholder="Nhập câu hỏi pháp lý, tải lên tài liệu hoặc dán văn bản..." rows={1}/>
            <button type="submit" aria-label="Gửi câu hỏi" disabled={sending}>{sending ? <LoaderCircle className="spin" size={21}/> : <Send size={21}/>}</button>
          </form>
          {!active && <div className="suggestion-row">{suggestions.map((item) => <button key={item} onClick={() => sendMessage(undefined, item)}>{item}</button>)}</div>}
          <div className="maintenance-note">Đang test {selectedVersion.toUpperCase()}. Chuyển version sẽ bắt đầu hội thoại sạch; V2 là bản OCR/RAG hoàn chỉnh.</div>
        </div>
      </main>
    </div>
  </div>;
}
