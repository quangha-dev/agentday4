"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpenText, FileScan, Orbit, Wifi } from "lucide-react";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="LexFlow trang chủ">
          <span className="brand-mark"><Orbit size={19} strokeWidth={2.4} /></span>
          <span><strong>LexFlow</strong><small>LEGAL INTELLIGENCE</small></span>
        </Link>
        <nav className="primary-nav" aria-label="Điều hướng chính">
          <Link className={pathname === "/" ? "active" : ""} href="/"><FileScan size={17} /> OCR Studio</Link>
          <Link className={pathname.startsWith("/library") ? "active" : ""} href="/library"><BookOpenText size={17} /> Kho dữ liệu</Link>
        </nav>
        <div className="system-pill"><Wifi size={14} /> API độc lập</div>
      </header>
      {children}
    </div>
  );
}

