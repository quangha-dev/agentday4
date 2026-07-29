"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  BookOpen, CalendarDays, ChevronDown, ChevronRight, CircleHelp, ExternalLink,
  FileDown, FileText, Landmark, LoaderCircle, LocateFixed, Search, Sparkles, UserRound, X,
} from "lucide-react";
import StatusBadge from "./StatusBadge";
import { api, DocumentItem, LegalNode, SearchResult } from "../lib/api";

const typeNames: Record<string, string> = { part: "Phần", chapter: "Chương", section: "Mục", subsection: "Tiểu mục", article: "Điều", clause: "Khoản", point: "Điểm", document_content: "Nội dung" };

function TreeItem({ node, selected, onSelect }: { node: LegalNode; selected: string | null; onSelect: (node: LegalNode) => void }) {
  const [open, setOpen] = useState(!["clause", "point"].includes(node.node_type));
  return <div className={`legal-tree-level type-${node.node_type}`}>
    <button className={selected === node.id ? "active" : ""} onClick={() => onSelect(node)}>
      <span className="tree-expander" onClick={(event) => { event.stopPropagation(); setOpen(!open); }}>{node.children.length ? open ? <ChevronDown size={14}/> : <ChevronRight size={14}/> : <i/>}</span>
      <span><b>{typeNames[node.node_type] ?? node.node_type} {node.marker}</b>{node.title && <small>{node.title}</small>}</span>
    </button>
    {open && node.children.length > 0 && <div className="legal-tree-children">{node.children.map((child) => <TreeItem key={child.id} node={child} selected={selected} onSelect={onSelect}/>)}</div>}
  </div>;
}

export default function LegalLibrary() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [tree, setTree] = useState<LegalNode[]>([]);
  const [selected, setSelected] = useState<LegalNode | null>(null);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("semantic");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  const document = documents.find((item) => item.id === documentId) ?? null;
  useEffect(() => { api.documents().then((items) => { setDocuments(items); const ready = items.find((item) => item.status === "INDEXED") ?? items[0]; if (ready) setDocumentId(ready.id); }).catch(() => setError("Backend thư viện hiện không khả dụng. Vui lòng thử lại sau.")); }, []);
  useEffect(() => { if (!documentId) return; api.tree(documentId).then((nodes) => { setTree(nodes); setSelected(nodes[0] ?? null); }).catch(() => { setTree([]); setSelected(null); }); }, [documentId]);

  const counts = useMemo(() => {
    const total: Record<string, number> = {};
    const walk = (nodes: LegalNode[]) => nodes.forEach((node) => { total[node.node_type] = (total[node.node_type] ?? 0) + 1; walk(node.children); });
    walk(tree); return total;
  }, [tree]);

  const submitSearch = async (event: FormEvent) => {
    event.preventDefault(); if (!query.trim()) return;
    setSearching(true); setError("");
    try { setResults(await api.search(query, mode, documentId || undefined)); }
    catch { setError("Không thể kết nối dịch vụ tra cứu. Dữ liệu tài liệu vẫn được giữ nguyên."); }
    finally { setSearching(false); }
  };

  const selectResult = (result: SearchResult) => setSelected({ id: result.legal_node_id, document_id: result.document_id, parent_id: null, node_type: result.node_type, marker: result.marker, title: result.title, content: result.content, full_path: result.full_path, order_index: 0, page_start: result.page_start, page_end: result.page_end, bbox_spans: [], children: [] });

  return <main className="documents-page">
    <section className="library-page-title documents-title">
      <div><span className="section-eyebrow">KHO DỮ LIỆU ĐÃ NẠP</span><h1>Tài liệu pháp luật</h1><p>Duyệt phiên bản, tra cứu cấu trúc và đối chiếu từng kết quả về PDF nguồn.</p></div>
      <div className="document-counts"><span><b>{documents.length}</b><small>Văn bản</small></span><i/><span><b>{counts.article ?? 0}</b><small>Điều luật</small></span><i/><span><b>{counts.clause ?? 0}</b><small>Khoản</small></span></div>
    </section>

    <form className="document-search" onSubmit={submitSearch}>
      <Search size={20}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tra cứu nội dung trong văn bản đang chọn…"/>{query && <button type="button" onClick={() => { setQuery(""); setResults([]); }}><X size={16}/></button>}<select value={mode} onChange={(event) => setMode(event.target.value)}><option value="semantic">Semantic</option><option value="exact">Chính xác</option><option value="keyword">Từ khóa</option><option value="hybrid">Kết hợp</option></select><button className="search-submit" disabled={searching}>{searching ? <LoaderCircle className="spin" size={17}/> : <Sparkles size={17}/>} Tra cứu</button>
    </form>
    {error && <div className="notice notice-error">{error}</div>}

    {documents.length === 0 ? <section className="empty-library"><BookOpen size={36}/><h2>Chưa có tài liệu trong thư viện</h2><p>Tải lên PDF, OCR và xử lý cấu trúc trước khi tra cứu.</p><Link href="/library/upload">Thêm tài liệu đầu tiên</Link></section> : <section className="document-browser">
      <aside className="stored-documents">
        <div className="browser-heading"><span>VĂN BẢN ĐÃ THÊM</span><b>{documents.length}</b></div>
        <div className="stored-list">{documents.map((item) => <button key={item.id} className={item.id === documentId ? "active" : ""} onClick={() => { setDocumentId(item.id); setResults([]); }}><span className="stored-icon"><FileText size={18}/></span><span className="stored-copy"><strong>{item.document_number || item.title}</strong><small>{item.document_type || item.original_filename}</small><em>v{item.version_number} · {item.page_count} trang</em></span><StatusBadge status={item.status}/></button>)}</div>
      </aside>

      <aside className="document-structure">
        <div className="browser-heading"><span>{results.length ? "KẾT QUẢ TRA CỨU" : "CẤU TRÚC VĂN BẢN"}</span>{results.length > 0 && <button onClick={() => setResults([])}>Xem cây</button>}</div>
        {results.length ? <div className="result-list">{results.map((item) => <button key={`${item.legal_node_id}-${item.score}`} className={selected?.id === item.legal_node_id ? "active" : ""} onClick={() => selectResult(item)}><span>{Math.round(item.score * 100)}%</span><strong>{item.full_path}</strong><small>{item.title || item.content.slice(0, 110)}</small></button>)}</div> : tree.length ? <div className="legal-tree">{tree.map((node) => <TreeItem key={node.id} node={node} selected={selected?.id ?? null} onSelect={setSelected}/>)}</div> : <div className="browser-empty"><BookOpen size={24}/><p>Văn bản chưa được phân tích cấu trúc.</p><Link href="/library/upload">Mở trang xử lý</Link></div>}
      </aside>

      <article className="document-detail">
        {document && <div className="legal-metadata-strip"><div><span>SỐ KÝ HIỆU</span><strong>{document.document_number || "Chưa cập nhật"}</strong></div><div><CalendarDays size={16}/><span>Ban hành<small>{document.issued_date || "—"}</small></span></div><div><Landmark size={16}/><span>Cơ quan<small>{document.issuing_authority || "—"}</small></span></div><div><UserRound size={16}/><span>Người ký<small>{document.signer || "—"}</small></span></div></div>}
        {selected ? <>
          <div className="detail-path"><span>{selected.full_path}</span><a href={document ? api.exportUrl(document.id) : "#"} title="Xuất JSON"><FileDown size={16}/></a></div>
          <div className="detail-content"><span className="node-label">{typeNames[selected.node_type] ?? selected.node_type} {selected.marker}</span><h2>{selected.title || selected.full_path}</h2>{selected.content ? selected.content.split("\n").map((line, index) => <p key={index}>{line}</p>) : <p className="muted">Chọn Khoản hoặc Điểm bên dưới để xem nội dung chi tiết.</p>}</div>
          <div className="source-reference"><LocateFixed size={18}/><div><strong>Nguồn đối chiếu</strong><small>Trang {selected.page_start}{selected.page_end !== selected.page_start ? `–${selected.page_end}` : ""} · phiên bản {document?.version_number}</small></div><a href={api.fileUrl(selected.document_id, selected.page_start)} target="_blank" rel="noreferrer">Mở PDF <ExternalLink size={13}/></a></div>
          <iframe className="source-pdf" title={`PDF trang ${selected.page_start}`} src={api.fileUrl(selected.document_id, selected.page_start)}/>
        </> : <div className="detail-empty"><CircleHelp size={32}/><h2>Chọn một điều khoản</h2><p>Nội dung và PDF nguồn sẽ hiển thị tại đây.</p></div>}
      </article>
    </section>}
  </main>;
}

