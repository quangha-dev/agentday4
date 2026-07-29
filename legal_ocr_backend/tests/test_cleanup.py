from app.services.cleanup import clean_page_text, find_repeated_margin_lines


def test_cleanup_preserves_legal_markers_and_removes_page_number() -> None:
    source = "Điều 12. Quyền của người lao động\n\n  1.  Nội dung   khoản.\n--- 12 ---"
    cleaned = clean_page_text(source)
    assert "Điều 12." in cleaned
    assert "1. Nội dung khoản." in cleaned
    assert "--- 12 ---" not in cleaned


def test_detect_repeated_header() -> None:
    pages = [f"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nNội dung {index}\n{index}" for index in range(1, 5)]
    repeated = find_repeated_margin_lines(pages)
    assert "cộng hòa xã hội chủ nghĩa việt nam" in repeated

