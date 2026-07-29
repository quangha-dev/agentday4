"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft, Files, FileUp, Radio } from "lucide-react";

export default function LibraryShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return <div className="library-shell">
    <header className="library-topbar">
      <div className="library-brand-row">
        <Link href="/" className="back-chat"><ArrowLeft size={17}/> Trở về trang chat</Link>
        <span className="library-divider"/>
        <Link href="/library/documents" className="design-brand small"><span>L</span><div><strong>LexFlow</strong><small>THƯ VIỆN PHÁP LUẬT</small></div></Link>
      </div>
      <span className="api-badge"><Radio size={14}/> OCR API</span>
    </header>
    <nav className="library-tabs" aria-label="Các trang thư viện">
      <Link className={pathname.startsWith("/library/upload") ? "active" : ""} href="/library/upload"><FileUp size={17}/><span>Thêm & xử lý PDF</span></Link>
      <Link className={pathname.startsWith("/library/documents") ? "active" : ""} href="/library/documents"><Files size={17}/><span>Tài liệu đã thêm</span></Link>
    </nav>
    <div className="library-content">{children}</div>
  </div>;
}

