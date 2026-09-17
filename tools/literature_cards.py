#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重点文献卡片网页生成器（单文件、手机优先、离线可开）
====================================================================
把"多词多源检索得到的候选池 CSV"和/或"文献整理表 CSV"读进来，去重后
自动挑出**重点文献**，生成一个和 templates/网页范例/01-文献笔记网页 同一套
视觉语言的单文件网页：顶部搜索 + 分类筛选 + ⭐重点 + 卡片网格 + 点击看详情。

用途：文献自动检索凑够 ≥90 篇候选池后，学生不必一篇篇硬啃——先看这一页
"优先读哪十几篇、为什么值得读"，再去精读 PDF。

重点怎么选（可解释、不黑箱）：
  1) 整理表里手动标了"是否精读=是/√/1/★"的，无条件进重点（学生和 AI 的判断优先）；
  2) 其余按 被引数(对数) + 近年 + 综述/Meta + 与 --focus 关键词相关度 + 有摘要
     综合打分，从高到低补足到目标数量（默认约 15%，夹在 8–30 篇）。

硬规矩（与 workflows/webpage-guide.md 一致，脚本层面强制）：
  - 单个 .html，CSS/JS 全内联，**不引用任何外网 CDN/字体/脚本**，双击即开、不泄露检索内容；
  - 学生数据用 DOM textContent 渲染（自动转义，防摘要里的特殊字符破坏页面）；
  - 页脚标注来源文件、生成时间与"AI 整理、需核对原文、不作引用依据"。

典型用法：
  python tools/literature_cards.py "我的工作区/01-文献PDF/英文文献_候选池.csv" \
      --output "我的工作区/04-网页/重点文献卡片.html" --focus "AI依赖,NSSI,孤独"
  # 也可同时喂多个文件（检索 CSV + 中文整理表），自动去重合并：
  python tools/literature_cards.py 英文文献_候选池.csv 文献_整理表.csv --output 卡片.html
====================================================================
"""

import argparse
import csv
import html
import json
import math
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# 复用 paper_search 的去重键与规范化（单一事实来源）
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_search as ps  # noqa: E402

# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CANDIDATE_HEADERS = {
    "title": ["标题", "题名", "title", "篇名"],
    "authors": ["作者", "authors", "author"],
    "year": ["年份", "年", "发表年份", "year", "出版年"],
    "venue": ["期刊/会议", "期刊", "来源", "venue", "journal", "出版物"],
    "doi": ["DOI", "doi"],
    "url": ["链接", "网址", "url", "全文链接", "PDF"],
    "cited": ["被引数", "被引", "引用次数", "cited", "citations"],
    "abstract": ["摘要", "abstract", "概要"],
    "category": ["分类", "类别", "主题分类", "category"],
    "tags": ["关键词", "关键字", "tags", "keywords", "命中检索词", "主题词"],
    "star": ["是否精读", "精读", "重点", "star", "推荐", "必读"],
    "finding": ["核心发现", "核心观点", "主要结论", "finding", "一句话总结", "备注"],
    "relation": ["与我论文的关系", "相关性", "relation", "用途"],
}

STAR_POSITIVE = {"是", "yes", "y", "true", "1", "★", "☆", "√", "对", "重点", "精读", "必读", "*"}
REVIEW_PATTERN = re.compile(r"(综述|系统评价|元分析|meta[-\s]?analysis|systematic review|a review|review of)",
                            re.IGNORECASE)


def read_csv_rows(path):
    """以 utf-8-sig/gbk 顺序尝试读取 CSV，返回 dict 行列表；打不开返回 None。"""
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(text.splitlines())
    return [dict(r) for r in reader]


def pick(row, key):
    """按候选表头从一行里容错取值（去空白、忽略大小写/前后空格）。"""
    if not row:
        return ""
    norm = { (k or "").strip().lower(): v for k, v in row.items() }
    for cand in CANDIDATE_HEADERS[key]:
        v = norm.get(cand.strip().lower())
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def split_tags(s):
    """把关键词/命中检索词拆成列表（兼容 ;；,，、/ 与空白分隔），保序去重。"""
    if not s:
        return []
    parts = re.split(r"[;；,，、/|]+|\s{2,}", str(s))
    out, seen = [], set()
    for p in parts:
        p = p.strip()
        if p and p.lower() not in seen and len(p) <= 30:
            seen.add(p.lower())
            out.append(p)
    return out


def is_star(row, value):
    v = str(value or "").strip().lower()
    return bool(v) and (v in STAR_POSITIVE or v.startswith("是") or "精读" in v or "重点" in v)


def to_paper(row, source_name):
    title = pick(row, "title")
    if not title:
        return None
    cited = 0
    m = re.search(r"\d+", pick(row, "cited"))
    if m:
        cited = int(m.group())
    year = ""
    ym = re.search(r"(19|20)\d{2}", pick(row, "year"))
    if ym:
        year = ym.group(0)
    abstract = pick(row, "abstract")
    finding = pick(row, "finding")
    oneliner = finding or abstract
    oneliner = re.sub(r"\s+", " ", oneliner).strip()
    return {
        "title": title,
        "authors": pick(row, "authors"),
        "year": year,
        "venue": pick(row, "venue"),
        "doi": ps.normalize_doi(pick(row, "doi")),
        "url": pick(row, "url"),
        "cited": cited,
        "abstract": re.sub(r"\s+", " ", abstract).strip(),
        "source_api": [source_name],
        "matched_queries": [],
        "category": pick(row, "category"),
        "tags": split_tags(pick(row, "tags")),
        "star_flag": is_star(row, pick(row, "star")),
        "finding": finding,
        "oneliner": oneliner,
    }


def merge_card(existing, incoming):
    """卡片场景的合并：并集标签/来源/命中词，重点标记取或，缺漏互补，被引取大。"""
    m = ps.merge_records(existing, incoming)
    for k in ("tags", "matched_queries", "source_api"):
        merged = list(m.get(k) or [])
        for x in (incoming.get(k) or []):
            if x and x not in merged:
                merged.append(x)
        m[k] = merged
    m["star_flag"] = bool(existing.get("star_flag")) or bool(incoming.get("star_flag"))
    for k in ("category", "finding", "oneliner"):
        if not m.get(k) and incoming.get(k):
            m[k] = incoming[k]
    return m


def load_papers(paths):
    """读入多个 CSV，转 paper 并按 DOI/标题去重合并。返回 (papers, problems)。"""
    bucket, problems = {}, []
    for path in paths:
        p = Path(path)
        if not p.exists():
            problems.append(f"找不到文件：{path}")
            continue
        try:
            rows = read_csv_rows(p)
        except Exception as e:  # 读失败不静默
            problems.append(f"读取失败：{path}（{e}）")
            continue
        added = 0
        for row in rows:
            paper = to_paper(row, p.name)
            if not paper:
                continue
            key = ps.dedup_key(paper)
            if key[1] and key in bucket:
                bucket[key] = merge_card(bucket[key], paper)
            elif not key[1]:
                bucket[("uid", id(paper))] = paper
            else:
                bucket[key] = paper
            added += 1
        print(f"  · {p.name}：读到 {len(rows)} 行，识别 {added} 篇")
    papers = list(bucket.values())
    papers.sort(key=lambda r: (-(int(r.get("cited") or 0)), -(int(r.get("year") or 0))))
    return papers, problems


def score_paper(p, focus_terms):
    """重点打分（确定性、可解释）。分数越高越优先。"""
    score = 0.0
    score += math.log10(int(p.get("cited") or 0) + 1)            # 被引：对数，避免一家独大
    try:
        y = int(p.get("year") or 0)
        if y:
            score += max(0.0, min(1.0, (y - 2000) / 25.0))        # 近年加分，封顶
    except ValueError:
        pass
    hay = f"{p.get('title','')} {p.get('venue','')}".lower()
    if REVIEW_PATTERN.search(hay):
        score += 1.2                                              # 综述/Meta 优先（适合打底）
    if p.get("abstract"):
        score += 0.2
    text = (p.get("title", "") + " " + p.get("abstract", "") + " " + " ".join(p.get("tags", []))).lower()
    for t in focus_terms:
        if t and t.lower() in text:
            score += 0.8
    return round(score, 4)


def pick_stars(papers, focus_terms, top=None):
    """返回重点文献的下标集合（id 用列表下标）。"""
    forced = [i for i, p in enumerate(papers) if p.get("star_flag")]
    if top is None:
        top = max(8, min(30, round(len(papers) * 0.15)))
    ranked = sorted(range(len(papers)), key=lambda i: score_paper(papers[i], focus_terms), reverse=True)
    stars = set(forced)
    for i in ranked:
        if len(stars) >= top:
            break
        stars.add(i)
    return stars


def derive_categories(papers):
    """从 分类列（缺失则第一个标签）派生筛选分类，返回 [(cat,count)]，按数量降序。"""
    counts = {}
    for p in papers:
        cat = p.get("category") or (p.get("tags")[0] if p.get("tags") else "")
        cat = (cat or "未分类").strip()
        counts[cat] = counts.get(cat, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def build_payload(papers, star_idx, focus_terms):
    """构造嵌入网页的 JSON（只放可公开的题录信息，不含任何个人隐私字段）。"""
    cats = dict(derive_categories(papers))
    data = []
    for i, p in enumerate(papers):
        data.append({
            "id": i,
            "title": p.get("title", ""),
            "authors": p.get("authors", ""),
            "year": p.get("year", ""),
            "venue": p.get("venue", ""),
            "cited": int(p.get("cited") or 0),
            "doi": p.get("doi", ""),
            "url": p.get("url", ""),
            "tags": p.get("tags", [])[:6],
            "cat": p.get("category") or (p.get("tags")[0] if p.get("tags") else "未分类"),
            "star": i in star_idx,
            "oneliner": (p.get("oneliner") or "")[:220],
            "abstract": p.get("abstract", ""),
            "score": score_paper(p, focus_terms),
        })
    return data, list(cats.keys())


def render_html(data, cats, page_title, sources):
    """渲染单文件 HTML。数据经 json 嵌入、由 JS 用 textContent 渲染（天然转义）。"""
    payload_json = json.dumps({"papers": data, "cats": cats}, ensure_ascii=False)
    # json 数据放进 <script type="application/json">，不执行、不参与 HTML 解析为标签
    payload_tag = "<script type=\"application/json\" id=\"data\">" + \
        payload_json.replace("</", "<\\/") + "</script>"
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    source_list = "、".join(sources)
    safe_title = html.escape(page_title)
    safe_sources = html.escape(source_list)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
<style>
:root {{
  --bg:#f5f6f8; --card:#ffffff; --ink:#1f2329; --sub:#6b7280; --line:#e5e7eb;
  --brand:#2563eb; --brand-soft:#eff4ff; --gold:#d9a406; --gold-soft:#fff8e1;
  --radius:14px; --tap:42px;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  line-height:1.6; }}
.header {{ position:sticky; top:0; z-index:20; background:rgba(255,255,255,.96);
  backdrop-filter:blur(6px); border-bottom:1px solid var(--line); padding:14px 16px 10px; }}
.header h1 {{ font-size:18px; margin:0 0 2px; }}
.header .sub {{ font-size:12px; color:var(--sub); margin:0 0 10px; }}
.search-bar {{ display:flex; align-items:center; gap:8px; background:#f0f2f5;
  border-radius:10px; padding:0 12px; height:var(--tap); }}
.search-bar input {{ flex:1; border:0; background:transparent; font-size:15px; outline:none; color:var(--ink); }}
.filters {{ display:flex; gap:8px; overflow-x:auto; padding:10px 16px 4px;
  -webkit-overflow-scrolling:touch; scrollbar-width:none; }}
.filters::-webkit-scrollbar {{ display:none; }}
.filter-btn {{ flex:0 0 auto; min-height:36px; padding:0 14px; border:1px solid var(--line);
  background:#fff; border-radius:999px; font-size:13px; color:var(--sub); cursor:pointer; }}
.filter-btn.active {{ background:var(--brand); border-color:var(--brand); color:#fff; }}
.filter-btn.star.active {{ background:var(--gold); border-color:var(--gold); color:#fff; }}
.wrap {{ padding:12px 16px 96px; max-width:1080px; margin:0 auto; }}
.grid {{ display:grid; grid-template-columns:1fr; gap:12px; }}
@media (min-width:640px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }} }}
@media (min-width:980px) {{ .grid {{ grid-template-columns:repeat(3,1fr); }} }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  padding:14px; cursor:pointer; display:flex; flex-direction:column; gap:8px;
  min-height:150px; transition:box-shadow .15s, transform .15s; }}
.card:hover {{ box-shadow:0 6px 20px rgba(31,35,41,.10); transform:translateY(-1px); }}
.card.star {{ border-color:var(--gold); background:linear-gradient(180deg,var(--gold-soft),#fff 42%); }}
.card-cat {{ align-self:flex-start; font-size:11px; color:var(--brand);
  background:var(--brand-soft); border-radius:6px; padding:2px 8px; }}
.card-title {{ font-size:15px; font-weight:600; line-height:1.45; margin:0;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}
.card-meta {{ font-size:12px; color:var(--sub); display:flex; flex-wrap:wrap; gap:4px 10px; }}
.badge {{ font-weight:600; color:var(--gold); }}
.card-line {{ font-size:13px; color:#444; margin:0;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }}
.card-tags {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:auto; }}
.tag {{ font-size:11px; background:#f0f2f5; color:#555; border-radius:6px; padding:2px 8px; }}
.empty {{ text-align:center; color:var(--sub); padding:60px 20px; font-size:14px; }}
.footer {{ max-width:1080px; margin:0 auto; padding:0 16px 40px; font-size:11.5px; color:var(--sub); }}
/* 详情弹层 */
.modal-mask {{ position:fixed; inset:0; background:rgba(0,0,0,.45); display:none;
  z-index:40; padding:0; }}
.modal-mask.open {{ display:flex; align-items:flex-end; justify-content:center; }}
@media (min-width:640px) {{ .modal-mask.open {{ align-items:center; }} }}
.modal {{ background:#fff; width:100%; max-width:680px; max-height:88vh; overflow-y:auto;
  border-radius:18px 18px 0 0; padding:20px 18px 26px; }}
@media (min-width:640px) {{ .modal {{ border-radius:18px; }} }}
.modal h2 {{ font-size:17px; margin:0 0 8px; padding-right:30px; }}
.modal .m-meta {{ font-size:12.5px; color:var(--sub); margin-bottom:10px; }}
.modal .m-abstract {{ font-size:14px; color:#333; white-space:pre-wrap; }}
.modal .m-links {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }}
.modal .m-links a {{ min-height:var(--tap); display:inline-flex; align-items:center; padding:0 16px;
  background:var(--brand); color:#fff; border-radius:10px; text-decoration:none; font-size:14px; }}
.modal .m-tags {{ display:flex; flex-wrap:wrap; gap:6px; margin:10px 0; }}
.modal-close {{ position:absolute; top:14px; right:14px; width:var(--tap); height:var(--tap);
  border:0; background:#f0f2f5; border-radius:50%; font-size:18px; cursor:pointer; }}
</style>
</head>
<body>
<div class="header">
  <h1 id="pageTitle"></h1>
  <p class="sub" id="pageSub"></p>
  <div class="search-bar"><span>&#128269;</span><input id="searchInput" type="search"
    placeholder="搜索标题、作者、关键词、摘要……" autocomplete="off"></div>
</div>
<div class="filters" id="filters"></div>
<div class="wrap"><div class="grid" id="grid"></div><div class="empty" id="empty" style="display:none">没有匹配的文献，换个关键词或分类试试。</div></div>
<div class="footer" id="footer"></div>
<div class="modal-mask" id="modalMask"><div class="modal" id="modal"></div></div>
{payload_tag}
<script>
(function () {{
  var raw = JSON.parse(document.getElementById('data').textContent);
  var PAPERS = raw.papers, CATS = raw.cats;
  var state = {{ cat:'all', star:false, kw:'' }};
  document.getElementById('pageTitle').textContent = {json.dumps(page_title, ensure_ascii=False)};
  document.getElementById('pageSub').textContent =
    '候选池 ' + PAPERS.length + ' 篇 · 重点 ' + PAPERS.filter(function(p){{return p.star;}}).length + ' 篇（先读带 ⭐ 的）';
  document.getElementById('footer').textContent =
    '来源文件：' + {json.dumps(source_list, ensure_ascii=False)} + '｜生成时间：' + {json.dumps(gen_time, ensure_ascii=False)} +
    '｜本页由文献题录自动整理，摘要与出处请对照原文核实，不构成论文引用依据；请勿录入个人隐私信息。';

  var filters = document.getElementById('filters');
  function addFilter(label, cat, star) {{
    var b = document.createElement('button');
    b.className = 'filter-btn' + (star ? ' star' : '') +
      ((cat === state.cat && !star) || (star && state.star) ? ' active' : '');
    b.textContent = label;
    b.addEventListener('click', function () {{
      if (star) {{ state.star = !state.star; }} else {{ state.cat = cat; state.star = false; }}
      render();
    }});
    filters.appendChild(b);
  }}
  function buildFilters() {{
    filters.innerHTML = '';
    addFilter('全部 (' + PAPERS.length + ')', 'all', false);
    CATS.forEach(function (c) {{
      var n = PAPERS.filter(function(p){{return p.cat === c;}}).length;
      addFilter(c + ' (' + n + ')', c, false);
    }});
    var ns = PAPERS.filter(function(p){{return p.star;}}).length;
    addFilter('⭐ 重点 (' + ns + ')', 'all', true);
  }}
  function el(tag, cls, text) {{ var e=document.createElement(tag); if(cls)e.className=cls; if(text!=null)e.textContent=text; return e; }}
  function match(p) {{
    if (state.star && !p.star) return false;
    if (state.cat !== 'all' && p.cat !== state.cat) return false;
    if (state.kw) {{
      var hay = (p.title+' '+p.authors+' '+(p.tags||[]).join(' ')+' '+p.oneliner).toLowerCase();
      if (hay.indexOf(state.kw.toLowerCase()) === -1) return false;
    }}
    return true;
  }}
  function render() {{
    buildFilters();
    var grid = document.getElementById('grid'); grid.innerHTML='';
    var list = PAPERS.filter(match);
    document.getElementById('empty').style.display = list.length ? 'none' : 'block';
    list.forEach(function (p) {{
      var card = el('article','card'+(p.star?' star':''));
      card.appendChild(el('div','card-cat', p.cat));
      var t = el('h3','card-title', (p.star?'⭐ ':'') + p.title); card.appendChild(t);
      var meta = el('div','card-meta');
      if (p.year) meta.appendChild(el('span','',p.year));
      if (p.venue) meta.appendChild(el('span','',p.venue));
      if (p.cited>0) meta.appendChild(el('span','badge','被引 '+p.cited));
      card.appendChild(meta);
      if (p.authors) card.appendChild(el('div','card-meta', p.authors.length>60?p.authors.slice(0,60)+'…':p.authors));
      if (p.oneliner) card.appendChild(el('p','card-line', p.oneliner.length>120?p.oneliner.slice(0,120)+'…':p.oneliner));
      if (p.tags && p.tags.length) {{
        var tg = el('div','card-tags');
        p.tags.slice(0,3).forEach(function(x){{ tg.appendChild(el('span','tag',x)); }});
        card.appendChild(tg);
      }}
      card.addEventListener('click', function(){{ openModal(p); }});
      grid.appendChild(card);
    }});
  }}
  function openModal(p) {{
    var m = document.getElementById('modal'); m.innerHTML='';
    m.style.position='relative';
    var close = el('button','modal-close','×');
    close.addEventListener('click', closeModal); m.appendChild(close);
    m.appendChild(el('h2','',(p.star?'⭐ ':'')+p.title));
    var meta = el('div','m-meta');
    meta.textContent = [p.authors, p.year, p.venue, (p.cited>0?('被引 '+p.cited):'')].filter(Boolean).join(' · ');
    m.appendChild(meta);
    if (p.tags && p.tags.length) {{ var tg=el('div','m-tags'); p.tags.forEach(function(x){{tg.appendChild(el('span','tag',x));}}); m.appendChild(tg); }}
    if (p.abstract) m.appendChild(el('div','m-abstract', p.abstract));
    else if (p.oneliner) m.appendChild(el('div','m-abstract', p.oneliner));
    else m.appendChild(el('div','m-abstract','（该题录暂无摘要，请到原文数据库查看。）'));
    var links = el('div','m-links');
    if (p.doi) {{ var a=el('a','', 'DOI 原文'); a.href='https://doi.org/'+p.doi; a.target='_blank'; a.rel='noopener'; links.appendChild(a); }}
    if (p.url && p.url.indexOf('http')===0) {{ var b=el('a','', '查看链接'); b.href=p.url; b.target='_blank'; b.rel='noopener'; links.appendChild(b); }}
    m.appendChild(links);
    document.getElementById('modalMask').classList.add('open');
  }}
  function closeModal() {{ document.getElementById('modalMask').classList.remove('open'); }}
  document.getElementById('modalMask').addEventListener('click', function(e){{ if(e.target===this) closeModal(); }});
  document.getElementById('searchInput').addEventListener('input', function(e){{ state.kw=e.target.value; render(); }});
  render();
}})();
</script>
</body>
</html>
"""


def parse_focus(s):
    if not s:
        return []
    return [x.strip() for x in re.split(r"[;；,，、]+", s) if x.strip()]


def main():
    ap = argparse.ArgumentParser(description="把文献 CSV 生成重点文献卡片网页（单文件、手机优先、无外网依赖）")
    ap.add_argument("inputs", nargs="+", help="一个或多个文献 CSV（检索候选池 / 文献整理表均可，自动去重）")
    ap.add_argument("--output", required=True, help="输出 .html 路径")
    ap.add_argument("--top", type=int, default=None, help="重点文献目标篇数（默认约总数一成半，夹在8–30篇）")
    ap.add_argument("--title", default="重点文献推荐卡片", help="网页标题")
    ap.add_argument("--focus", default="", help="你的核心变量/主题词（逗号分隔），命中的文献重点排序加权")
    args = ap.parse_args()

    out = Path(args.output)
    if out.suffix.lower() not in (".html", ".htm"):
        print("错误：--output 必须是 .html 文件。")
        return 2

    print("读取并合并文献：")
    papers, problems = load_papers(args.inputs)
    for prob in problems:
        print("  ⚠ " + prob)
    if problems and not papers:
        print("没有可用文献，已停止（未生成网页）。请检查文件路径与编码。")
        return 1

    focus = parse_focus(args.focus)
    star_idx = pick_stars(papers, focus, args.top)
    data, cats = build_payload(papers, star_idx, focus)
    sources = sorted({Path(x).name for x in args.inputs if Path(x).exists()})
    page = render_html(data, cats, args.title, sources)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")

    print(f"\n已生成：{out}")
    print(f"候选池 {len(papers)} 篇，其中重点 {len(star_idx)} 篇；分类 {len(cats)} 个。")
    print("手机/电脑双击均可打开；可放进 我的工作区/04-网页/，用菜单第 10 项或 webpage_preview.py 预览。")
    if len(papers) < 90:
        print(f"提示：候选池目前 {len(papers)} 篇，建议先用 paper_search.py --source all --min 90 多词凑够 90 篇，重点会更全。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
