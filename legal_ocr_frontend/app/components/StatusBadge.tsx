const labels: Record<string, string> = {
  UPLOADED: "Đã tải lên", EXTRACTING: "Đang OCR", OCR_READY: "Chờ kiểm duyệt",
  CLEANED: "Đã làm sạch", REVIEWED: "Đã xác nhận", PARSED: "Đã phân cấp",
  INDEXING: "Đang lập chỉ mục", INDEXED: "Sẵn sàng tra cứu", FAILED: "Có lỗi",
};

export default function StatusBadge({ status }: { status: string }) {
  return <span className={`status status-${status.toLowerCase()}`}><i />{labels[status] ?? status}</span>;
}

