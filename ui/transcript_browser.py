import html as _html
import re

import streamlit as st
import streamlit.components.v1 as _components

_BROWSER_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #ffffff; --text: #1a1a1a; --border: #e0e0e0;
  --input-bg: #ffffff; --input-border: #cccccc; --input-text: #1a1a1a;
  --btn-bg: #ffffff; --btn-hover: #f5f5f5; --btn-border: #cccccc; --btn-text: #1a1a1a;
  --muted: #666666;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1e1e1e; --text: #e0e0e0; --border: #444444;
    --input-bg: #2d2d2d; --input-border: #555555; --input-text: #e0e0e0;
    --btn-bg: #2d2d2d; --btn-hover: #3d3d3d; --btn-border: #555555; --btn-text: #e0e0e0;
    --muted: #999999;
  }
}
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; background: var(--bg); color: var(--text); }
.search-bar { display: flex; align-items: center; gap: 6px; padding: 6px 8px; border-bottom: 1px solid var(--border); position: sticky; top: 0; background: var(--bg); z-index: 10; }
.search-bar input { flex: 1; padding: 5px 8px; border: 1px solid var(--input-border); border-radius: 4px; font-size: 13px; outline: none; background: var(--input-bg); color: var(--input-text); }
.search-bar input:focus { border-color: #4a9eff; }
.match-count { font-size: 12px; color: var(--muted); min-width: 80px; text-align: center; }
.nav-btn { padding: 4px 10px; cursor: pointer; border: 1px solid var(--btn-border); border-radius: 4px; background: var(--btn-bg); color: var(--btn-text); font-size: 16px; line-height: 1; }
.nav-btn:hover { background: var(--btn-hover); }
.nav-btn:disabled { opacity: 0.4; cursor: default; }
.transcript { height: calc(100vh - 46px); overflow-y: auto; padding: 8px; }
p { margin-bottom: 10px; line-height: 1.6; }
mark { background: #fff59d; border-radius: 2px; padding: 0 1px; }
mark.current { background: #ff9800; color: white; }
.jargon { border-bottom: 1px dotted #4a9eff; cursor: help; }
"""

_BROWSER_JS = """
var currentIndex = 0;
var marks = [];

function clearHighlights() {
  document.querySelectorAll('mark').forEach(function(m) {
    var parent = m.parentNode;
    parent.replaceChild(document.createTextNode(m.textContent), m);
    parent.normalize();
  });
  marks = [];
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
}

function highlightText(root, query) {
  var regex = new RegExp(escapeRegex(query), 'gi');
  var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
  var nodes = [];
  var node;
  while (node = walker.nextNode()) { nodes.push(node); }
  nodes.forEach(function(textNode) {
    var text = textNode.textContent;
    regex.lastIndex = 0;
    if (!regex.test(text)) { return; }
    regex.lastIndex = 0;
    var frag = document.createDocumentFragment();
    var lastIndex = 0;
    var match;
    while ((match = regex.exec(text)) !== null) {
      frag.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
      var mark = document.createElement('mark');
      mark.textContent = match[0];
      frag.appendChild(mark);
      marks.push(mark);
      lastIndex = match.index + match[0].length;
    }
    frag.appendChild(document.createTextNode(text.slice(lastIndex)));
    textNode.parentNode.replaceChild(frag, textNode);
  });
}

function updateUI() {
  var q = document.getElementById('search-input').value;
  var countEl = document.getElementById('match-count');
  var prevBtn = document.getElementById('prev-btn');
  var nextBtn = document.getElementById('next-btn');
  if (!q) {
    countEl.textContent = '';
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    return;
  }
  if (marks.length === 0) {
    countEl.textContent = '0 matches';
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    return;
  }
  marks.forEach(function(m, i) { m.className = i === currentIndex ? 'current' : ''; });
  marks[currentIndex].scrollIntoView({ block: 'center', behavior: 'smooth' });
  countEl.textContent = (currentIndex + 1) + ' / ' + marks.length;
  prevBtn.disabled = false;
  nextBtn.disabled = false;
}

function onSearch() {
  clearHighlights();
  currentIndex = 0;
  var q = document.getElementById('search-input').value;
  if (q.length >= 2) {
    highlightText(document.getElementById('transcript'), q);
  }
  updateUI();
}

function navigate(dir) {
  if (!marks.length) { return; }
  currentIndex = (currentIndex + dir + marks.length) % marks.length;
  updateUI();
}

document.getElementById('search-input').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') { navigate(e.shiftKey ? -1 : 1); }
});
"""


def _apply_jargon_tooltips(escaped_text: str, jargon: dict[str, str]) -> str:
    """Wrap recognised jargon terms in tooltip spans within already-HTML-escaped text.

    Terms are sorted longest-first so multi-word phrases take priority over
    single-word subterms.  Text inside existing HTML tags is never modified,
    which prevents double-wrapping if the function is called more than once.
    """
    if not jargon:
        return escaped_text

    sorted_terms = sorted(jargon.keys(), key=len, reverse=True)
    terms_pattern = r'(?<!\w)(' + '|'.join(re.escape(t) for t in sorted_terms) + r')(?!\w)'
    # Match either an HTML tag (group 1) or a jargon term (group 2).
    # HTML tags are passed through unchanged; only group-2 matches are wrapped.
    combined = re.compile(r'(<[^>]+>)|' + terms_pattern, re.IGNORECASE)

    def replacer(m: re.Match) -> str:
        if m.group(1) is not None:
            # It's an HTML tag — leave it untouched
            return m.group(1)
        matched = m.group(2)
        definition = jargon.get(matched.lower())
        if not definition:
            return matched
        escaped_def = _html.escape(definition, quote=True)
        return f'<span class="jargon" title="{escaped_def}">{matched}</span>'

    return combined.sub(replacer, escaped_text)


def render_transcript_browser(
    spans: list[tuple[str, str, str]],
    jargon: dict[str, str] | None = None,
    initial_search: str = "",
) -> None:
    """Render the searchable HTML transcript browser.

    initial_search: pre-populate the search box and run a search on load.
    """
    st.markdown("### 📄 Transcript")

    if not spans:
        st.info("No transcript data available.")
        return

    jargon = jargon or {}
    lines_html = []
    for speaker, _, text in spans:
        s = _html.escape(speaker)
        t = _html.escape(text)
        if jargon:
            t = _apply_jargon_tooltips(t, jargon)
        lines_html.append(f"<p><strong>{s}:</strong> {t}</p>")
    transcript_body = "\n".join(lines_html)

    escaped_initial = _html.escape(initial_search, quote=True)
    init_js = (
        "(function(){"
        "var input=document.getElementById('search-input');"
        f"if(input.value){{onSearch();}}"
        "})();"
    )

    component_html = (
        f"<!DOCTYPE html>\n<html><head>\n<style>\n{_BROWSER_CSS}\n</style>\n</head><body>\n"
        '<div class="search-bar">\n'
        f'  <input type="text" id="search-input" placeholder="Search transcript..." oninput="onSearch()" value="{escaped_initial}">\n'
        '  <span class="match-count" id="match-count"></span>\n'
        '  <button class="nav-btn" id="prev-btn" onclick="navigate(-1)" title="Previous match" disabled>&#9650;</button>\n'
        '  <button class="nav-btn" id="next-btn" onclick="navigate(1)" title="Next match" disabled>&#9660;</button>\n'
        "</div>\n"
        '<div class="transcript" id="transcript">\n'
        + transcript_body
        + "\n</div>\n"
        f"<script>\n{_BROWSER_JS}\n{init_js}\n</script>\n"
        "</body></html>"
    )

    _components.html(component_html, height=400, scrolling=False)
