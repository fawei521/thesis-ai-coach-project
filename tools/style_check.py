#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 腔体检：读一份草稿（正文节选 / 开题大纲 / PPT 大纲 / 讲稿），只报"一眼像模板写的"的地方。
用法：python tools/style_check.py 我的工作区/06-论文正文/讨论_初稿.md [--strict]
**只报问题，不替你改一个字**（改了就不是你的文字了）。
判据有两个来源：**词条与句式来自 `core/academic-style.md` 第二节那张禁则表**——往表里加一行，
本工具立刻开始抓它；从表里删一个词，立刻不抓（按学校或导师的用词偏好自己改表，不必改代码、不必等新版本）。
结构统计留在本文件里（句段是否一样长、单段超载、排比、数字密度、大纲均一）——那是算法不是词表。
本工具不测 AIGC 率、不承诺"过检测""降率"——那条路不在本包的立场上（见结尾说明）。
"""
import argparse
import re
import statistics
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 控制台默认 GBK，遇 ⚠ ↔ 等字符会直接崩；门禁与 AI 都以管道读输出）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "core" / "academic-style.md"          # 判据表的家：词表与规范同源，不许有两套
TIERS, USES = ("缺项", "风险", "提示"), ("包含", "句首", "正则", "配对", "须有")
OVER_P = 200   # 单段超载线（按汉字数）；线与理由同写在 core/academic-style.md 第三节，case_32 盯这三处不许漂
VAGUE = ["显著", "重要", "有效", "深入", "全面", "充分", "极大", "明显", "积极", "坚实"]  # 评价词与数字同现的判断固定在代码里，见 academic-style 第二节末
CJK, NUM, SENT = re.compile(r"[\u4e00-\u9fff]"), re.compile(r"\d+(?:\.\d+)?"), re.compile(r"[。！？；\n]")
PAGE_HEAD = re.compile(r"^#+\s*第\s*\d+\s*页[:：]?\s*")
LISTISH = re.compile(r"^\s*([-*·]|\d+[.、]|#{1,4}\s)")   # 条目行与标题行：它们堆成的块不叫"一段"


def read_text(path):
    """草稿可能是 UTF-8 / UTF-8-sig / GBK（Windows 另存为常见），逐个试，不假装读到了。"""
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace"), "utf-8(有替换)"


def load_bans(path=None):
    """解析禁则表。**读不出东西就返回错误，不返回空表**——拿着空词表跑完再说"没抓到套话"，
    是尺子空转里最坏的一种：它看起来一切正常。
    path 在调用时才取 SPEC，回归可以把 SPEC 指到一份改坏的副本上验"坏了会不会报错"。"""
    path = path or SPEC
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, ["读不到判据表：%s（本工具的词表全部来自这份文件，缺它就没有判据）" % path]
    rows, bad = [], []
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|"):
            continue
        c = [x.strip() for x in s.strip("|").split("|")]
        if len(c) != 5 or c[0] not in TIERS:
            continue
        tier, cat, hit, use, why = c
        if use not in USES:
            bad.append("「%s」那行的用法写成「%s」，只能是：%s" % (cat, use, "／".join(USES)))
            continue
        row = {"tier": tier, "cat": cat, "use": use, "why": why}
        if use == "正则":
            try:
                row["pat"] = re.compile(hit)
            except re.error as e:
                bad.append("「%s」那行的正则编译不了：%s" % (cat, e))
                continue
        elif use == "配对":
            row["pairs"] = [(x.split("…")[0], x.split("…")[1]) for x in hit.split(",") if "…" in x]
            if not row["pairs"]:
                bad.append("「%s」那行的配对写成「%s」，要写成 前项…后项" % (cat, hit))
                continue
        else:
            row["terms"] = [t for t in hit.split(",") if t]
            if not row["terms"]:
                bad.append("「%s」那行的命中列是空的" % cat)
                continue
        rows.append(row)
    if bad:
        return None, bad
    if not rows:
        return None, ["判据表里一条都没解析到——检查 %s 第二节那张表是不是被改坏了" % "core/academic-style.md"]
    return rows, []


def n_cjk(s):
    return len(CJK.findall(s))


def sentences(text):
    return [s for s in (c.strip().lstrip("#->* 0123456789.、 ") for c in SENT.split(text)) if n_cjk(s) >= 6]


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if n_cjk(p) >= 20]


def density(n, chars):
    return round(n * 1000.0 / max(chars, 1), 2)


def locs(pairs):
    """把 (词, 行号) 收成两句人能读的话：命中了哪些词、分别在哪几行。行号给学生定位用。"""
    return ("「%s」" % "、".join(sorted({w for w, _ in pairs})[:6]),
            "第 %s 行" % "、".join(str(i) for i in sorted({i for _, i in pairs})[:6]))


def linker_hits(text, words):
    """连接词只按**句首**算：真人也写"最后我们……"，但 AI 是拿它们当段落骨架。"""
    out = []
    for i, ln in enumerate(text.splitlines(), 1):
        for seg in re.split(SENT, ln):
            s = seg.strip().lstrip("#->* 0123456789.、")
            out += [(w, i) for w in words if s.startswith(w)]
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


def ban_hits(rows, text):
    """按表逐行判，返回 [(档, 文案)]。表里加一行＝这里多一条判据，代码不用动。
    句首类不在这里——它是聚合判据（看每千字密度，不看单次命中），单独走 check_body。"""
    lines, out = text.splitlines(), []
    for r in rows:
        if r["use"] == "句首":
            continue
        if r["use"] == "包含":
            hs = [(t, i) for i, ln in enumerate(lines, 1) for t in r["terms"] if t in ln]
            need = 2 if r["tier"] == "提示" else 1        # 提示档管"别满篇都是"，一次不算满篇
            if len(hs) >= need:
                w, at = locs(hs)
                out.append((r["tier"], "%s：%s 出现 %d 次（%s）——%s" % (r["cat"], w, len(hs), at, r["why"])))
        elif r["use"] == "正则":
            hs = [(m.group(0), i) for i, ln in enumerate(lines, 1) for m in r["pat"].finditer(ln)]
            need = 2 if r["tier"] == "提示" else 1        # v1.108 起正则按档计：一处设问、一处「对 X 进行分析」不是病，满篇才是
            if len(hs) >= need:                           # 缺项／风险档仍是一次即报（写法错误不存在"用多了才有问题"）
                out.append((r["tier"], "%s：%s（第 %s 行）——%s"
                            % (r["cat"], "、".join(sorted({h for h, _ in hs})[:4]),
                               "、".join(str(i) for i in sorted({i for _, i in hs})[:6]), r["why"])))
        elif r["use"] == "配对":
            n = sum(1 for ln in lines for a, b in r["pairs"] if a in ln and b in ln)
            if n >= 3:
                out.append((r["tier"], "%s这类句式连用 %d 处——%s"
                            % ("、".join("%s…%s" % p for p in r["pairs"][:3]), n, r["why"])))
        elif r["use"] == "须有":
            if not any(t in text for t in r["terms"]):
                out.append((r["tier"], "%s这一类词一个都没有（要找的是：%s）——%s"
                            % (r["cat"], "、".join(r["terms"][:8]), r["why"])))
    return out


def check_body(text, rows, outline=False):
    """正文与大纲共用的检查：表里的词条 ＋ 固定几项结构统计。"""
    res, lines = [], text.splitlines()
    paras, sents = paragraphs(text), sentences(text)
    chars = n_cjk(text)
    res.extend(ban_hits(rows, text))
    lk = linker_hits(text, [t for r in rows if r["use"] == "句首" for t in r["terms"]])
    if chars >= 600 and density(len(lk), chars) >= 3:
        res.append(("风险", "句首套话连接词每千字 %s 个（%s）——它们只是脚手架，真人靠逻辑本身衔接；"
                    "每类留一处、其余删掉，删完重读一遍看还顺不顺" % (density(len(lk), chars), locs(lk)[0])))
    elif len(lk) >= 3:
        res.append(("提示", "句首套话连接词 %d 处（%s），不必全删，但连着三段都用就是模板味"
                    % (len(lk), locs(lk)[0])))
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
    heavy = sorted([(n_cjk(p), sum(1 for x in SENT.split(p) if n_cjk(x) >= 6),
                     next((i for i, ln in enumerate(lines, 1) if ln.strip().startswith(p.strip()[:12])), 0))
                    for p in paras if n_cjk(p) >= OVER_P
                    and sum(1 for x in p.splitlines() if LISTISH.match(x)) * 2 < len(p.splitlines())], reverse=True)
    if heavy:
        res.append(("提示", "单段超 %d 字的 %d 段，最长 %d 字 %d 句（起于第 %d 行）——一段只装一个主张，"
                    "逐段找第二段主张从哪句开始；该不该拆你判、要拆你下笔，本工具不动你的字"
                    "（线为什么画在 %d、为什么不判红见 core/academic-style.md 第三节）"
                    % (OVER_P, len(heavy), heavy[0][0], heavy[0][1], heavy[0][2], OVER_P)))
    n_num = len(NUM.findall(text))
    if chars >= 600 and density(n_num, chars) < 1.0:
        res.append(("缺项", "整篇 %d 字里几乎没有数字（%d 个）——没有本研究的样本量、α、r、p、人数与时间，"
                    "读者看到的是一篇放到任何论文都成立的稿子" % (chars, n_num)))
    loose = [(w, i) for i, ln in enumerate(lines, 1) for w in VAGUE if w in ln and not NUM.search(ln)]
    if len(loose) >= 4:
        res.append(("提示", "「%s」这类评价词出现 %d 次且同句没有数字支撑——评价留给读者做"
                    % ("、".join(sorted({w for w, _ in loose})[:5]), len(loose))))
    content = [ln for ln in lines if n_cjk(ln) >= 6]
    bullets = [ln for ln in content if re.match(r"^\s*([-*·]|\d+[.、])\s", ln)]
    if not outline and len(content) >= 12 and len(bullets) * 2 >= len(content):
        res.append(("提示", "%d/%d 行是条目号或项目符号——正文靠段落推进，条目只该出现在大纲里；"
                    "把要点写成完整的句子" % (len(bullets), len(content))))
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
    rows, bad = load_bans()
    if rows is None:
        print("判据表读不出来，本工具不跑：\n  - " + "\n  - ".join(bad))
        print("判据全在 core/academic-style.md 第二节那张表里；表坏了就不检查，**不假装检查过了**。")
        return 2
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
    res = check_body(text, rows, is_outline) + (check_outline(text) if is_outline else [])
    res.sort(key=lambda x: {"缺项": 0, "风险": 2, "提示": 3}.get(x[0], 9))
    print("=" * 60)
    print("AI 腔体检：%s（%d 字 · %s · 编码 %s · 判据 %d 条%s）"
          % (a.file, chars, "汇报/PPT 大纲" if is_outline else "正文体", enc, len(rows),
             " · --strict" if a.strict else ""))
    print("=" * 60)
    if not res:
        print("没抓到套话与均一结构。仍要做的是通读一遍，凡是自己都想不起为什么这么写的句子，重写或删掉。")
    tier = ""
    for kind, msg in res:
        if kind != tier:
            tier = kind
            print("\n【%s】" % kind)
        print("  - " + msg)
    print("\n" + "-" * 60)
    print("这份稿子是谁写的，走两条不同的工序：**学生自己的稿子**按 workflows/writing-guide.md 第三节那四步自己改；"
          "**AI 起草的稿子**按 core/academic-style.md 第四节那四步（先列具体信息再落笔、缺的标 [待你补] 不要编）。")
    print("词条判据就在 core/academic-style.md 第二节的表里，导师说某个词不许用就加一行，说某个词是本文术语就删掉它。")
    print("本工具只报问题，不替你改一个字——AI 替你改完，交上去的还是 AI 的话。")
    print("说明：本工具只看结构像不像模板、措辞合不合学术语体，**不测 AIGC 率、不承诺任何检测结果**；"
          "用了 AI 就如实申报，见 templates/ai-usage-declaration.md。")
    return 1 if (a.strict and any(k == "缺项" for k, _ in res)) else 0


if __name__ == "__main__":
    sys.exit(main())
