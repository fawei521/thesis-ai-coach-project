#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文献原文可获取性探测、下载与落盘体检（v1.98，菜单第 26 项）。
为什么需要它：`paper_search.py` 只给题录与摘要，而 `core/evidence-rigor.md` 第一节把"读的是什么材料"
列为引用四要素之一——**只有摘要时不得输出"该研究发现 X"级别的结论**。这一项把"能不能拿到全文"
变成一次可复跑的检查，公开原文落到 `我的工作区/01-文献PDF/原文/`，综述里每条数字才有地方可翻。
清单（CSV 或 JSON）：id, doi, pmcid, arxiv, url, expect_title——填其中任意几个即可。
**expect_title 一定要填**：它做"标题回核"。DOI 打错一位会静默取回**另一篇**文献，
比下载失败更危险（v1.98 实测：Brand 2019 的 DOI 尾号猜成 …023，Crossref 返回了一篇讲孤独症退化的文章）。
用法：python tools/lit_fetch.py 清单.csv --probe（探测）／--go（下载，默认上限 30 篇，--max/--delay 可调）
     python tools/lit_fetch.py --audit   清单可省（体检已落盘的原文：页数/文字层/首页标题，见 `lit_audit.py`）
**下载成功 ≠ 原文到手**：--go 之后、或你手工放进原文区的文件，都要跑一次 --audit 验明正身。
红线与 `workflows/literature-auto-search.md` 第八节同源，此处只执行不重述：只走公开入口、
不绕付费墙、不碰要登录的库、逐篇带停顿、单次限量；下载的原文仅限本人学习研究使用。
"""
import argparse
import csv
import difflib
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
      "Accept": "*/*"}
ALIAS = {"id": ("id", "编号", "no", "标签"), "doi": ("doi", "DOI"),
         "pmcid": ("pmcid", "pmc", "PMCID"), "arxiv": ("arxiv", "arxivid", "arXiv"),
         "url": ("url", "链接", "pdf", "url_pdf"),
         "expect_title": ("expect_title", "title", "题名", "标题")}


def read_rows(path):
    """吃 CSV 或 JSON 清单；UTF-8-sig / GB18030 都认。"""
    text = None
    for enc in ("utf-8-sig", "gb18030"):
        try:
            text = Path(path).read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise SystemExit("清单编码识别失败（只支持 UTF-8 / GBK 系）：" + str(path))
    if path.lower().endswith(".json"):
        raw = json.loads(text)
    else:
        raw = list(csv.DictReader(text.splitlines()))
    rows = []
    for item in raw:
        row = {}
        for key, names in ALIAS.items():
            for n in names:
                if str(item.get(n, "")).strip():
                    row[key] = str(item[n]).strip()
                    break
        if row.get("id") and not row["id"].startswith("#"):   # 模板里的 # 说明行不算数据
            rows.append(row)
    return rows


def fetch(url, timeout=60, tries=3):
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except Exception as exc:                     # 校园网/代理常抖，退避重试
            last = exc
            time.sleep(2 * (n + 1))
    raise last


def is_pdf(data):
    return data[:1024].lstrip().startswith(b"%PDF")


def candidates(row):
    """按来源类型给候选地址；顺序＝越可能直取越靠前。付费墙内的库不出地址。"""
    out = [(("直链", row["url"]))] if row.get("url") else []
    pmc = row.get("pmcid", "")
    if pmc:
        pid = pmc if pmc.upper().startswith("PMC") else "PMC" + pmc
        out.append(("PMC", "https://pmc.ncbi.nlm.nih.gov/articles/%s/pdf/" % pid))
        out.append(("EuropePMC全文",
                    "https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pid))
    ax = row.get("arxiv", "")
    if ax:
        out.append(("arXiv", "https://arxiv.org/pdf/%s" % ax.split("v")[0]))
    doi = row.get("doi", "")
    if doi:
        low = doi.lower()
        if "frontiersin" in low or "10.3389/" in low:
            out.append(("Frontiers", "https://www.frontiersin.org/articles/%s/pdf" % doi))
        elif "10.1186/" in low or "bmc" in low:
            out.append(("BMC", "https://bmcpsychology.biomedcentral.com/counter/pdf/%s.pdf" % doi))
        elif "10.1038/" in low:
            out.append(("Nature", "https://www.nature.com/%s.pdf" % doi.split("10.1038/")[-1]))
    return out


def crossref_title(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    msg = json.loads(fetch(url, timeout=30)[2].decode("utf-8", "ignore"))["message"]
    return (msg.get("title") or [""])[0]


def same_title(a, b):
    """归一化后比：互相包含算同题；否则看相似度。**只用于"DOI 有没有指向另一篇"这种粗判**。"""
    na = re.sub(r"[^0-9a-z\u4e00-\u9fa5]", "", (a or "").lower())
    nb = re.sub(r"[^0-9a-z\u4e00-\u9fa5]", "", (b or "").lower())
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.8


def probe(row, go, out_dir):
    rec = dict(id=row["id"], status="", detail="", path="", source="")
    cl = candidates(row)
    if not cl:
        rec.update(status="需数据库", detail="清单里只有题录、无公开入口（付费墙或需登录）")
        return rec
    if row.get("doi") and row.get("expect_title"):
        try:
            got = crossref_title(row["doi"])
            if not same_title(got, row["expect_title"]):
                rec.update(status="标题对不上",
                           detail="DOI 指向《%s》，与清单期望《%s》不是一条——先修 DOI" % (got[:40], row["expect_title"][:40]))
                return rec
        except Exception as exc:
            rec["detail"] = "标题回核没做成(%s)；" % type(exc).__name__
    for kind, url in cl:
        try:
            st, ctype, body = fetch(url)
        except Exception as exc:
            rec.update(status="失败", detail="%s 取不到：%s %s" % (kind, type(exc).__name__, url[:60]))
            continue
        as_pdf = is_pdf(body) or ("pdf" in ctype.lower() and len(body) > 20000)
        as_xml = body.lstrip()[:5] == b"<?xml" and b"<article" in body[:6000]
        if not (as_pdf or as_xml):
            rec.update(status="非PDF", detail="%s 返回 %s(%s) %dKB" % (kind, ctype.split(";")[0], st, len(body) // 1024))
            continue
        rec["source"] = url
        ext = ".pdf" if as_pdf else ".xml"      # 开放全文 XML 一样能逐字引用，且比扫描版 PDF 更好查
        if go:
            dest = out_dir / (re.sub(r"[\\:*?\"<>|]", "_", row["id"]) + ext)
            dest.write_bytes(body)
            rec["path"] = dest.name
        rec.update(status=("已获取" if go else "可获取") + ("" if as_pdf else "(全文XML)"),
                   detail="%s %dKB ← %s" % (kind, len(body) // 1024, url[:70]))
        return rec
    return rec


def main():
    ap = argparse.ArgumentParser(description="文献原文可获取性探测、下载与落盘体检（不绕付费墙）")
    ap.add_argument("manifest", nargs="?", default="",
                    help="清单 CSV 或 JSON（列：id,doi,pmcid,arxiv,url,expect_title）；--audit 时可省")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe", action="store_true", help="只探测能不能拿到，不落盘")
    mode.add_argument("--go", action="store_true", help="下载公开全文 PDF 到 --out")
    mode.add_argument("--audit", action="store_true",
                      help="体检 --out 目录里已落盘的原文（页数/文字层/标题回核），有坏件返回 1")
    ap.add_argument("--out", default="我的工作区/01-文献PDF/原文", help="落盘目录（默认原文区）")
    ap.add_argument("--max", type=int, default=30, help="本次最多取几篇（红线：逐篇、限量）")
    ap.add_argument("--delay", type=float, default=2.0, help="篇间隔秒数（模拟人工节奏）")
    ap.add_argument("--report", default="我的工作区/01-文献PDF/原文获取台账.md", help="台账输出路径")
    a = ap.parse_args()
    if a.audit:                                   # 落盘之后还要开一次：下载成功 ≠ 原文到手
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from lit_audit import run_dir
        return run_dir(a.out, read_rows(a.manifest) if a.manifest else ())
    rows = read_rows(a.manifest)
    if not rows:
        print("清单里没读到任何带 id 的行——列名请用 id,doi,pmcid,arxiv,url,expect_title")
        return 1
    out_dir = Path(a.out)
    if a.go:
        out_dir.mkdir(parents=True, exist_ok=True)
    print("清单 %d 条｜模式 %s｜本次上限 %d 篇｜篇间隔 %.1f 秒"
          % (len(rows), "下载" if a.go else "探测", a.max, a.delay))
    done, results = 0, []
    for row in rows:
        if a.go and done >= a.max:
            results.append(dict(id=row["id"], status="未尝试", detail="已到本次限量 %d 篇，歇一会儿再跑" % a.max))
            continue
        rec = probe(row, a.go, out_dir)
        results.append(rec)
        if rec["status"].startswith(("已获取", "可获取")):
            done += 1
        print("  [%s] %-6s %s" % (row["id"], rec["status"], rec["detail"][:76]))
        time.sleep(a.delay)
    from collections import Counter
    tally = Counter(r["status"] for r in results)
    print("\n汇总：" + "｜".join("%s %d" % (k, v) for k, v in sorted(tally.items())))
    rep = Path(a.report)
    rep.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# 文献原文获取台账", "",
             "> 生成：`tools/lit_fetch.py %s %s`。状态六态：已获取/可获取=公开全文能拿到；"
             "**需数据库**=只能走知网/学校已购权限（见 `workflows/literature-auto-search.md` 第五步）；"
             "非PDF/失败=换源或人工；**标题对不上**=DOI 指向了别的文章，先修题录再谈下载。" % (a.manifest, "--go" if a.go else "--probe"),
             "", "| 编号 | 状态 | 来源/原因 |", "|---|---|---|"]
    lines += ["| %s | %s | %s |" % (r["id"], r["status"], r["detail"].replace("|", "/")[:120])
              for r in results]
    rep.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("台账已写：" + str(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
