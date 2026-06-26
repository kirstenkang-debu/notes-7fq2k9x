#!/usr/bin/env python3
"""
Build a single self-contained study.html dashboard from notes/*.md.

- Scans notes/ for Markdown files (skips files starting with "_" except the
  template, which is shown as a styling example).
- Parses simple YAML-ish frontmatter (title, date, category, source, type, tags).
- Converts the Markdown body to HTML (focused converter for our note format).
- Emits study.html: sidebar grouped BY CATEGORY + live search + clean reading pane.

Re-run any time notes change:  python3 build_dashboard.py
"""
import os
import re
import glob
import html
import json

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = os.path.join(HERE, "notes")
OUT = os.path.join(HERE, "study.html")


def parse_frontmatter(text):
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if m:
        block, body = m.group(1), m.group(2)
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip() for v in val[1:-1].split(",") if v.strip()]
            meta[key] = val
    return meta, body


def md_inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', s)
    return s


def md_to_html(body):
    out, lines, i = [], body.splitlines(), 0
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            close_list(); i += 1; continue
        if re.match(r"^---+\s*$", line):
            close_list(); out.append("<hr>"); i += 1; continue
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            close_list()
            lvl = len(h.group(1))
            out.append(f"<h{lvl}>{md_inline(h.group(2))}</h{lvl}>")
            i += 1; continue
        li = re.match(r"^[-*]\s+(.*)$", line)
        if li:
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{md_inline(li.group(1))}</li>")
            i += 1; continue
        close_list()
        out.append(f"<p>{md_inline(line)}</p>")
        i += 1
    close_list()
    return "\n".join(out)


def main():
    files = sorted(glob.glob(os.path.join(NOTES_DIR, "*.md")))
    notes = []
    for f in files:
        base = os.path.basename(f)
        if base.startswith("_") and base != "_TEMPLATE.md":
            continue
        with open(f, encoding="utf-8") as fh:
            raw = fh.read()
        meta, body = parse_frontmatter(raw)
        title = meta.get("title") or base.replace(".md", "")
        category = meta.get("category", "기타")
        if base == "_TEMPLATE.md":
            title = "📄 (예시) " + title
            category = "✦ 예시/템플릿"
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        notes.append({
            "file": base,
            "title": title,
            "date": meta.get("date", ""),
            "category": category,
            "source": meta.get("source", ""),
            "type": meta.get("type", ""),
            "tags": tags,
            "html": md_to_html(body),
            "search": (title + " " + category + " " + " ".join(tags) + " " + body).lower(),
        })

    notes.sort(key=lambda n: (n["category"], n["date"]), reverse=False)
    cats = sorted({n["category"] for n in notes})
    data_json = json.dumps(notes, ensure_ascii=False)

    page = (TEMPLATE
            .replace("__DATA__", data_json)
            .replace("__COUNT__", str(len(notes)))
            .replace("__CATCOUNT__", str(len(cats))))
    for path in (OUT, os.path.join(HERE, "index.html")):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(page)
    print(f"Built study.html + index.html: {len(notes)} note(s) across {len(cats)} category(ies).")


TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI · 사업 스터디 노트</title>
<style>
  :root{
    --bg:#0f1115; --panel:#171a21; --panel2:#1e222b; --text:#e6e8ee;
    --muted:#9aa3b2; --accent:#7aa2ff; --border:#2a2f3a; --code:#ffd479;
  }
  @media (prefers-color-scheme: light){
    :root{ --bg:#f6f7f9; --panel:#ffffff; --panel2:#f0f2f6; --text:#1c2128;
           --muted:#5b6472; --accent:#2f6bff; --border:#e1e4ea; --code:#9a5b00; }
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{display:flex;font:16px/1.65 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",
       "Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--text)}
  aside{width:330px;min-width:330px;height:100vh;overflow-y:auto;
        background:var(--panel);border-right:1px solid var(--border);padding:18px}
  aside h1{font-size:14px;letter-spacing:.03em;color:var(--muted);margin:0 0 14px}
  .search{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border);
          background:var(--panel2);color:var(--text);font-size:14px;margin-bottom:14px}
  .search:focus{outline:2px solid var(--accent);border-color:transparent}
  .cat-header{font-size:12px;font-weight:700;letter-spacing:.02em;color:var(--accent);
              text-transform:none;margin:16px 4px 6px;display:flex;
              justify-content:space-between;align-items:center}
  .cat-header .n{color:var(--muted);font-weight:500}
  .note-item{padding:10px 12px;border-radius:10px;cursor:pointer;margin-bottom:5px;
             border:1px solid transparent}
  .note-item:hover{background:var(--panel2)}
  .note-item.active{background:var(--panel2);border-color:var(--accent)}
  .note-item .t{font-weight:600;font-size:14px}
  .note-item .m{font-size:12px;color:var(--muted);margin-top:3px}
  .tag{display:inline-block;font-size:11px;color:var(--accent);
       background:color-mix(in srgb,var(--accent) 14%,transparent);
       padding:1px 7px;border-radius:999px;margin:3px 4px 0 0}
  .empty{color:var(--muted);font-size:13px;padding:8px}
  main{flex:1;height:100vh;overflow-y:auto;padding:48px 56px}
  .wrap{max-width:760px;margin:0 auto}
  article h1{font-size:29px;line-height:1.25;margin:.2em 0 .1em}
  article h2{font-size:20px;margin:1.4em 0 .4em;padding-bottom:.2em;
             border-bottom:1px solid var(--border)}
  article h3{font-size:17px;margin:1.1em 0 .3em}
  article p{margin:.6em 0}
  article ul{margin:.4em 0 .8em;padding-left:1.3em}
  article li{margin:.25em 0}
  article code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;
       color:var(--code);background:var(--panel2);padding:.12em .4em;border-radius:6px}
  article a{color:var(--accent)}
  article hr{border:none;border-top:1px solid var(--border);margin:1.6em 0}
  .meta-bar{font-size:13px;color:var(--muted);margin-bottom:8px}
  .meta-bar .cat{color:var(--accent);font-weight:600}
  .hint{color:var(--muted);font-size:14px;text-align:center;margin-top:18vh}
  .hint code{background:var(--panel2);padding:.1em .4em;border-radius:6px}
  mark{background:var(--accent);color:#000;border-radius:3px}
</style>
</head>
<body>
<aside>
  <h1>📚 AI · 사업 스터디 · 노트 __COUNT__개 · 분야 __CATCOUNT__개</h1>
  <input class="search" id="q" placeholder="🔍  전체 노트 검색…" autocomplete="off">
  <div id="list"></div>
</aside>
<main><div class="wrap" id="content">
  <div class="hint">왼쪽에서 노트를 고르거나 검색해보세요.<br><br>
  노트 추가 후 <code>python3 build_dashboard.py</code> 로 갱신.</div>
</div></main>

<script>
const NOTES = __DATA__;
const list = document.getElementById('list');
const content = document.getElementById('content');
const q = document.getElementById('q');
let active = null;

function tagsHtml(tags){ return tags.map(t=>`<span class="tag">${t}</span>`).join(''); }

function render(filter=''){
  const f = filter.trim().toLowerCase();
  const matches = NOTES.filter(n => !f || n.search.includes(f));
  list.innerHTML = '';
  if(!matches.length){ list.innerHTML = '<div class="empty">검색 결과 없음.</div>'; return; }
  const groups = {};
  matches.forEach(n=>{(groups[n.category]=groups[n.category]||[]).push(n);});
  Object.keys(groups).sort().forEach(cat=>{
    const h = document.createElement('div');
    h.className = 'cat-header';
    h.innerHTML = `<span>${cat}</span><span class="n">${groups[cat].length}</span>`;
    list.appendChild(h);
    groups[cat].forEach(n=>{
      const div = document.createElement('div');
      div.className = 'note-item' + (active===n.file?' active':'');
      div.innerHTML = `<div class="t">${n.title}</div>
        <div class="m">${[n.date,n.type].filter(Boolean).join(' · ')}</div>
        <div>${tagsHtml(n.tags)}</div>`;
      div.onclick = ()=>openNote(n, f);
      list.appendChild(div);
    });
  });
}

function openNote(n, f){
  active = n.file;
  let body = n.html;
  if(f){
    const re = new RegExp('('+f.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','gi');
    body = body.replace(/>([^<]+)</g, (m,txt)=> '>'+txt.replace(re,'<mark>$1</mark>')+'<');
  }
  content.innerHTML = `<article>
    <div class="meta-bar"><span class="cat">${n.category}</span>
      ${[n.date,n.type].filter(Boolean).map(x=>' · '+x).join('')}
      ${n.source?(' · '+ (/^https?:/.test(n.source)?`<a href="${n.source}" target="_blank">source</a>`:n.source)):''}
      <div>${tagsHtml(n.tags)}</div></div>
    ${body}</article>`;
  content.parentElement.scrollTop = 0;
  render(q.value);
}

q.addEventListener('input', ()=>render(q.value));
render();
if(NOTES.length) openNote(NOTES[0], '');
</script>
</body>
</html>"""

if __name__ == "__main__":
    main()
