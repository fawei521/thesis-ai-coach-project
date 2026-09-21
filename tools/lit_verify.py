#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题录双源核验：查"这条文献是不是真的、字段对不对"（v1.98，菜单第 27 项）。
它管的是 `CONSTITUTION.md` 第一条与 `core/evidence-rigor.md` 第一节里最要命的一种事故：
**题录看起来完整、其实是编的或安错了文章**——杜撰的标题、把 A 刊写成 B 刊、DOI 猜一位数字
指向了另一篇，都属于"格式没问题、内容全错"，人眼扫一遍扫不出来，逐字段比对才出得来。
两个登记处互为独立源（换源复核＝三查里的第三查）：Crossref（出版方登记的 DOI 元数据）与
OpenAlex（另一家索引库）。两家一致→`双源一致`；只有一家→`单源`；口径不同→逐字段点名差在哪。
它**不生成文献、不替你补字段**：查不到就输出 `登记处查无` 并保留原条目，由你回原文
（知网/出版社页面/PDF 版权页）定夺。缺什么标什么，绝不填一个"看着像"的值。
用法：python tools/lit_verify.py 题录.csv [--gbt] [--strict]；报告写到 同名_题录核验.md（--out 可改）
"""
import argparse
import csv
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 控制台默认 GBK，遇 ⚠ ↔ 等字符会直接崩；门禁与 AI 都以管道读输出）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
      "Accept": "application/json"}
ALIAS = {"title": ("title", "题名", "标题"), "authors": ("authors", "作者"),
         "year": ("year", "年份", "年"), "journal": ("journal", "期刊", "来源", "刊名"),
         "volume": ("volume", "卷"), "issue": ("issue", "期"), "pages": ("pages", "页", "页码"),
         "doi": ("doi", "DOI")}


def read_rows(path):
    text = None
    for enc in ("utf-8-sig", "gb18030"):
        try:
            text = Path(path).read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise SystemExit("题录表编码识别失败（只支持 UTF-8 / GBK 系）：" + str(path))
    rows = list(csv.DictReader(text.splitlines())) if path.lower().endswith(".csv") \
        else json.loads(text)
    out = []
    for r in rows:
        row = {k: next((str(r[n]).strip() for n in names if str(r.get(n, "")).strip()), "")
               for k, names in ALIAS.items()}
        if row["title"] and not row["title"].startswith("#"):   # 模板里的 # 说明行不算数据
            out.append(row)
    return out


def get_json(url, timeout=30, tries=3):
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            return json.loads(body.decode("utf-8", "ignore"))
        except Exception as exc:
            last = exc
            time.sleep(2 * (n + 1))
    raise last


def from_crossref(doi=None, title=None):
    url = ("https://api.crossref.org/works/" + urllib.parse.quote(doi) if doi
           else "https://api.crossref.org/works?" + urllib.parse.urlencode(
               {"query.bibliographic": title, "rows": 1}))
    m = get_json(url)["message"]
    item = m if doi else (m.get("items") or [{}])[0]
    per = item.get("author") or item.get("editor") or []
    yr = ((item.get("issued", {}).get("date-parts") or [[None]])[0][0])
    return dict(title=html.unescape((item.get("title") or [""])[0]).strip(),
                journal=html.unescape((item.get("container-title") or [""])[0]).strip(),
                volume=str(item.get("volume", "") or ""), issue=str(item.get("issue", "") or ""),
                pages=str(item.get("page", "") or item.get("article-number", "") or ""),
                year=("" if yr is None else str(yr)), doi=item.get("DOI", ""),
                authors="; ".join("%s %s" % (p.get("family", ""), (p.get("given", "") or "")[:1])
                                  for p in per[:3]))


def from_openalex(doi=None, title=None):
    url = ("https://api.openalex.org/works/doi:" + doi if doi
           else "https://api.openalex.org/works?" + urllib.parse.urlencode(
               {"filter": "title.search:" + title, "per-page": 1}))
    j = get_json(url)
    w = j if "biblio" in j else (j.get("results") or [{}])[0]
    b = w.get("biblio") or {}
    src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "")
    fp, lp = str(b.get("first_page") or ""), str(b.get("last_page") or "")
    return dict(title=(w.get("title") or w.get("display_name") or "").strip(), journal=src,
                volume=str(b.get("volume", "") or ""), issue=str(b.get("issue", "") or ""),
                pages=("-".join(x for x in (fp, lp) if x)) or str(b.get("article_number") or ""),
                year=str(w.get("publication_year") or ""),
                doi=(w.get("doi") or "").replace("https://doi.org/", ""),
                authors="; ".join((a.get("author") or {}).get("display_name", "")
                                  for a in (w.get("authorships") or [])[:3]))


def norm(s):
    return re.sub(r"[^0-9a-z一-龥]", "", (s or "").lower())


def page_eq(a, b):
    a, b = norm(a), norm(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def diff(rec, expect):
    """逐字段比；只比"期望值与登记值都非空"的对，缺字段另列。"""
    bad = []
    for f, cn in (("year", "年"), ("volume", "卷"), ("pages", "页")):
        e, c = str(expect.get(f, "")).strip(), str(rec.get(f, "")).strip()
        if e and c and norm(e) != norm(c) and not (f == "pages" and page_eq(e, c)):
            bad.append("%s:%s≠%s" % (cn, e, c))
    et, rt = norm(expect.get("title")), norm(rec.get("title"))
    if et and rt and et[:36] != rt[:36]:
        bad.append("标题对不上")
    ej, rj = norm(expect.get("journal")), norm(rec.get("journal"))
    if ej and rj and ej[:20] not in rj[:24] and rj[:20] not in ej[:24]:
        bad.append("刊名对不上")
    return bad


def verdict(row):
    """→ dict(状态, 差异, 依据, 取到)。状态五态，判据见 `core/evidence-rigor.md` 三查。"""
    def mk(st, d, why, got):
        return dict(状态=st, 差异=d, 依据=why, 取到=got)
    srcs, errs = {}, {}
    for name, fn in (("crossref", from_crossref), ("openalex", from_openalex)):
        try:
            srcs[name] = fn(doi=row.get("doi") or None, title=None if row.get("doi") else row["title"])
        except Exception as exc:
            errs[name] = type(exc).__name__
        time.sleep(0.6)
    if not srcs:
        return mk("登记处查无", "", "两家都没返回记录；" + json.dumps(errs, ensure_ascii=False), {})
    if len(srcs) == 1:
        only = list(srcs)[0]
        return mk("单源", "、".join(diff(srcs[only], row)),
                  "只有 %s 有记录（另一家：%s）" % (only, errs), srcs[only])
    a, b = srcs["crossref"], srcs["openalex"]
    cross = [k for k in ("year", "volume", "pages", "title")
             if a.get(k) and b.get(k) and not (
                 norm(a[k]) == norm(b[k]) or (k == "pages" and page_eq(a[k], b[k])))]
    got = dict(a, **{k: v for k, v in b.items() if not a.get(k)})
    if cross:
        return mk("双源互斥", "两源不一致:" + "/".join(cross),
                  "CR=%s／OA=%s" % (json.dumps({k: a[k] for k in cross}, ensure_ascii=False)[:90],
                                    json.dumps({k: b[k] for k in cross}, ensure_ascii=False)[:90]), got)
    mine = sorted(set(diff(a, row) + diff(b, row)))
    if mine:
        return mk("有出入", "、".join(mine),
                  "两源一致但与你的条目不同——以登记处＋原文版权页为准", got)
    return mk("双源一致", "", "Crossref 与 OpenAlex 逐字段一致", got)
    return mk("双源一致", "", "Crossref 与 OpenAlex 逐字段一致", got)


def gbt(rec):
    return "%s. %s[J]. %s, %s, %s%s: %s. DOI:%s." % (
        rec.get("authors") or "", rec.get("title", ""), rec.get("journal", ""),
        rec.get("year", ""), rec.get("volume", ""),
        ("(%s)" % rec["issue"]) if rec.get("issue") else "",
        rec.get("pages", ""), rec.get("doi", ""))


def main():
    ap = argparse.ArgumentParser(description="题录双源核验（Crossref + OpenAlex），不生成文献")
    ap.add_argument("csv", help="题录表 CSV/JSON（列：题名,作者,年份,期刊,卷,期,页,DOI）")
    ap.add_argument("--gbt", action="store_true", help="同时输出 GB/T 7714 条目（字段取自登记处）")
    ap.add_argument("--out", default="", help="报告输出路径（默认 同名_题录核验.md）")
    ap.add_argument("--strict", action="store_true", help="有 有出入/双源互斥/查无 时返回失败码")
    a = ap.parse_args()
    rows = read_rows(a.csv)
    if not rows:
        print("题录表里没读到带「题名」的行——列名用 题名/作者/年份/期刊/卷/期/页/DOI")
        return 1
    print("待核 %d 条（每条约 2 次查询，逐条串行，不并发压库）" % len(rows))
    results = []
    flags = {"双源一致": "OK", "单源": "!!", "有出入": "XX", "双源互斥": "XX", "登记处查无": "??"}
    for row in rows:
        v = verdict(row)
        results.append(dict(条目=row, **v))
        print("  [%s] %-6s《%s》 %s" % (flags[v["状态"]], v["状态"], row["title"][:34], v["差异"]))
    from collections import Counter
    tally = Counter(r["状态"] for r in results)
    print("\n汇总：" + "｜".join("%s %d" % (k, v) for k, v in sorted(tally.items())))

    out = Path(a.out) if a.out else Path(a.csv).with_name(Path(a.csv).stem + "_题录核验.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# 题录双源核验报告", "",
             "> 生成：`tools/lit_verify.py %s`。两个登记处互为独立源（`core/evidence-rigor.md` 三查第三查）。"
             "**本工具不生成文献、不替你补字段**：`有出入`／`双源互斥`／`登记处查无` 的行必须回原文定夺，"
             "补不到就删条——引一条查无此文的参考文献，比少引一条严重得多。" % Path(a.csv).name, "",
             "| 状态 | 你的条目 | 登记处 | 差异 | 依据 |", "|---|---|---|---|---|"]
    lines += ["| %s | %s（%s %s） | %s | %s | %s |" % (
                  r["状态"], (r["条目"].get("title") or "")[:40], r["条目"].get("journal", ""),
                  r["条目"].get("year", ""), (r["取到"].get("title") or "—")[:40],
                  r["差异"] or "—", r["依据"][:120]) for r in results]
    if a.gbt:
        lines += ["", "## GB/T 7714-2015 条目（字段取自登记处，**发表年卷以原文版权页为最终依据**）", ""]
        lines += ["- %s%s" % (gbt(r["取到"]), "" if r["状态"] == "双源一致"
                              else "  （状态：%s，先核再用）" % r["状态"])
                  for r in results if r["取到"]]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("报告已写：" + str(out))
    bad = sum(tally.get(k, 0) for k in ("有出入", "双源互斥", "登记处查无"))
    return 1 if (a.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
