"use client";

import { ChangeEvent, DragEvent, FormEvent, useEffect, useState } from "react";
import {
  ArrowLeftRight, Check, CheckCircle2, Download, ExternalLink, FileCheck2,
  FileJson, FileText, LoaderCircle, Play, Save, ScanLine, Sparkles, UploadCloud,
  WandSparkles,
} from "lucide-react";
import StatusBadge from "./StatusBadge";
import { API_BASE, api, DocumentItem, LegalMetadata, PageItem, SystemReadiness } from "../lib/api";

const apiOrigin = API_BASE.replace(/\/api\/v1\/?$/, "");
const initialMetadata: LegalMetadata = {
  document_number: "",
  issued_date: "",
  effective_date: "",
  document_type: "",
  issuing_authority: "",
  signer: "",
  summary: "",
};

export default function OcrStudio() {
  const [metadata, setMetadata] = useState<LegalMetadata>(initialMetadata);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [pages, setPages] = useState<PageItem[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [progress, setProgress] = useState(0);
  const [chunkResult, setChunkResult] = useState<{ count: number; strategy: string } | null>(null);
  const [readiness, setReadiness] = useState<SystemReadiness | null>(null);

  const page = pages[pageIndex] ?? null;
  const verifiedCount = pages.filter((item) => item.is_verified).length;
  const currentStep = !document ? 1 : pages.length === 0 ? 2 : chunkResult ? 4 : 3;

  useEffect(() => {
    api.readiness().then(setReadiness).catch(() => setReadiness(null));
  }, []);

  const refreshPages = async (documentId = document?.id) => {
    if (!documentId) return;
    const items = await api.pages(documentId);
    setPages(items);
    setPageIndex((value) => Math.min(value, Math.max(0, items.length - 1)));
  };

  useEffect(() => {
    if (!page) return;
    const pageText = page.verified_text ?? page.cleaned_text ?? page.raw_text;
    queueMicrotask(() => setText(pageText));
  }, [page]);

  const updateMetadata = (field: keyof LegalMetadata, value: string) => {
    setMetadata((current) => ({ ...current, [field]: value }));
  };

  const upload = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedFile) { setError("Vui lòng chọn một file PDF."); return; }
    setBusy("upload"); setError(""); setNotice("");
    try {
      const created = await api.upload(selectedFile, metadata);
      setDocument(created); setPages([]); setProgress(0);
      setNotice(`Đã lưu hồ sơ ${created.document_number} · phiên bản ${created.version_number}.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể tải file"); }
    finally { setBusy(""); }
  };

  const startOcr = async () => {
    if (!document) return;
    setBusy("ocr"); setError(""); setProgress(4);
    try {
      const currentReadiness = await api.readiness();
      setReadiness(currentReadiness);
      if (!currentReadiness.ocr.ready) throw new Error(currentReadiness.ocr.error?.message ?? "OCR chưa sẵn sàng");
      const job = await api.process(document.id);
      for (;;) {
        await new Promise((resolve) => setTimeout(resolve, 850));
        const state = await api.job(job.id);
        setProgress(state.progress); setNotice(state.message ?? "Đang OCR");
        if (state.status === "COMPLETED") break;
        if (state.status === "FAILED") throw new Error(state.message ?? "OCR thất bại");
      }
      await refreshPages(document.id);
      setDocument(await api.document(document.id));
      setNotice("OCR hoàn tất. Hãy đối chiếu PDF và văn bản theo từng trang.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "OCR thất bại"); }
    finally { setBusy(""); }
  };

  const runPageAction = async (label: string, action: () => Promise<PageItem>, success: string) => {
    setBusy(label); setError("");
    try { const updated = await action(); setPages((items) => items.map((item) => item.id === updated.id ? updated : item)); setNotice(success); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể xử lý trang"); }
    finally { setBusy(""); }
  };

  const cleanWithLlm = async () => {
    if (!page) return;
    setBusy("llm-clean"); setError("");
    try {
      const result = await api.cleanPageWithLlm(page.id);
      setPages((items) => items.map((item) => item.id === result.page.id ? result.page : item));
      setText(result.page.cleaned_text ?? result.page.raw_text);
      setNotice(result.warning ? `${result.warning} Phương thức: ${result.method}.` : `Đã làm sạch bằng ${result.method}.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "LLM cleanup thất bại"); }
    finally { setBusy(""); }
  };

  const verifyAllPages = async () => {
    const pendingPages = pages.filter((item) => !item.is_verified);
    if (pendingPages.length === 0) return;
    setBusy("verify-all"); setError("");
    try {
      let completed = 0;
      for (const item of pendingPages) {
        const content = item.id === page?.id
          ? text
          : item.verified_text ?? item.cleaned_text ?? item.raw_text;
        const updated = await api.verify(item.id, content);
        setPages((current) => current.map((candidate) => candidate.id === updated.id ? updated : candidate));
        completed += 1;
        setNotice(`Đang xác nhận trang: ${completed}/${pendingPages.length}.`);
      }
      setNotice(`Đã xác nhận tất cả ${pages.length} trang.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể xác nhận tất cả các trang");
    } finally {
      setBusy("");
    }
  };

  const processAndIndex = async () => {
    if (!document) return;
    setBusy("finalize"); setError(""); setChunkResult(null);
    try {
      if (verifiedCount !== pages.length) throw new Error(`Cần xác nhận đủ ${pages.length} trang trước khi xử lý dữ liệu.`);
      const parsed = await api.parse(document.id);
      setNotice(`${parsed.message}. Đang chia chunk theo cấu trúc pháp luật…`);
      const indexed = await api.index(document.id);
      setChunkResult({ count: indexed.indexed_chunks, strategy: indexed.chunk_strategy });
      setDocument({ ...document, status: "INDEXED" });
      setNotice(`Hoàn tất: ${indexed.indexed_articles} Điều, ${indexed.indexed_chunks} chunk đã lưu vào vector database.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể hoàn thiện dữ liệu"); }
    finally { setBusy(""); }
  };

  const reset = () => { setDocument(null); setPages([]); setSelectedFile(null); setChunkResult(null); setNotice(""); setError(""); };
  const imageUrl = page?.image_url ? `${apiOrigin}${page.image_url}` : "";

  return <main className="ingest-page">
    <section className="library-page-title">
      <div><span className="section-eyebrow">NẠP DỮ LIỆU PHÁP LÝ</span><h1>Thêm và xử lý văn bản</h1><p>OCR, kiểm duyệt từng trang và lập chỉ mục theo đúng cấu trúc luật.</p></div>
      {document && <button className="secondary-button" onClick={reset}>Thêm tài liệu khác</button>}
    </section>

    <ol className="process-steps">{["Thông tin", "OCR", "Đối chiếu", "Lưu dữ liệu"].map((label, index) => <li key={label} className={currentStep >= index + 1 ? "active" : ""}><span>{currentStep > index + 1 ? <Check size={13}/> : index + 1}</span><b>{label}</b></li>)}</ol>
    {(notice || error) && <div className={`notice ${error ? "notice-error" : ""}`}>{error || notice}</div>}
    {readiness && !readiness.ocr.ready && <div className="notice notice-error">OCR chưa sẵn sàng: {readiness.ocr.error?.message}</div>}
    {busy === "ocr" && <div className="progress-track"><span style={{ width: `${progress}%` }}/><small>{progress}%</small></div>}

    {!document ? <form className="metadata-upload-grid" onSubmit={upload}>
      <section className="form-card">
        <div className="card-heading"><span>01</span><div><h2>Thông tin văn bản</h2><p>Metadata này được gắn vào mọi chunk để quản lý phiên bản và truy xuất nguồn.</p></div></div>
        <div className="legal-form-grid">
          <label><span>Số ký hiệu *</span><input required value={metadata.document_number} onChange={(e) => updateMetadata("document_number", e.target.value)} placeholder="66.24/2026/NQ-CP"/></label>
          <label><span>Loại văn bản *</span><input required value={metadata.document_type} onChange={(e) => updateMetadata("document_type", e.target.value)} placeholder="Nghị quyết"/></label>
          <label><span>Ngày ban hành *</span><input required type="date" value={metadata.issued_date} onChange={(e) => updateMetadata("issued_date", e.target.value)}/></label>
          <label><span>Ngày có hiệu lực *</span><input required type="date" value={metadata.effective_date} onChange={(e) => updateMetadata("effective_date", e.target.value)}/></label>
          <label><span>Cơ quan ban hành *</span><input required value={metadata.issuing_authority} onChange={(e) => updateMetadata("issuing_authority", e.target.value)} placeholder="Chính phủ"/></label>
          <label><span>Người ký *</span><input required value={metadata.signer} onChange={(e) => updateMetadata("signer", e.target.value)} placeholder="Nguyễn Văn Thắng"/></label>
          <label className="full"><span>Trích yếu *</span><textarea required value={metadata.summary} onChange={(e) => updateMetadata("summary", e.target.value)} rows={4}/></label>
        </div>
      </section>
      <section className="form-card upload-card">
        <div className="card-heading"><span>02</span><div><h2>File nguồn</h2><p>PDF gốc được giữ bất biến để đối chiếu.</p></div></div>
        <label className={`file-drop ${dragging ? "dragging" : ""}`} onDragOver={(e: DragEvent) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(e: DragEvent) => { e.preventDefault(); setDragging(false); setSelectedFile(e.dataTransfer.files[0] ?? null); }}>
          {selectedFile ? <><FileCheck2 size={34}/><strong>{selectedFile.name}</strong><small>{(selectedFile.size / 1024 / 1024).toFixed(2)} MB · sẵn sàng tải lên</small></> : <><UploadCloud size={34}/><strong>Thả PDF vào đây</strong><small>Hoặc bấm để chọn file · tối đa 100 MB</small></>}
          <input type="file" accept="application/pdf" hidden onChange={(e: ChangeEvent<HTMLInputElement>) => setSelectedFile(e.target.files?.[0] ?? null)}/>
        </label>
        <button className="primary-button wide" disabled={!!busy || !selectedFile}>{busy === "upload" ? <LoaderCircle className="spin" size={17}/> : <UploadCloud size={17}/>} Lưu hồ sơ & tải PDF</button>
        <div className="data-promise"><span><Check/> PDF gốc bất biến</span><span><Check/> Tự động tăng version cùng số ký hiệu</span><span><Check/> Metadata đi cùng mọi chunk</span></div>
      </section>
    </form> : <>
      <section className="document-context">
        <span className="document-file-icon"><FileText size={21}/></span>
        <div className="document-main"><strong>{document.document_number}</strong><span>{document.document_type} · {document.issuing_authority}</span></div>
        <div className="document-facts"><span>Ban hành<b>{document.issued_date}</b></span><span>Hiệu lực<b>{document.effective_date}</b></span><span>Phiên bản<b>v{document.version_number}</b></span></div>
        <StatusBadge status={document.status}/>
      </section>

      {pages.length === 0 ? <section className="ocr-ready-card"><span><ScanLine size={36}/></span><div><h2>Hồ sơ đã sẵn sàng để OCR</h2><p>Hệ thống tự chọn text layer hoặc Tesseract theo từng trang PDF.</p></div><button className="primary-button" onClick={startOcr} disabled={!!busy}>{busy === "ocr" ? <LoaderCircle className="spin" size={17}/> : <Play size={17}/>} Bắt đầu OCR</button></section> : <>
        <section className="review-toolbar"><div><span>ĐỐI CHIẾU TỪNG TRANG</span><strong>{verifiedCount}/{pages.length} trang đã xác nhận</strong></div><div className="review-toolbar-actions"><button className="verify-all-button" onClick={verifyAllPages} disabled={!!busy || verifiedCount === pages.length}>{busy === "verify-all" ? <LoaderCircle className="spin" size={15}/> : <CheckCircle2 size={15}/>} {verifiedCount === pages.length ? "Đã xác nhận tất cả" : "Xác nhận tất cả"}</button><a href={api.fileUrl(document.id, page?.page_number ?? 1)} target="_blank" rel="noreferrer"><ExternalLink size={15}/> Mở PDF gốc</a></div></section>
        <section className="ocr-review-grid">
          <aside className="review-pages"><span>TRANG</span>{pages.map((item, index) => <button key={item.id} className={index === pageIndex ? "active" : ""} onClick={() => { setPageIndex(index); setShowDiff(false); }}><b>{String(item.page_number).padStart(2, "0")}</b><small>{item.classification}</small>{item.is_verified && <i><Check size={11}/></i>}</button>)}</aside>
          <section className="pdf-page-panel"><div className="review-panel-head"><span>PDF · TRANG {page?.page_number}</span><b>{page?.confidence ? `${Math.round(page.confidence)}% tin cậy` : "Chưa có độ tin cậy"}</b></div><div className="pdf-page-scroll">{imageUrl ? <img src={imageUrl} alt={`PDF trang ${page?.page_number}`}/> : <span>Không có ảnh trang</span>}</div></section>
          <section className="text-page-panel"><div className="review-panel-head"><span>TEXT · TRANG {page?.page_number}</span><button className={showDiff ? "active" : ""} onClick={() => setShowDiff(!showDiff)}><ArrowLeftRight size={15}/> So sánh</button></div>{showDiff ? <div className="text-diff"><div><small>BẢN OCR THÔ</small><pre>{page?.raw_text}</pre></div><div><small>BẢN ĐANG DUYỆT</small><pre>{text}</pre></div></div> : <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck={false}/>}<div className="text-stats"><span>{text.length.toLocaleString("vi-VN")} ký tự</span><span>{page?.bounding_boxes.length ?? 0} vùng nhận dạng</span></div><div className="text-actions"><button onClick={cleanWithLlm} disabled={!!busy}><WandSparkles size={16}/> LLM xoá ký tự thừa</button><button onClick={() => page && runPageAction("save", () => api.saveText(page.id, text), "Đã lưu chỉnh sửa trang." )} disabled={!!busy}><Save size={16}/> Lưu</button><button className="primary" onClick={() => page && runPageAction("verify", () => api.verify(page.id, text), "Đã xác nhận trang." )} disabled={!!busy}><CheckCircle2 size={16}/> Xác nhận</button></div></section>
        </section>

        <section className="finalize-card"><div className="finalize-icon"><FileJson size={24}/></div><div><span>HIERARCHICAL LEGAL CHUNKING · VER2</span><h2>Phân tích cấu trúc và lưu vector database</h2><p>Mỗi chunk giữ metadata riêng và nội dung luật sạch theo Phần / Chương / Mục / Điều / Khoản / Điểm. Chỉ xử lý khi mọi trang đã được xác nhận.</p>{verifiedCount !== pages.length && <small>Còn {pages.length - verifiedCount} trang chưa xác nhận.</small>}{chunkResult && <small>Đã tạo {chunkResult.count} chunk · {chunkResult.strategy}</small>}</div><div className="finalize-actions"><a href={api.exportUrl(document.id)}><Download size={16}/> Xuất JSON</a><button onClick={processAndIndex} disabled={!!busy || verifiedCount !== pages.length}>{busy === "finalize" ? <LoaderCircle className="spin" size={17}/> : <Sparkles size={17}/>} Xử lý & lưu dữ liệu</button></div></section>
      </>}
    </>}
  </main>;
}
