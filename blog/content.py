import html
import re

import markdown_it
import nh3

_md = markdown_it.MarkdownIt("commonmark", {"html": False})

SAFE_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "del",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}

SAFE_ATTRIBUTES = {
    "a": {"href", "title"},
    "code": {"class"},
}

SAFE_URL_SCHEMES = {"http", "https", "mailto"}


def render_markdown(content_markdown: str) -> str:
    """
    Renders Markdown content to sanitized HTML.
    HTML tags within markdown are disabled and output is sanitized with nh3.
    """
    if not content_markdown:
        return ""

    raw_html = _md.render(content_markdown)
    sanitized_html = nh3.clean(
        raw_html,
        tags=SAFE_TAGS,
        attributes=SAFE_ATTRIBUTES,
        url_schemes=SAFE_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )
    return sanitized_html


def extract_plain_text(content_markdown: str) -> str:
    """
    Extracts clean, normalized plain text from Markdown for search indexing and excerpting.
    All tags and entities are stripped, and whitespace is collapsed.
    """
    if not content_markdown:
        return ""

    raw_html = _md.render(content_markdown)
    stripped = nh3.clean(raw_html, tags=set())
    unescaped = html.unescape(stripped)
    collapsed = re.sub(r"\s+", " ", unescaped).strip()
    return collapsed


def generate_excerpt(plain_text: str, max_length: int = 300) -> str:
    """
    Generates a concise excerpt from plain text, safely bounded by max_length.
    Truncates at a word boundary when possible.
    """
    if not plain_text or len(plain_text) <= max_length:
        return plain_text

    target_len = max_length - 3  # room for ellipsis
    truncated = plain_text[:target_len]

    last_space = truncated.rfind(" ")
    if last_space > target_len // 2:
        truncated = truncated[:last_space]

    return f"{truncated.rstrip()}..."
