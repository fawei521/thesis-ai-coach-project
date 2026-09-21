#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文献知识库检索器（v1.99，菜单第 29 项）——AI 回答领域事实问题之前先跑这个。

为什么是它：`core/evidence-rigor.md` 第三节要求"本轮要用请重新读一次文件"，可学生和 AI
都没有地方知道**本地已经核过哪一句**。本工具把库里的卡片按相关度排出来，并且**只报文件名与行号**——
它不替你判断真假，它负责让你能在 30 秒内打开原文那一行。

算法与代价（对学生如实说明）：词法检索 BM25（Robertson & Zaragoza 2009，Foundations and Trends
in IR 3(4):339 一系；k1=1.2、b=0.75 与 Lucene/Elasticsearch/SQLite FTS5 三处默认值一致），
中文按**二元切分**建索引（Lucene `CJKAnalyzer`、Elasticsearch 内建 `cjk` 分析器同一做法）。
- 好处：**纯标准库、离线、零安装**，每条命中都带行号，能逐行核对——这是向量检索给不了的。
- 短处：只认字面词，**近义表述会漏**（官方对这套办法的边界说明："approximate word boundaries"）。
  搜不到不等于库里没有：换同义词/上位词/英文再试，仍按 `core/evidence-rigor.md` 第四节报
  "已用这些词检索，各命中多少"，**不许报"没有"**。
- 为什么不用向量：语义检索要有 embedding 模型（云 API 或本地 torch 依赖），而本包承诺
  "不装任何第三方库也能完整运行"（`requirements.txt`）；且本项目研究青少年自伤，
  把文献摘录上传做向量化触及 `psychology/ethics.md` 的边界。取舍见 `core/literature-kb.md` 第五节。

红线：**只读**。本工具不写任何文件、不改任何卡片（对齐宪法第七条"可复现、可人工核对"）。

用法：
  python tools/kb_search.py 孤独感 中介
  python tools/kb_search.py "反刍思维" --top 8 --full-only
  python tools/kb_search.py CAIDS --verbatim     # 只搜「逐字原文」行
"""
import argparse
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 默认 GBK，遇 ⚠ ↔ ² 会崩）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
K1, B = 1.2, 0.75                     # 与 Lucene/ES/FTS5 默认一致
CJK = "一-鿿㐀-䶿豈-﫿"
IS_CJK = re.compile("^[%s]$" % CJK)
TOKEN = re.compile(r"[a-z0-9]+|[%s]" % CJK)   # 不按 . - _ 续接：那样 "CAIDS-20" 会成为一个整词，
                                               # 查 "CAIDS" 就搜不到它——与 Lucene 标准分词器的切法一致。


def tokenize(text):
    """中文出相邻二元组、英文数字出整词；落单的中文字退出一元（Lucene CJKAnalyzer 同款行为）。

    走一遍正则扫描即可，别按字符逐个再 index 回原文——那样找到的"位置"永远是首次出现，
    重复出现的字会被切错，而且整篇是 O(n²)。
    """
    toks, run = [], []

    def flush():
        if len(run) == 1:
            toks.append(run[0])
        for i in range(len(run) - 1):
            toks.append(run[i] + run[i + 1])
        run.clear()

    for m in TOKEN.finditer(text.lower()):
        s = m.group(0)
        if IS_CJK.match(s):
            run.append(s)
        else:
            flush()
            toks.append(s)
    flush()
    return toks


SCOPE = re.compile(r"我读到哪一层.*?`([^`]+)`")
VERIFIED = re.compile(r"学生核对过没有.*?`([^`]+)`")
LOCAL = re.compile(r"本地原文在哪.*?`([^`]+)`")


def read_card(path):
    """一张卡 → (行列表, 词频, 元信息)。行号从 1 起，与编辑器里看到的行号一致。"""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as e:
        print("  ！读不了 %s：%s" % (path.name, e), file=sys.stderr)
        return None
    meta, verbatim, body = {}, [], []
    for i, ln in enumerate(lines, 1):
        for pat, key in ((SCOPE, "scope"), (VERIFIED, "checked"), (LOCAL, "local")):
            if key not in meta:
                mm = pat.search(ln)
                if mm:
                    meta[key] = mm.group(1)
        if ln.lstrip().startswith(">"):        # 只认引用块那一行=真正的逐字引文。
            verbatim.append(i)                 # 别把"- **逐字原文**："标签行也算进去，
                                               # 否则 --verbatim 给你看的是标签而不是那句话。
        body.append((i, ln))
    return {"path": path, "lines": lines, "tf": Counter(tokenize("\n".join(lines))),
            "vlines": verbatim, "meta": meta}


def build(cards, verbatim_only):
    docs = []
    for c in cards:
        if verbatim_only and c["vlines"]:
            text = "\n".join(c["lines"][i - 1] for i in c["vlines"])
        else:
            text = "\n".join(c["lines"])
        docs.append(Counter(tokenize(text)))
    return docs


def search(query, cards, top, verbatim_only):
    docs = build(cards, verbatim_only)
    n = len(docs)
    if not n:
        return []
    dlen = [max(sum(d.values()), 1) for d in docs]
    avg = sum(dlen) / n
    df = defaultdict(int)
    for d in docs:
        for t in d:
            df[t] += 1
    terms = set(tokenize(query))
    per_doc = defaultdict(float)
    for term in terms:
        n_t = df.get(term, 0)
        if not n_t:
            continue
        idf = math.log(1 + (n - n_t + .5) / (n_t + .5))
        for idx, d in enumerate(docs):
            f = d.get(term, 0)
            if f:
                per_doc[idx] += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * dlen[idx] / avg))
    ranked = sorted(per_doc.items(), key=lambda kv: -kv[1])[:top]
    return [(sc, cards[idx], list(terms)) for idx, sc in ranked]


def main():
    ap = argparse.ArgumentParser(description="本地文献知识库检索（只读，输出行号供回原文核对）")
    ap.add_argument("query", nargs="+", help="检索词，可多个（概念间是 AND 效果：多词共现排得高）")
    ap.add_argument("--dir", default="我的工作区/10-知识库", help="库目录（默认学生工作区知识库）")
    ap.add_argument("--top", type=int, default=5, help="最多报几张卡（默认 5；Self-RAG 实测：硬塞更多篇反而更差）")
    ap.add_argument("--verbatim", action="store_true", help="只在「逐字原文」行里搜（找具体那句话时用）")
    ap.add_argument("--full-only", action="store_true", help="只看「我读到哪一层=全文PDF」的卡")
    ap.add_argument("--checked-only", action="store_true", help="只看学生已逐字比对过的卡")
    a = ap.parse_args()
    d = (ROOT / a.dir) if not Path(a.dir).is_absolute() else Path(a.dir)
    if not d.is_dir():
        print("✗ 找不到库目录：%s\n  先跑菜单第 28 项建库，或 --dir 指到你放卡片的地方。" % d)
        return 1
    cards = [c for c in (read_card(p) for p in sorted(d.rglob("*.md")))
             if c and c["tf"]]
    if a.full_only:
        cards = [c for c in cards if c["meta"].get("scope") == "全文PDF"]
    if a.checked_only:
        cards = [c for c in cards if "已逐字" in c["meta"].get("checked", "")]
    q = " ".join(a.query)
    hits = search(q, cards, a.top, a.verbatim)
    print("=" * 66)
    print("知识库检索：%s　　库：%s（%d 张卡）" % (q, a.dir, len(cards)))
    print("=" * 66)
    if not hits:
        print("⚠ 0 命中。这不等于库里没有——"
              "换同义词/上位词/英文名再试一轮；仍 0 命中就说“已用这些词检索未命中”，别说“没有”。")
        print("  还可以试：--verbatim（只搜逐字原文行）、去掉 --full-only/--checked-only 放宽条件。")
        return 0
    for rank, (score, c, terms) in enumerate(hits, 1):
        m = c["meta"]
        scope, checked = m.get("scope", "未声明"), m.get("checked", "未声明")
        flag = "" if scope == "全文PDF" else "　⚠切片级：本卡不得用于下结论（evidence-rigor 第二节）"
        if checked != "未声明" and "已逐字" not in checked:
            flag += "｜⚠学生未核对：AI 起草的卡不算已核实"
        print("\n%d. %s　得分 %.2f%s" % (rank, c["path"].name, score, flag))
        print("   读到哪一层：%s　学生核对：%s" % (scope, checked))
        if m.get("local") and m["local"] not in ("无", "原文未报告", ""):
            lf = ROOT / m["local"]
            print("   本地原文：%s（%s）" % (m["local"], "存在" if lf.exists() else "！路径失效，去菜单第 26 项重新取"))
        shown = c["vlines"] if (a.verbatim and c["vlines"]) else _best_lines(c, terms)
        for ln in shown[:3]:
            print("   > L%-4d| %s" % (ln, c["lines"][ln - 1].strip()[:96]))
    print("\n" + "-" * 66)
    print("下一步（AI 必须做完再作答）：打开上面那张卡的**那一行**读上下文，")
    print("  引用时报“卡片文件＋行号”；要写进正式稿则回 `本地原文` 那个文件核一遍原句（三查第三查要独立源）。")
    print("  卡片不自动等于证据：它只是把你上次核到的位置标出来。详见 core/literature-kb.md。")
    return 0


def _best_lines(card, terms):
    """给每张卡挑最能代表命中位置的行：逐字原文行优先，其次含检索词的行。"""
    scored = []
    for i, ln in enumerate(card["lines"], 1):
        s = sum(1 for t in terms if t in ln.lower())
        if s:
            scored.append((s + (2 if i in card["vlines"] else 0), i))
    return [i for _, i in sorted(scored, reverse=True)[:3]] or \
           [i for i in card["vlines"][:3]] or [1]


if __name__ == "__main__":
    sys.exit(main())
