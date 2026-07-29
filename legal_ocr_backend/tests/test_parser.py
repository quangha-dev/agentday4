from app.services.parser import PageText, parse_legal_structure


def test_parser_builds_article_clause_point_tree_and_pages() -> None:
    pages = [
        PageText(1, "CHƯƠNG I\nQuy định chung\nĐiều 1. Phạm vi điều chỉnh\n1. Luật này quy định:\na) Quyền của cá nhân."),
        PageText(2, "Điều 2. Đối tượng áp dụng\n1. Cơ quan, tổ chức và cá nhân có liên quan."),
    ]
    roots = parse_legal_structure(pages)
    chapter = roots[0]
    assert chapter["node_type"] == "chapter"
    first_article = chapter["children"][0]
    assert first_article["node_type"] == "article"
    assert first_article["marker"] == "1"
    assert first_article["children"][0]["node_type"] == "clause"
    assert first_article["children"][0]["children"][0]["node_type"] == "point"
    assert chapter["children"][1]["page_start"] == 2

