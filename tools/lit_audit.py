#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""已落盘原文的体检（v1.98 第 26 项的 --audit 模式，纯标准库）。
为什么单独一册：`lit_fetch.py --go` 判的是"网上那篇能不能拿到"，拿到之后**还得开一次看是不是它**。
2026-09-22 实测踩过：知网点"PDF下载"被重定向回首页，落盘的是一个 1.3MB 的期刊宣传图，
文件大小、扩展名、返回码全都"正常"，只有打开看首页才看得出来——**下载成功 ≠ 原文到手**。

它只看形状，不 OCR：
  页数 / 有没有文字层 / 图像页数量 / 从内容流里能读出的可读书串，
  再和清单里的 expect_title 比。**读不出书串不等于文件坏**（子集字体 CID 编码就是这样），
  这时它报"需人工看首页"，绝不把"我读不出"写成"这篇不对"。
"""
import re
import zlib
from pathlib import Path

MIN_BYTES = 20000          # 比这小的 PDF 基本是错误页或占位页
STOP = {"the", "and", "for", "with", "from", "this", "that", "study", "based", "using", "their"}


def payload(data):
    """把所有 FlateDecode 流解压后拼进原始字节，供正则扫。解不动的跳过——本工具不许因为坏流而崩。"""
    out = [data]
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        try:
            out.append(zlib.decompress(m.group(1)))
        except Exception:
            continue
    return b"".join(out)


def readable(buf, limit=600):
    """从 (...)Tj 与 [...]TJ 里抠出可读书串（PDF 字符串里的 \\( \\) \\n 等先还原）。"""
    chunks = re.findall(rb"\(((?:\\.|[^\\()])*)\)", buf)
    text = b" ".join(chunks)
    text = re.sub(rb"\\([()\\])", rb"\1", text)
    text = re.sub(rb"[^ -~]", b" ", text)
    return re.sub(rb"\s+", b" ", text).decode("ascii", "ignore")[:limit]


def words(s):
    return {w for w in re.findall(r"[A-Za-z]{4,}", (s or "").lower()) if w not in STOP}


def match_title(expect, snippet):
    """标题回核，两条判据任一命中即算一致：
    ① 实词重叠（正常抽字的 PDF）；② 去掉所有空格后的连续包含（有些出版方 PDF 逐字定位，
    抽出来是 "D e v e l o p m e n t" 这种，按词比必然全不命中——v1.98 实测把正确的 CAIDS-20 误判过"对不上"）。
    """
    want = list(words(expect))[:8]
    if not want:
        return "无比对材料", 0
    hit = sum(1 for w in want if any(w in h or h in w for h in words(snippet)))
    flat = lambda s: re.sub(r"[^0-9a-z\u4e00-\u9fa5]", "", (s or "").lower())
    ne, ns = flat(expect), flat(snippet)
    probe = ne[:40]                       # 取期望标题前 40 个字符：逐字定位的 PDF 只能截到标题前半截，
    both = len(probe) >= 20 and probe in ns   # 而后面的页眉页脚会污染开头，所以只往"含不含"这一侧判
    if hit >= 2 or both:
        return "一致", max(hit, 2)
    return "标题对不上", hit


def doc_title(data):
    """文档信息里的 /Title——出版方 PDF 常写，比从内容流里抠字可靠。"""
    m = re.search(rb"/Title\s*\(((?:\\.|[^\\()])*)\)", data)
    if not m:
        return ""
    return re.sub(rb"[^ -~]", b" ", re.sub(rb"\\([()\\])", rb"\1", m.group(1))).decode("ascii", "ignore")


def audit_pdf(path, expect=""):
    data = Path(path).read_bytes()
    if not data.lstrip().startswith(b"%PDF") or b"%%EOF" not in data[-2048:]:
        return dict(state="文件坏", pages=0, note="不是完整 PDF（缺 %PDF 头或 %%EOF 尾）")
    buf = payload(data)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", buf)) or len(re.findall(rb"/MediaBox", buf))
    imgs = len(re.findall(rb"/Subtype\s*/Image", buf))
    has_text = bool(re.search(rb"\)\s*T[jJ]", buf)) or b"TJ" in buf
    snip = (doc_title(data) + " " + (readable(buf) if has_text else "")).strip()
    if pages <= 1 and not has_text and imgs:
        return dict(state="疑似拿错", pages=pages,
                    note="单页、无文字层、整页是一张图——重定向页/宣传图就是这个形状")
    if not snip:
        return dict(state="需人工看首页", pages=pages,
                    note="图像版或子集字体，抽不出文字层（%d 页、%d 图页）" % (pages, imgs))
    state, hit = match_title(expect, snip)
    if state == "一致":
        return dict(state="一致", pages=pages, note="可读书串命中期望标题 %d 个实词" % hit)
    if state == "标题对不上":
        return dict(state="标题对不上", pages=pages, note="首页读到的不是清单那篇：" + snip[:60])
    why = "清单没给 expect_title" if not expect else "中文标题或子集字体抽不出可比字串，**只能人工看首页**"
    return dict(state="只报形状", pages=pages, note="%s：%s" % (why, snip[:56]))


def audit_xml(path, expect=""):
    txt = Path(path).read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<article-title>(.*?)</article-title>", txt, re.S)
    got = re.sub(r"<[^>]+>", "", m.group(1)) if m else ""
    if not got:
        return dict(state="文件坏", pages=1, note="XML 里没有 <article-title>")
    state, hit = match_title(expect, got)
    return dict(state=state if state != "无比对材料" else "只报形状", pages=1,
                note=("标题逐字：%s" % got[:70]) if state != "一致" else "标题一致（命中 %d 词）" % hit)


def audit_file(path, expect=""):
    p = Path(path)
    low = p.name.lower()
    if low.endswith(".xml"):
        return audit_xml(p, expect)
    if low.endswith(".pdf"):
        if p.stat().st_size < MIN_BYTES:
            return dict(state="文件坏", pages=0, note="只有 %d 字节，不可能是正文" % p.stat().st_size)
        return audit_pdf(p, expect)
    return dict(state="跳过", pages=0, note="不是 PDF/XML")


def expect_map(manifest_rows):
    """清单里的 id → expect_title；id 与文件名前缀对上（lit_fetch 落盘名就是 id）。"""
    return {r["id"]: r.get("expect_title", "") for r in (manifest_rows or []) if r.get("id")}


def run_dir(directory, rows=()):
    want = expect_map(rows)
    folder = Path(directory)
    files = sorted([p for p in folder.iterdir() if p.suffix.lower() in (".pdf", ".xml")]) \
        if folder.is_dir() else []
    print("原文体检：%s（%d 份）" % (directory, len(files)))
    if not files:
        print("  目录里没有 PDF/XML——先跑 --probe/--go，或把 --out 指到原文目录")
        return 1
    bad = 0
    for p in files:
        head = re.split(r"[_\.]", p.name)[0]
        r = audit_file(p, want.get(head, want.get(p.stem, "")))
        if r["state"] in ("文件坏", "疑似拿错", "标题对不上"):
            bad += 1
        print("  [%-12s] %4s页 %-52s %s" % (r["state"], r["pages"], p.name[:52], r["note"][:66]))
    print("结论：%d 份里 %d 份要人工处理。判读口径：只有“一致”才算原文到手；"
          "“需人工看首页”＝图像版，能看但不能逐字搜，引用前自己翻到那一页。" % (len(files), bad))
    return 1 if bad else 0
