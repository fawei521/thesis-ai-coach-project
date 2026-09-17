#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英文学术文献检索工具
数据源：OpenAlex（免费，无需API key，2.4亿篇文献）、Semantic Scholar（免费）
用法：
  python paper_search.py --query "AI emotional dependence adolescent" --limit 20
  python paper_search.py --source semantic --query "non-suicidal self-injury rumination" --limit 15
  python paper_search.py --query "loneliness mediation" --output results.csv
"""

import json
import csv
import sys
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime


def search_openalex(query, limit=20):
    """通过OpenAlex API检索文献（免费，无需key）"""
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

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"网络错误：{e}")
        print("请检查网络连接，或稍后重试。")
        return []

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
    """通过Semantic Scholar API检索文献（免费，无需key）"""
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

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"网络错误：{e}")
        print("Semantic Scholar可能限流，建议改用OpenAlex（--source openalex）")
        return []

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
    print(f"数据源：{args.source}")
    print(f"关键词：{args.query}")
    print(f"数量：{args.limit}")
    print("正在检索，请稍候...\n")

    if args.source == "openalex":
        results = search_openalex(args.query, args.limit)
    else:
        results = search_semantic_scholar(args.query, args.limit)

    if not results:
        print("未检索到结果。建议：")
        print("1. 简化关键词，用2-3个核心词")
        print("2. 换同义词（如 self-injury 换成 NSSI）")
        print("3. 换数据源试试（--source semantic）")
        sys.exit(1)

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
