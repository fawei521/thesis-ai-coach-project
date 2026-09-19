#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
毕业论文英文文献检索工具（OpenAlex / Semantic Scholar，免费、无需 API key）
====================================================================
设计原则（v1.58 起）：
  1. **多词检索，不单词下判断**：一个概念往往有多种英文写法，只搜一个词会漏掉
     一大片，甚至把"0 命中"误判成"没人做过"（假空白）。请为每个核心概念准备
     至少 3 个同义/近义/上下位/缩写词，用 --query 重复传入或用 --queries 一次传入。
  2. **多源交叉**：--source all 同时查 OpenAlex 与 Semantic Scholar，按
     DOI/规范标题去重合并，互相补全被引数与摘要。
  3. **候选池要大**：--min 90 会逐词逐源翻页，直到去重后达到 90 篇或库内穷尽；
     这是"候选题录池"，不是要精读/引用 90 篇——再分级筛重点 10–20 篇精读。
  4. 纯标准库 + 纯函数化：合并/去重/配额逻辑不依赖网络，便于离线确定性测试。

典型用法：
  # 单词、单源（老用法，兼容）
  python tools/paper_search.py --query "AI dependence adolescent NSSI" --source openalex --limit 20

  # 多近义词 + 双源 + 凑够 90 篇候选池（推荐）
  python tools/paper_search.py \\
      --query "AI chatbot dependence adolescent" \\
      --query "artificial intelligence emotional attachment teenagers" \\
      --query "human-AI relationship compulsive use youth" \\
      --source all --min 90 \\
      --output "我的工作区/01-文献PDF/英文文献_候选池.csv"

  # 分号/换行分隔的便捷写法（菜单用）
  python tools/paper_search.py --queries "AI dependence;AI attachment;chatbot reliance" --source all --min 90

输出 CSV（UTF-8-BOM，Excel 直接打开不乱码）列：
  标题,作者,年份,期刊/会议,DOI,链接,被引数,摘要,来源API,命中检索词,检索日期
====================================================================
"""

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 控制台默认 GBK）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FIELDNAMES = ["标题", "作者", "年份", "期刊/会议", "DOI", "链接", "被引数",
              "摘要", "来源API", "命中检索词", "检索日期"]
TODAY = date.today().isoformat()
USER_AGENT = "ThesisLiteratureSearch/1.0 (academic literature search for undergraduate thesis; mailto:student@example.com)"


# ============================================================
# 纯函数区（不联网；被 literature_cards.py 复用，也被离线单测覆盖）
# ============================================================
def normalize_title(title):
    """把标题规范化成去重键：NFKC、去注音符号、小写、去标点与多余空白。

    仅用于去重比较，不改变原始标题。
    """
    if not title:
        return ""
    s = unicodedata.normalize("NFKC", str(title))
    # 去掉拉丁附加符号（é→e、ï→i），提升跨库标题匹配率
    s = "".join(c for c in unicodedata.normalize("NFKD", s)
                if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_doi(doi):
    """规范 DOI：去 URL 前缀与空白、转小写。无法识别返回空串。"""
    if not doi:
        return ""
    s = str(doi).strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    s = re.sub(r"^doi:\s*", "", s)
    return s.strip()


def split_queries(values):
    """把多个 --query / 一个 --queries 的输入拆成去重后的检索词列表。

    --queries 接受分号（;；）、换行分隔；逗号在英文学术短语里可能是检索式的
    一部分，故不作为分隔符。每个词去重并保序。
    """
    out = []
    seen = set()

    def add(q):
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)

    for v in values or []:
        if v is None:
            continue
        for part in re.split(r"[;\n；]+", str(v)):
            add(part)
    return out


def dedup_key(rec):
    """去重主键：有 DOI 用 DOI，否则用规范标题。"""
    doi = normalize_doi(rec.get("doi"))
    if doi:
        return ("doi", doi)
    return ("title", normalize_title(rec.get("title", "")))


def merge_records(existing, incoming):
    """把 incoming 合并进 existing（同一篇）：并集命中词/来源，被引取大，缺漏互补。

    返回合并后的记录（不就地改 existing 的关键字段以外结构）。
    """
    merged = dict(existing)
    # 命中检索词、来源 API 取并集（保序去重）
    for list_key in ("matched_queries", "source_api"):
        old = merged.get(list_key) or []
        new = incoming.get(list_key) or []
        if isinstance(old, str):
            old = [old]
        if isinstance(new, str):
            new = [new]
        union = []
        for x in old + new:
            if x and x not in union:
                union.append(x)
        merged[list_key] = union
    # 被引数取较大值（不同库口径不同）
    try:
        merged["cited"] = max(int(merged.get("cited") or 0), int(incoming.get("cited") or 0))
    except (TypeError, ValueError):
        pass
    # 缺漏字段互补（incoming 不为空就补 existing 的空值）
    for k in ("title", "authors", "year", "venue", "doi", "url", "abstract"):
        if not merged.get(k) and incoming.get(k):
            merged[k] = incoming[k]
    return merged


def add_record(bucket, rec):
    """按 dedup_key 把 rec 合入 bucket（dict）。返回是否为新增。"""
    key = dedup_key(rec)
    # DOI 缺失时标题为空不参与合并，各自保留
    if key[1] and key in bucket:
        bucket[key] = merge_records(bucket[key], rec)
        return False
    if not key[1]:
        # 无任何可用键，用 id() 占位确保不丢记录
        bucket[("uid", id(rec))] = rec
        return True
    bucket[key] = rec
    return True


def collect(queries, sources, target, per_page, year=None, fetcher=None,
            sleeper=None, max_pages_per_pair=6, verbose=True):
    """逐"来源×检索词"翻页拉取并去重合并，直到去重后篇数 ≥ target 或全部穷尽。

    纯编排逻辑：网络动作由注入的 fetcher(source, query, offset, per_page, year)
    完成，默认 None 时不联网（离线测试注入假 fetcher）。
    返回 (records_list, stats)；stats 记录每个 (source, query) 的命中数，便于留痕。
    """
    fetcher = fetcher or (lambda *a, **k: [])
    sleeper = sleeper or (lambda s: None)
    bucket = {}
    stats = []
    for source in sources:
        for query in queries:
            offset = 0
            got_this_pair = 0
            for page in range(max_pages_per_pair):
                try:
                    batch = fetcher(source, query, offset, per_page, year) or []
                except Exception as e:  # 单次请求失败不致命：记录后跳到下一词/源
                    stats.append({"source": source, "query": query, "page": page,
                                  "fetched": 0, "error": str(e)})
                    if verbose:
                        print(f"  [跳过] {source} / {query!r} 第{page + 1}页请求失败：{e}")
                    break
                if not batch:
                    break
                for r in batch:
                    r.setdefault("matched_queries", [query])
                    if query not in r["matched_queries"]:
                        r["matched_queries"].append(query)
                    r.setdefault("source_api", [source])
                    add_record(bucket, r)
                got_this_pair += len(batch)
                offset += len(batch)
                stats.append({"source": source, "query": query, "page": page,
                              "fetched": len(batch)})
                if verbose:
                    print(f"  {source}｜{query!r} 第{page + 1}页 {len(batch)} 篇，"
                          f"去重后累计 {len(bucket)} 篇")
                if len(batch) < per_page:
                    break  # 该词在该库已穷尽
                if target and len(bucket) >= target:
                    break
                sleeper(0.35)
            if target and len(bucket) >= target:
                break
            sleeper(0.2)
        if target and len(bucket) >= target:
            break
    records = sorted(bucket.values(),
                     key=lambda r: (-(int(r.get("cited") or 0)), -(int(r.get("year") or 0))))
    return records, stats


# ============================================================
# 网络抓取区（可被 collect 的默认流程调用；解析为统一 record 结构）
# ============================================================
def _http_get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def search_openalex_page(query, offset, per_page, year=None, timeout=20):
    """抓 OpenAlex 一页，返回统一 record 列表。按被引数降序。"""
    params = {
        "search": query,
        "per-page": min(int(per_page), 200),
        "page": (offset // max(1, int(per_page))) + 1,
        "sort": "cited_by_count:desc",
        "mailto": "student@example.com",
    }
    if year:
        params["filter"] = f"from_publication_date:{year}-01-01,to_publication_date:{year}-12-31"
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    data = _http_get_json(url, timeout=timeout)
    out = []
    for w in data.get("results", []):
        doi = normalize_doi(w.get("doi") or (w.get("ids") or {}).get("doi"))
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in w.get("authorships", []) if a.get("author"))
        # 重建摘要（OpenAlex 给的是 词->位置 的倒排索引）
        abstract = ""
        inv = w.get("abstract_inverted_index")
        if inv:
            positions = {}
            for word, idxs in inv.items():
                for i in idxs:
                    positions[i] = word
            abstract = " ".join(positions[i] for i in sorted(positions))
        out.append({
            "title": (w.get("title") or "").strip(),
            "authors": authors,
            "year": w.get("publication_year") or "",
            "venue": (w.get("primary_location") or {}).get("source", {}).get("display_name", "")
                     if w.get("primary_location") else "",
            "doi": doi,
            "url": (w.get("doi") or w.get("id") or "").replace("https://doi.org/", "https://doi.org/"),
            "cited": _as_int(w.get("cited_by_count")),
            "abstract": abstract,
            "source_api": ["OpenAlex"],
        })
    return out


def search_semantic_page(query, offset, per_page, year=None, timeout=20):
    """抓 Semantic Scholar 一页，返回统一 record 列表。"""
    fields = "title,authors,year,venue,externalIds,abstract,citationCount,openAccessPdf,url"
    params = {
        "query": query,
        "limit": min(int(per_page), 100),
        "offset": int(offset),
        "fields": fields,
    }
    if year:
        params["year"] = year
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
    data = _http_get_json(url, timeout=timeout)
    out = []
    for p in data.get("data", []):
        ext = p.get("externalIds") or {}
        doi = normalize_doi(ext.get("DOI"))
        authors = ", ".join(a.get("name", "") for a in p.get("authors", []) if a.get("name"))
        link = (p.get("openAccessPdf") or {}).get("url") or p.get("url") or ""
        if doi and not link:
            link = "https://doi.org/" + doi
        out.append({
            "title": (p.get("title") or "").strip(),
            "authors": authors,
            "year": p.get("year") or "",
            "venue": p.get("venue") or "",
            "doi": doi,
            "url": link,
            "cited": _as_int(p.get("citationCount")),
            "abstract": (p.get("abstract") or "").replace("\n", " ").strip(),
            "source_api": ["Semantic Scholar"],
        })
    return out


def live_fetcher(source, query, offset, per_page, year):
    if source == "openalex":
        return search_openalex_page(query, offset, per_page, year)
    if source == "semantic":
        return search_semantic_page(query, offset, per_page, year)
    return []


# ============================================================
# 输出
# ============================================================
def records_to_rows(records):
    """统一 record → CSV 行字典（FIELDNAMES）。"""
    rows = []
    for r in records:
        rows.append({
            "标题": r.get("title", ""),
            "作者": r.get("authors", ""),
            "年份": r.get("year", ""),
            "期刊/会议": r.get("venue", ""),
            "DOI": r.get("doi", ""),
            "链接": r.get("url", ""),
            "被引数": r.get("cited", 0),
            "摘要": (r.get("abstract") or "").replace("\r", " ").replace("\n", " "),
            "来源API": ";".join(r.get("source_api", [])),
            "命中检索词": ";".join(r.get("matched_queries", [])),
            "检索日期": TODAY,
        })
    return rows


def save_csv(rows, output):
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(
        description="英文学术文献检索（OpenAlex/Semantic Scholar，免费无 key；支持多近义词、多源、目标篇数）")
    ap.add_argument("--query", action="append", default=[],
                    help="检索词，可重复传入多个近义词（如 --query 'AI dependence' --query 'AI attachment'）")
    ap.add_argument("--queries", default="",
                    help="便捷写法：分号/换行分隔的多个检索词（如 'AI dependence;AI attachment;chatbot reliance'）")
    ap.add_argument("--source", default="openalex", choices=["openalex", "semantic", "all"],
                    help="数据源：openalex（默认）/semantic/all（两个都查并去重合并）")
    ap.add_argument("--limit", type=int, default=20,
                    help="不设 --min 时，每个检索词×每个来源单页拉取的上限（默认20）")
    ap.add_argument("--min", dest="min_target", type=int, default=0,
                    help="去重后的目标篇数（如 90）：达到即停，达不到会明确提示补词，不静默成功")
    ap.add_argument("--year", default=None, help="限定年份，如 2023（默认不限）")
    ap.add_argument("--output", default="papers.csv", help="输出 CSV 路径")
    args = ap.parse_args()

    queries = split_queries(args.query + ([args.queries] if args.queries else []))
    if not queries:
        print("错误：请用 --query 或 --queries 提供至少一个检索词。")
        print("示例：python tools/paper_search.py --query \"AI dependence adolescent NSSI\" --source all --min 90")
        return 1
    sources = ["openalex", "semantic"] if args.source == "all" else [args.source]

    if args.min_target:
        per_page = max(args.limit, 100)
        target = args.min_target
        print(f"检索目标：去重后 ≥{target} 篇候选池；{len(queries)} 个检索词 × {len(sources)} 个来源，逐页拉取……")
    else:
        per_page = max(1, args.limit)
        target = 0
        print(f"检索词 {len(queries)} 个；来源 {sources}；每词每源单页上限 {per_page} 篇……")

    try:
        records, stats = collect(queries, sources, target, per_page, year=args.year,
                                 fetcher=live_fetcher, sleeper=time.sleep, verbose=True)
    except Exception as e:
        print(f"检索失败：{e}")
        print("可能是网络不通或 API 临时限流。可：①稍后重试；②改用浏览器在 Google Scholar/PubMed 手动检索。")
        return 1

    rows = records_to_rows(records)
    save_csv(rows, args.output)

    print(f"\n已保存 {len(rows)} 篇（去重后）到：{args.output}")
    print("各来源×检索词命中明细（请同步抄进检索记录留痕）：")
    for s in stats:
        if "error" in s:
            print(f"  - {s['source']}｜{s['query']!r}｜第{s['page'] + 1}页｜失败：{s['error']}")
        else:
            print(f"  - {s['source']}｜{s['query']!r}｜第{s['page'] + 1}页｜{s['fetched']} 篇")

    if target and len(rows) < target:
        print(f"\n⚠ 去重后仅 {len(rows)} 篇，未达到目标 {target} 篇。这不是失败，但请不要据此下"
              f"'没人做过'的结论（防假空白）。建议：")
        print("  1) 为每个核心概念再补 2–3 个同义/近义词（含缩写、英式/美式拼写、更上位词）；")
        print("  2) 加 --source all 双源互补；3) 到知网/万方/PubMed/Google Scholar 用中文与英文词再检；")
        print("  4) 把每个词的命中数如实记入检索记录，0 命中也留痕。")
    if not rows:
        print("\n本次 0 条结果。请检查网络，或换更上位的词重检（例：chatbot→artificial intelligence）。")
    else:
        print("\n下一步：用 tools/literature_organizer.py 去重分类，再用 tools/literature_cards.py 把重点做成卡片网页。")
        print("找不到全文时走合法途径：学校图书馆已购权限、开放获取（OA）版本、联系作者或馆际互借，不要用盗版站点。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
