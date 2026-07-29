import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const incoming = await headers();
  const host = incoming.get("host") ?? "localhost:3000";
  const protocol = incoming.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const imageUrl = `${protocol}://${host}/og-chat.png`;
  const title = "LexFlow — Chat và thư viện pháp luật";
  const description = "OCR, kiểm duyệt song song PDF–text, quản lý phiên bản và tra cứu ngữ nghĩa văn bản pháp luật.";
  return {
    title,
    description,
    openGraph: { title, description, type: "website", locale: "vi_VN", images: [{ url: imageUrl, width: 1693, height: 929, alt: "LexFlow — OCR, kiểm duyệt và tra cứu pháp luật" }] },
    twitter: { card: "summary_large_image", title, description, images: [imageUrl] },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="vi"><body>{children}</body></html>;
}
