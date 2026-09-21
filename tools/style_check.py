#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 腔体检：读一份草稿（正文节选 / 开题大纲 / PPT 大纲 / 讲稿），只报"一眼像模板写的"的地方。
用法：python tools/style_check.py 我的工作区/06-论文正文/讨论_初稿.md [--strict]
**只报问题，不替你改一个字**（改了就不是你的文字了）。判据是结构统计＋套话命中；
本工具不测 AIGC 率、不承诺"过检测""降率"——那条路不在本包的立场上（见结尾说明）。
"""
import argparse
import os
import re
import statistics
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 控制台默认 GBK，遇 ⚠ ↔ 等字符会直接崩；门禁与 AI 都以管道读输出）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
# 词表：本包自采的中文套话清单，按学校/导师意见自己增删即可（不必等新版）
LINKERS = ["综上所述", "总而言之", "总的来说", "首先", "其次", "再次", "最后", "与此同时", "值得注意的是",
           "需要指出的是", "不难发现", "由此可见", "进一步而言", "在此基础上", "一般而言", "众所周知", "随着", "在当下"]
FILLERS = ["赋能", "抓手", "闭环", "底层逻辑", "深度融合", "全方位", "多维度", "系统性", "高度契合",
           "有效提升", "有力支撑", "重要意义", "深远影响", "必然趋势"]
VAGUE = ["显著", "重要", "有效", "深入", "全面", "充分", "极大", "明显", "积极", "坚实"]
PARALLEL = [("不仅", "而且"), ("既", "又"), ("一方面", "另一方面"), ("无论", "都"), ("越来越", "越来越")]
SUBJECTS = ["名", "人", "学生", "大学生", "初中生", "高中生", "被试", "样本", "受访者", "问卷"]
SCALE_HINT = ["量表", "问卷", "信度", "效度", "α", "Cronbach"]
SITUATIONS = ["月", "大学", "中学", "学校", "城区", "农村", "某市", "年份"]
CJK, NUM, SENT = re.compile(r"[\u4e00-\u9fff]"), re.compile(r"\d+(?:\.\d+)?"), re.compile(r"[。！？；\n]")
PAGE_HEAD = re.compile(r"^#+\s*第\s*\d+\s*页[:：]?\s*")


def read_text(path):
    """草稿可能是 UTF-8 / UTF-8-sig / GBK（Windows 另存为常见），逐个试，不假装读到了。"""
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace"), "utf-8(有替换)"


def n_cjk(s):
    return len(CJK.findall(s))


def sentences(text):
    return [s for s in (c.strip().lstrip("#->* 0123456789.、 ") for c in SENT.split(text)) if n_cjk(s) >= 6]


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if n_cjk(p) >= 20]


def density(n, chars):
    return round(n * 1000.0 / max(chars, 1), 2)


def hits(text, words):
    """返回 [(词, 行号)]：行号是给学生定位用的，不是给机器看的。"""
    return [(w, i) for i, ln in enumerate(text.splitlines(), 1) for w in words if w in ln]


def linker_hits(text):
    """连接词只按**句首**算：真人也写"最后我们……"，但 AI 是拿它们当段落骨架。"""
    out = []
    for i, ln in enumerate(text.splitlines(), 1):
        for seg in re.split(SENT, ln):
            s = seg.strip().lstrip("#->* 0123456789.、")
            out += [(w, i) for w in LINKERS if s.startswith(w)]
    return out


def cv(vals):
    """变异系数＝标准差/均值。<0.25 意味着每段/每句一样长，读起来像模板。"""
    if len(vals) < 3 or not statistics.mean(vals):
        return None
    return round(statistics.pstdev(vals) / statistics.mean(vals), 3)


def parallel_triples(text):
    """找 A、B、C 式三连：顿号切出 ≥3 项、每项 2–8 字、长度彼此相近。"""
    found = []
    for i, ln in enumerate(text.splitlines(), 1):
        for seg in re.split(r"[。；;]", ln):
            items = [x.strip() for x in seg.split("、") if 2 <= len(x.strip()) <= 8]
            if len(items) >= 3 and max(len(x) for x in items[:4]) - min(len(x) for x in items[:4]) <= 2:
                found.append(("、".join(items[:4]), i))
    return found


def check_body(text):
    """正文与大纲共用的检查，返回四档清单。"""
    res, lines = [], text.splitlines()
    paras, sents = paragraphs(text), sentences(text)
    chars = n_cjk(text)
    lk, fl, fg = linker_hits(text), hits(text, FILLERS), hits(text, VAGUE)
    if fl:
        res.append(("缺项", "这些词是空转的，删掉不损失任何信息：%s（第 %s 行）"
                    % ("、".join(sorted({w for w, _ in fl})[:8]), "、".join(str(i) for i in sorted({i for _, i in fl})[:6]))))
    if chars >= 600 and density(len(lk), chars) >= 3:
        res.append(("风险", "句首套话连接词每千字 %s 个（%s）——它们只是脚手架，真人靠逻辑本身衔接；"
                    "每类留一处、其余删掉，删完重读一遍看还顺不顺" % (density(len(lk), chars), "、".join(sorted({w for w, _ in lk})[:6]))))
    elif len(lk) >= 3:
        res.append(("提示", "句首套话连接词 %d 处（%s），不必全删，但连着三段都用就是模板味"
                    % (len(lk), "、".join(sorted({w for w, _ in lk})[:5]))))
    for a, b in PARALLEL:
        n = sum(1 for ln in lines if a in ln and b in ln)
        if n >= 3:
            res.append(("风险", "%s 这种句式连用 %d 处——实际写作很少有人句句都这么搭"
                        % ("「%s」" % a if a == b else "「%s…%s…」" % (a, b), n)))
    tri = parallel_triples(text)
    if len(tri) >= 3:
        res.append(("提示", "三连排比 %d 处，例如「%s」（第 %d 行）。留一处最有力的，其余改成一句具体陈述"
                    % (len(tri), tri[0][0], tri[0][1])))
    pc, sc = cv([n_cjk(p) for p in paras]), cv([n_cjk(s) for s in sents])
    if pc is not None and pc < 0.25:
        res.append(("风险", "%d 个自然段字数几乎一样（变异系数 %s）——真人写作长短不齐，"
                    "把最长那段拆开、或把两段合并，节奏就活了" % (len(paras), pc)))
    if sc is not None and sc < 0.25:
        res.append(("风险", "%d 个句子长度几乎一样（变异系数 %s）——加一两个三五字的短句试试" % (len(sents), sc)))
    if len(paras) >= 6:
        heads = [p[:4] for p in paras]
        top = max(set(heads), key=heads.count)
        if heads.count(top) / len(heads) >= 0.4:
            res.append(("风险", "%d/%d 段都以「%s」开头——换两三段改成用数据、用例子、用上文结论起头"
                        % (heads.count(top), len(heads), top)))
    n_num = len(NUM.findall(text))
    if chars >= 600 and density(n_num, chars) < 1.0:
        res.append(("缺项", "整篇 %d 字里几乎没有数字（%d 个）——没有本研究的样本量、α、r、p、人数与时间，"
                    "读者看到的是一篇放到任何论文都成立的稿子" % (chars, n_num)))
    if not any(w in text for w in SUBJECTS) and not any(w in text for w in SCALE_HINT):
        res.append(("风险", "找不到被试与量表层面的具体词（如「多少名大学生」「某量表 α」）——"
                    "这类具体信息是「这是你做的研究」最硬的证据"))
    if not any(w in text for w in SITUATIONS):
        res.append(("提示", "没有时间点与场景（哪一年、哪所学校、什么施测条件）——这种细节只能你自己补"))
    loose = [(w, i) for w, i in fg if not NUM.search(lines[i - 1] or "")]
    if len(loose) >= 4:
        res.append(("提示", "「%s」这类评价词出现 %d 次且同句没有数字支撑——评价留给读者做"
                    % ("、".join(sorted({w for w, _ in loose})[:5]), len(loose))))
    return res


def check_outline(text):
    """汇报/PPT 大纲专属：一页三要点、每页字数齐、标题不带结论，是最常见的「一眼排的」。"""
    res, pages, cur = [], [], {"t": "（开头）", "n": 0, "c": 0}
    for ln in text.splitlines():
        if re.match(r"^#{1,4}\s", ln) or re.match(r"^\s*第\s*\d+\s*页", ln):
            pages.append(cur)
            cur = {"t": PAGE_HEAD.sub("", ln.strip().lstrip("# ")).strip()[:20], "n": 0, "c": 0}
        elif re.match(r"^\s*[-*·]\s", ln):
            cur["n"] += 1
            cur["c"] += n_cjk(ln)
    pages.append(cur)
    pages = [p for p in pages if p["n"]]
    if len(pages) >= 4:
        ns = [p["n"] for p in pages]
        if len(set(ns)) == 1 and ns[0] == 3:
            res.append(("风险", "%d 页全是三条要点——真人排汇报会有两条或四条的页，看内容决定，别凑三" % len(pages)))
        cs = [p["c"] for p in pages]
        if min(cs) and max(cs) - min(cs) < 0.2 * max(cs):
            res.append(("提示", "每页要点字数几乎相同（%d–%d 字）——按信息量分配，重点页可以多写几字" % (min(cs), max(cs))))
        nodata = [p["t"] for p in pages if not NUM.search(p["t"]) and not any(k in p["t"] for k in ("结果", "表", "图"))]
        if len(pages) >= 5 and len(nodata) >= len(pages) * 0.6:
            res.append(("风险", "多数页标题里没有数据也没有结论（如「%s」）——标题写成你这页最想说的那句话，"
                        "别写「研究背景」这种栏目名" % "、".join(nodata[:3])))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI 腔体检：只报像模板的地方，不代写、不测检测率")
    ap.add_argument("file", help="要体检的草稿（.md 或 .txt；PPT 大纲也走这条）")
    ap.add_argument("--strict", action="store_true", help="有缺项时退出码 1（给脚本与自检用）")
    a = ap.parse_args(argv)
    p = Path(a.file)
    if not p.is_absolute() and not p.is_file():
        p = ROOT / a.file
    if not p.is_file():
        print("读不到文件：%s\n先确认路径；不确定就把文件从文件夹拖进这个窗口。" % a.file)
        return 2
    text, enc = read_text(p)
    chars = n_cjk(text)
    if chars < 200:
        print("这份只有 %d 个汉字，太短，结构统计不成立（至少 200 字）。" % chars)
        return 2
    is_outline = bool(re.search(r"第\s*\d+\s*页", text)) or \
        (p.suffix.lower() == ".md" and bool(re.search(r"^#{1,4}\s.*页", text, re.M)))
    res = check_body(text) + (check_outline(text) if is_outline else [])
    res.sort(key=lambda x: {"缺项": 0, "风险": 2, "提示": 3}.get(x[0], 9))
    print("=" * 60)
    print("AI 腔体检：%s（%d 字 · %s · 编码 %s%s）"
          % (a.file, chars, "汇报/PPT 大纲" if is_outline else "正文体", enc, " · --strict" if a.strict else ""))
    print("=" * 60)
    if not res:
        print("没抓到套话与均一结构。仍要做的是第 2 步：通读一遍，凡是自己都想不起为什么这么写的句子，重写或删掉。")
    tier = ""
    for kind, msg in res:
        if kind != tier:
            tier = kind
            print("\n【%s】" % kind)
        print("  - " + msg)
    print("\n" + "-" * 60)
    print("改法按 workflows/writing-guide.md 第三节的四步走：逐句读 → 换成只有你写得出的具体内容 →"
          " 打乱一样长的句段 → AI 只做校对不生成。改完再跑一次本工具；再配合菜单第 25 项记一行写作留痕"
          "（过程证据比句式打扮有用）。")
    print("本工具只报问题，不替你改一个字——AI 替你改完，交上去的还是 AI 的话。")
    print("说明：本工具只看结构像不像模板，**不测 AIGC 率、不承诺任何检测结果**；用了 AI 就如实申报，"
          "见 templates/ai-usage-declaration.md。")
    return 1 if (a.strict and any(k == "缺项" for k, _ in res)) else 0


if __name__ == "__main__":
    sys.exit(main())
