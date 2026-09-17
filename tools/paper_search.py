#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英文学术文献检索工具
数据源：OpenAlex（免费，无需API key，2.4亿篇文献）、Semantic Scholar（免费）
用法：
  python paper_search.py --query "AI emotional dependence adolescent" --limit 20
  python paper_search.py --source semantic --query "non-suicidal self-injury rumination" --limit 15
  python paper_search.py --query "loneliness mediation" --output results.csv
健壮性：单个数据源 429 限流/超时会自动等待重试一次；仍失败则自动换另一个数据源再试。
"""

import json
import csv
import sys
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _open_with_retry(req, source_name, attempts=2):
    """带重试的 urlopen：429 限流等待 3 秒重试一次，其他网络错误等待 2 秒重试一次。
    成功返回 response；两次都失败返回 None（None=网络失败，区别于"零结果"的 []）。"""
    last_err = None
    for i in range(attempts):
        try:
            return urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and i < attempts - 1:
                print(f"{source_name} 返回 429 限流，等待 3 秒后自动重试一次……")
                time.sleep(3)
                continue
            print(f"网络错误：HTTP {e.code} {e.reason}（{source_name}）")
            return None
        except urllib.error.URLError as e:
            last_err = e
            if i < attempts - 1:
                print(f"{source_name} 连接失败（{e.reason}），等待 2 秒后自动重试一次……")
                time.sleep(2)
                continue
            print(f"网络错误：{e}（{source_name}）")
            return None
    print(f"网络错误：{last_err}（{source_name}）")
    return None


def search_openalex(query, limit=20):
    """通过OpenAlex API检索文献（免费，无需key）；网络失败返回 None，零结果返回 []"""
    base_url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per_page": min(limit, 50),
        "sort": "relevance_score:desc",
        "filter": "type:article",
    }
    url = base_url + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={
        "User-Agent": "ThesisAICoach/1.0 (mailto:student@example.com)"
    })

    response = _open_with_retry(req, "OpenAlex")
    if response is None:
        return None
    data = json.loads(response.read().decode("utf-8"))

    results = []
    for work in data.get("results", []):
        # 提取作者
        authors = []
        for authorship in work.get("authorships", [])[:5]:
            name = authorship.get("author", {}).get("display_name", "")
            if name:
                authors.append(name)
        author_str = ", ".join(authors)
        if len(work.get("authorships", [])) > 5:
            author_str += " et al."

        # 提取期刊
        source = work.get("primary_location", {}).get("source", {}) or {}
        journal = source.get("display_name", "")

        # 提取年份
        pub_date = work.get("publication_date", "")
        year = pub_date[:4] if pub_date else ""

        # 提取DOI
        doi = work.get("doi", "") or ""
        if doi and doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        # 摘要（OpenAlex用倒排索引存储）
        abstract = ""
        abstract_inverted = work.get("abstract_inverted_index", {})
        if abstract_inverted:
            word_positions = []
            for word, positions in abstract_inverted.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort()
            abstract = " ".join(w for _, w in word_positions)

        # 开放获取链接
        oa_url = ""
        best_oa = work.get("open_access", {}) or {}
        oa_url = best_oa.get("oa_url", "") or ""
        if not oa_url:
            primary = work.get("primary_location", {}) or {}
            oa_url = primary.get("pdf_url", "") or ""

        results.append({
            "标题": work.get("title", ""),
            "作者": author_str,
            "年份": year,
            "期刊": journal,
            "DOI": doi,
            "被引次数": work.get("cited_by_count", 0),
            "摘要": abstract[:500],
            "开放获取链接": oa_url,
            "语言": work.get("language", ""),
        })

    return results


def search_semantic_scholar(query, limit=20):
    """通过Semantic Scholar API检索文献（免费，无需key）；网络失败返回 None，零结果返回 []"""
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": "title,authors,year,venue,externalIds,citationCount,abstract,tldr,openAccessPdf",
    }
    url = base_url + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={
        "User-Agent": "ThesisAICoach/1.0"
    })

    response = _open_with_retry(req, "Semantic Scholar")
    if response is None:
        return None
    data = json.loads(response.read().decode("utf-8"))

    results = []
    for paper in data.get("data", []):
        authors = []
        for a in paper.get("authors", [])[:5]:
            name = a.get("name", "")
            if name:
                authors.append(name)
        author_str = ", ".join(authors)
        if len(paper.get("authors", [])) > 5:
            author_str += " et al."

        ids = paper.get("externalIds", {}) or {}
        doi = ids.get("DOI", "")

        abstract = paper.get("abstract", "") or ""
        tldr = paper.get("tldr", {}) or {}
        if tldr and tldr.get("text"):
            abstract = tldr["text"] + " [TLDR] " + abstract

        oa_pdf = paper.get("openAccessPdf", {}) or {}
        pdf_url = oa_pdf.get("url", "") if oa_pdf else ""

        results.append({
            "标题": paper.get("title", ""),
            "作者": author_str,
            "年份": paper.get("year", ""),
            "期刊": paper.get("venue", ""),
            "DOI": doi,
            "被引次数": paper.get("citationCount", 0),
            "摘要": abstract[:500],
            "开放获取链接": pdf_url,
            "语言": "",
        })

    return results


def export_csv(results, output_path):
    """导出为CSV"""
    if not results:
        print("没有结果可导出。")
        return

    out_p = Path(output_path)
    if out_p.parent and not out_p.parent.exists():
        out_p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["序号", "标题", "作者", "年份", "期刊", "DOI", "被引次数", "摘要", "开放获取链接", "语言"]
    with open(out_p, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, r in enumerate(results, 1):
            row = {"序号": i}
            row.update(r)
            writer.writerow(row)

    print(f"结果已导出：{output_path}（共{len(results)}篇）")


def print_results(results, max_show=10):
    """打印检索结果"""
    print("\n" + "=" * 70)
    print(f"检索结果（共{len(results)}篇，显示前{min(max_show, len(results))}篇）")
    print("=" * 70)

    for i, r in enumerate(results[:max_show], 1):
        print(f"\n[{i}] {r['标题']}")
        print(f"    作者：{r['作者']}")
        print(f"    年份：{r['年份']}  期刊：{r['期刊']}")
        print(f"    被引：{r['被引次数']}  DOI：{r['DOI']}")
        if r["摘要"]:
            print(f"    摘要：{r['摘要'][:150]}...")
        if r["开放获取链接"]:
            print(f"    免费下载：{r['开放获取链接']}")

    if len(results) > max_show:
        print(f"\n...还有{len(results) - max_show}篇，导出CSV查看全部。")


SEARCHERS = {
    "openalex": ("OpenAlex", search_openalex),
    "semantic": ("Semantic Scholar", search_semantic_scholar),
}


def main():
    parser = argparse.ArgumentParser(description="英文学术文献检索工具（免费API）")
    parser.add_argument("--query", "-q", required=True, help="检索关键词（英文）")
    parser.add_argument("--source", "-s", choices=["openalex", "semantic"],
                        default="openalex", help="数据源（默认openalex，稳定免费）")
    parser.add_argument("--limit", "-n", type=int, default=20, help="返回数量（默认20）")
    parser.add_argument("--output", "-o", help="输出CSV文件路径")
    args = parser.parse_args()

    print("=" * 70)
    print("英文学术文献检索工具")
    print("=" * 70)
    print(f"首选数据源：{args.source}")
    print(f"关键词：{args.query}")
    print(f"数量：{args.limit}")
    print("正在检索，请稍候...\n")

    # 首选源；网络失败（None）时自动换另一个源重试一次；零结果（[]）不换源
    order = [args.source] + [s for s in ("openalex", "semantic") if s != args.source]
    results, used_source = None, None
    for s in order:
        name, fn = SEARCHERS[s]
        r = fn(args.query, args.limit)
        if r is None:
            if s != order[-1]:
                print(f"{name} 暂不可用，自动改用另一数据源重试……\n")
                continue
            results = None
            break
        results, used_source = r, name
        break

    if not results:
        if results is None:
            print("两个数据源本次都未能连通（超时/限流）。建议：")
            print("1. 检查网络（校园网/代理），稍后重试；")
            print("2. 再跑一次本命令（工具已内置等待重试与自动换源）；")
            print("3. 仍失败时先用知网等中文库，网络恢复后补英文检索。")
            sys.exit(1)
        print("未检索到结果。建议：")
        print("1. 简化关键词，用2-3个核心词")
        print("2. 换同义词（如 self-injury 换成 NSSI）")
        print("3. 换数据源试试（--source semantic）")
        sys.exit(1)

    print(f"实际命中数据源：{used_source}")
    # 按被引次数排序
    results.sort(key=lambda x: x["被引次数"] if x["被引次数"] else 0, reverse=True)

    print_results(results)

    if args.output:
        export_csv(results, args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_output = Path(f"文献检索结果_{timestamp}.csv")
        export_csv(results, str(default_output))

    print("\n提示：")
    print("- 开放获取链接可以直接下载PDF")
    print("- 没有免费链接的文献，优先通过学校图书馆下载，或用图书馆馆际互借/文献传递；")
    print("  也可在 Google Scholar、ResearchGate、作者主页找合法开放获取版，或邮件向作者索取（请勿使用侵权渠道）")
    print("- 把CSV发给AI，可以帮你筛选、分类、提取重点")


if __name__ == "__main__":
    main()
