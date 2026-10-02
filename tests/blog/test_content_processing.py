from blog.content import extract_plain_text, generate_excerpt, render_markdown


def test_render_markdown_basic_formatting():
    md = "# Heading 1\n\nThis is **bold** and *italic* text with a [link](https://example.com)."
    html = render_markdown(md)

    assert "<h1>Heading 1</h1>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html
    assert 'href="https://example.com"' in html
    assert 'rel="noopener noreferrer"' in html


def test_render_markdown_disables_and_sanitizes_raw_html():
    malicious_md = (
        "Hello <script>alert('xss')</script> "
        "<img src=x onerror=alert(1)> "
        "<a href='javascript:alert(1)'>click me</a>"
    )
    html = render_markdown(malicious_md)

    # HTML tags inside markdown are escaped
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img" not in html
    assert "&lt;img" in html
    # javascript: scheme is stripped / not rendered as an active link
    assert 'href="javascript:' not in html


def test_extract_plain_text():
    md = "# Title Here\n\nParagraph with **bold**, [link](https://test.com), and `code`."
    text = extract_plain_text(md)

    assert "<" not in text
    assert ">" not in text
    assert "Title Here" in text
    assert "Paragraph with bold, link, and code." in text
    assert "\n" not in text  # Whitespace collapsed


def test_extract_plain_text_empty():
    assert extract_plain_text("") == ""
    assert extract_plain_text("   \n\n  ") == ""


def test_generate_excerpt_short_text():
    text = "Short plain text."
    excerpt = generate_excerpt(text, max_length=300)
    assert excerpt == text


def test_generate_excerpt_truncation_at_word_boundary():
    long_text = "word " * 100  # 500 characters
    excerpt = generate_excerpt(long_text, max_length=100)

    assert len(excerpt) <= 100
    assert excerpt.endswith("...")
    assert not excerpt.endswith(" ...")
    assert not excerpt.endswith("word... ")


def test_generate_excerpt_exact_boundary():
    text = "a" * 300
    assert generate_excerpt(text, max_length=300) == text
