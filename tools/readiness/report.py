# -*- coding: utf-8 -*-
"""报告体（开题报告正文）口径：对齐 `templates/proposal-template.md`（待办 P8）。

与 PPT 汇报大纲的三点不同：
1. 八节**按标题定位**——正文里偶然出现"方法"两个字，不算写了研究方法这一节；
2. 有报告体专属的硬要求（量表四要素、创新点 1-3 个且不夸大、参考文献篇数与年份、统计方法要写明）；
3. 没有"页"的概念，页数与每页要点数那套规则在这份材料上不成立，所以不进本模块。
"""
import re

from .common import check_sections

SECTIONS_REPORT = [("选题背景与意义", ["背景", "意义"]),
                   ("国内外研究现状", ["文献", "综述", "研究现状"]),
                   ("研究问题与假设", ["假设", "研究问题", "H1"]),
                   ("研究方法与设计", ["方法", "设计", "程序"]),
                   ("研究创新点", ["创新"]),
                   ("研究进度安排", ["进度", "安排", "时间表"]),
                   ("预期困难与对策", ["困难", "局限", "对策"]),
                   ("参考文献", ["参考文献"])]
# 模板里"慎用首次/填补空白"那句措辞提示写在引用块里，学生抄下来时不该被抓（与讲稿行同一条规矩）
OVERCLAIM = ["首次", "首创", "填补空白", "填补了空白", "国际领先", "国内第一", "从未有人", "没有人研究过"]
HEAD = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")


def split_sections(text):
    """切成 [(节标题, 本节正文)]。节级取"命中八节关键词最多"的那一级——**不是最浅的一级**：
    模板开头那行 `## 本科毕业论文（设计）开题报告` 也含"设计"，按最浅判就把整份文档的节级
    定在第 2 级，八节全被判成缺项（第一版就这么错过，实测才抓到）。更深的子标题
    （如 `#### （一）研究对象`）留在本节正文里——不然"研究方法"会因为下一行就是子标题而被判成空节。
    一级都命中不了时返回空，调用方退回全文口径。"""
    lines = text.splitlines()
    heads = [(i, len(m.group(1)), m.group(2)) for i, m in
             ((i, HEAD.match(ln)) for i, ln in enumerate(lines)) if m]

    def cover(lv):
        return len({name for name, keys in SECTIONS_REPORT
                    if any(l == lv and any(k in t for k in keys) for _, l, t in heads)})

    best = max(range(1, 7), key=cover)
    if not cover(best):
        return []
    cuts = [(i, t) for i, l, t in heads if l == best]
    return [(t, "\n".join(lines[i + 1:(cuts[n + 1][0] if n + 1 < len(cuts) else len(lines))]))
            for n, (i, t) in enumerate(cuts)]


def locate(sections, keys):
    """按文档顺序找第一个标题命中 keys 的节；没找到返回 ("", "")。"""
    for t, b in sections:
        if any(k in t for k in keys):
            return t, b
    return "", ""


def subsection(body, keys):
    """从一节正文里再切出子节（`#### （四）数据处理` 到下一个同级标题之间）。
    统计方法只在"数据处理"这一小节里要求——拿整节研究方法去判，样本量段里那句
    "链式中介建议 300"就会把检查混过去（阴性验证实测到的漏报）。"""
    lines = body.splitlines()
    start = None
    for i, ln in enumerate(lines):
        m = HEAD.match(ln)
        if not m:
            continue
        if start is None and any(k in m.group(2) for k in keys):
            start = i + 1
        elif start is not None:
            return "\n".join(lines[start:i])
    return "\n".join(lines[start:]) if start is not None else ""


def kind_checks(text):
    """报告体特有的缺项与提示；跨形态都成立的在 common.shared_checks。"""
    secs = split_sections(text)
    body = text.replace("\n", " ")
    scan = "\n".join(t for t, _ in secs) if secs else body
    want = check_sections(SECTIONS_REPORT, "报告八节", "第二节", "节", scan)
    got = []
    for name, keys in SECTIONS_REPORT:          # 只量八节自己，"指导教师意见"这类签名栏空着是对的
        t, b = locate(secs, keys)
        if t and len(re.sub(r"\s", "", b)) < 20:
            want.append(("缺项", "「%s」只有标题没有内容（这一节的小节标题是：%s）——空着交上去老师一定会问" % (name, t)))
    # 模板留的下划线空位（__年__月、________）不带【】，只数【】会把没填的模板判成"写好了"
    blanks = sum(len(re.findall(r"_{2,}", ln)) for ln in text.splitlines())
    if blanks:
        want.append(("缺项", "还有 %d 处下划线空位没填（如 __年__月、________）——填不上就删掉那一行，别把空模板交上去" % blanks))
    _, m_body = locate(secs, ("方法", "设计", "程序"))
    if m_body:
        rows = [l for l in m_body.splitlines() if "量表" in l and re.match(r"^\s*\d+[\.、]", l)]
        weak = []
        for i, ln in enumerate(rows, 1):
            miss = [n for n, pat in (("题数", r"\d+\s*题"), ("维度", r"维度"), ("信度", r"α|信度|Cronbach"),
                                     ("出处", r"\d{4}|作者|主编")) if not re.search(pat, ln)]
            if miss:
                weak.append("第 %d 条缺%s" % (i, "、".join(miss)))
        if weak:
            got.append("研究工具里的量表信息不完整：%s——四要素（题数/维度/信度/出处）补齐，信度还要写出来自"
                       "哪个样本、哪一节哪张表；没有位置就先标 [需核实]（proposal-guide 第三节与 core/evidence-rigor.md）"
                       % "；".join(weak[:4]))
        probe = subsection(m_body, ("数据处理", "统计分析", "数据分析")) or m_body
        if not re.search(r"PROCESS|SPSS|JASP|AMOS|Bootstrap|Harman|结构方程|回归|相关|中介", probe):
            want.append(("缺项", "数据处理这一节没写统计方法与软件——要列明用什么做相关与中介（如 SPSS/JASP＋PROCESS "
                         "模型 6、Bootstrap 次数），只写公认软件（proposal-guide 第三节的硬口径）"))
        lack = [n for n, pat in (("功效分析依据（G*Power 或经验法则）", r"G\*?Power|功效|效应量"),
                                 ("中介样本量下限（≥200、链式≥300）", r"200|300"),
                                 ("无效卷上浮与剔除", r"无效|上浮|剔除|回收"))
                if not re.search(pat, m_body, re.I)]
        if len(lack) >= 2:
            got.append("样本量这块缺依据：%s——老师必问「样本多少、够吗」，三条都写才站得住（proposal-guide 第五节）"
                       % "、".join(lack))
    inn_title, inn_body = locate(secs, ("创新",))
    if inn_body and len(re.findall(r"^\s*(?:\d+[\.、]|[-*]\s)", inn_body, re.M)) > 3:
        got.append("%s 列了不止 3 条创新点——1-3 个扎实的即可，堆多了显得不诚实（proposal-guide 第三节）" % inn_title)
    over = sorted({w for w in OVERCLAIM if w in "\n".join(
        l for l in text.splitlines() if not l.strip().startswith(">"))})
    if over:
        want.append(("风险", "出现「%s」这类强断言。评审会接着问「别人真的没做过吗」——按 core/evidence-rigor.md 的"
                     "否定结论四步先给出检索依据（检索词、数据库、时间范围、命中数），拿不出就改成「较少有研究探讨」"
                     "「有待进一步检验」" % "、".join(over)))
    _, ref_body = locate(secs, ("参考文献",))
    refs = len(re.findall(r"^\s*\[\s*\d+\s*\]", ref_body, re.M)) or len(re.findall(r"\[[A-Z]{1,2}/?[A-Z]{0,2}\]", ref_body))
    if refs:
        if refs < 30:
            got.append("参考文献现在 %d 条——模板口径是近 5 年为主、建议 30 篇以上（proposal-guide 第六节）" % refs)
        ry = [int(y) for y in re.findall(r"\b(20[0-2]\d)\b", ref_body)]
        if ry and sum(1 for y in ry if y >= 2021) * 2 < len(ry):
            got.append("参考文献里近五年（2021 及以后）偏少：%d 处中只有 %d 处——综述以近五年为主（第六节）"
                       % (len(ry), sum(1 for y in ry if y >= 2021)))
    else:
        want.append(("缺项", "参考文献一节还没放条目——按 GB/T 7714-2015 格式列（tools/reference_formatter.py 可以把"
                     "你手抄的格式理顺），近 5 年为主、建议 30 篇以上"))
    if not re.search(r"长直线|注意力题|作答时长|低变异|高缺失", text):
        got.append("没看到无效问卷的剔除标准（作答时长过短、长直线、个体内低变异、高缺失、注意力题答错）"
                   "——标准要在收数前定，模板四（三）有这一段")
    return want, got
