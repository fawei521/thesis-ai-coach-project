#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开题就绪度自检（v1.85）——只报问题，不替你写一个字。

读两份东西：开题大纲（默认 `我的工作区/05-开题报告/我的开题大纲.md`）
与进度卡（默认 `我的工作区/我的论文进度.md`），按 `workflows/proposal-guide.md`
第二、四、五、六节的口径做**机械体检**，分四档输出：
  缺项（评审必问、现在就没写）／矛盾（两份材料互相对不上）／
  风险（伦理与因果措辞这类会被当场抓的问题）／提示（能改会更好）。
本工具不修改任何文件、不联网、不生成任何正文——写什么仍然是你自己的事。

退出码：0 = 检查跑通（有没有问题看报告）；1 = 用法错误（大纲不存在），或 --strict 下有缺项。
"""
import argparse
import re
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，stdout 被管道捕获时遇到 ↔ χ² 这类字符会 UnicodeEncodeError；
# 真控制台编码本来就是 UTF-8（实测 CREATE_NEW_CONSOLE 下 isatty()=True 且 encoding=utf-8），
# 而无条件 reconfigure 在它是无操作，所以判断不再依赖 isatty()——NUL 设备上 isatty() 也为真。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DEF_OUTLINE = ROOT / "我的工作区" / "05-开题报告" / "我的开题大纲.md"
DEF_PROGRESS = ROOT / "我的工作区" / "我的论文进度.md"

# 报告体八节（proposal-guide.md 第二节）：任一关键词命中即认为写了
SECTIONS_REPORT = [("选题背景与意义", ["背景", "意义"]),
                   ("国内外研究现状", ["文献", "综述", "研究现状"]),
                   ("研究问题与假设", ["假设", "研究问题", "H1"]),
                   ("研究方法与设计", ["方法", "设计", "程序"]),
                   ("研究创新点", ["创新"]),
                   ("研究进度安排", ["进度", "安排", "时间表"]),
                   ("预期困难与对策", ["困难", "局限", "对策"]),
                   ("参考文献", ["参考文献"])]
# PPT 汇报八项（proposal-guide.md 第四节）：与报告体**不是一套**，
# 拿报告口径去判 PPT 大纲会假报"参考文献没找到"（v1.86 真人走查 S4）。
SECTIONS_PPT = [("封面（题目/姓名/导师/日期）", ["副标题", "汇报人", "指导教师"]),
                ("选题背景", ["背景"]),
                ("文献综述与研究空白", ["综述", "空白"]),
                ("研究模型与假设", ["模型", "假设"]),
                ("研究方法（对象/量表/分析）", ["方法", "对象", "量表", "分析"]),
                ("创新点", ["创新"]),
                ("进度安排", ["进度"]),
                ("致谢/请老师指正", ["指正", "致谢", "谢谢"])]
# 进度卡字段 → 内部标签；值里留着" / "说明是模板选项、按未填处理
FIELDS = [("论文题目", "TITLE"), ("研究类型", "TYPE"), ("自变量", "X"), ("因变量", "Y"),
          ("中介变量 M1", "M1"), ("中介变量 M2", "M2"), ("调节变量", "W"),
          ("研究假设", "HYP"), ("计划答辩时间", "DEF")]
VARNAME = {"X": "自变量", "Y": "因变量", "M1": "中介变量1", "M2": "中介变量2", "W": "调节变量"}
CAUSAL = ["导致", "证明了", "引起", "决定了"]
CROSS = ["横断", "一次性施测", "同一时间", "横截面"]
MINOR = ["青少年", "未成年", "初中生", "高中生", "中学生", "小学生"]
CONSENT = ["知情同意", "监护人", "家长同意", "父母同意", "自愿", "匿名"]
TOOLISH = re.compile(r"(tools/\w+\.py|\w+\.py\b|auto_stats|outline_to_ppt|sample_size|paper_search"
                     r"|menu\.py|启动工具箱|--[a-z][a-z-]+)")


def clean_value(val):
    """把"- 字段：值"里的值净化成可比对的**核心词**：真人会写 `非自杀性自伤（NSSI）`、`暂无，待定`、
    `**自然**（走查时选的）`，整串拿去和大纲做子串比对必然假报"两边对不上"（v1.86 真人走查 S2）。"""
    v = val.strip().replace("**", "").replace("`", "").lstrip("*").strip()
    v = re.split(r"[（(—、；;，]| {2,}", v, maxsplit=1)[0].strip()
    if not v or v in ("无", "暂无", "暂定", "待定", "N/A", "na", "-") or " / " in val or "默认" in val:
        return ""
    return v


def parse_progress(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s*([^：:]+)[：:]\s*(.*)$", line)
        if not m:
            # 假设常写成缩进子条目（"- 研究假设：" 下面 "- H1 …"）：冒号后为空也要认成"已列条目"，
            # 否则会漏报"假设没写进大纲"（v1.86 真人走查 S3）。
            if "HYP" in out and not out["HYP"] and re.match(r"^\s+[-*]\s*H\d+\b", line):
                out["HYP"] = "已列条目"
            continue
        key, val = m.group(1).strip(), m.group(2).strip()
        for zh, tag in FIELDS:
            if zh in key and tag not in out:
                out[tag] = clean_value(val)
    return out


def parse_pages(text):
    """按标题切页；`> 讲稿：` 行与列表行分开算。"""
    pages, cur = [], {"t": "（封面/开头）", "lines": []}
    for ln in text.splitlines():
        if re.match(r"^#{1,4}\s", ln):
            pages.append(cur)
            cur = {"t": ln.lstrip("#").strip(), "lines": []}
        else:
            cur["lines"].append(ln)
    pages.append(cur)
    return pages


def check(outline, prog, base=None):
    want, got = [], []
    base = Path(base) if base else DEF_OUTLINE.parent   # 图片按"大纲自己所在目录"解析
    body = outline.replace("\n", " ")
    # 输入是 PPT 大纲还是报告正文，两套口径分开核（v1.86 真人走查 S4：以前拿报告八节判 PPT，
    # 对着一份本来就不含参考文献页的汇报大纲报"参考文献没找到"）
    ppt = bool(re.search(r"第\s*\d+\s*页", outline))
    secs, 口径, 量词 = (SECTIONS_PPT, "第四节", "项") if ppt else (SECTIONS_REPORT, "第二节", "节")
    for name, keys in secs:
        if not any(k in body for k in keys):
            want.append(("缺项", "%s里的「%s」没找到——按 proposal-guide %s补上这一%s"
                         % ("汇报八项" if ppt else "报告八节", name, 口径, 量词)))
    lines = outline.splitlines()
    ph = sum(l.count("【") for l in lines)
    _mk = [i + 1 for i, l in enumerate(lines) if "[需核实]" in l]
    if ph:
        tally, cur = {}, "（封面/开头）"
        for ln in lines:                       # 按页分组，零基础同学才对得上是哪一页要补（S6）
            if re.match(r"^#{1,4}\s", ln):
                cur = ln.lstrip("#").strip()[:14]
            if "【" in ln:
                tally[cur] = tally.get(cur, 0) + ln.count("【")
        want.append(("缺项", "还有 %d 处【】没换成你自己的内容，按页看：%s——占位没换就交是硬伤"
                     % (ph, "、".join("%s %d 处" % (k, v) for k, v in list(tally.items())[:8]))))
    if _mk:
        want.append(("缺项", "第 %s 行还留着 [需核实]——回原文补上「逐字原文＋第几节/哪张表」，补不上就删掉这条（core/evidence-rigor.md）" % "、".join(str(i) for i in _mk[:6])))
    imgs = list(dict.fromkeys(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", outline)
                            + re.findall(r"([^\s（）()]+\.png)", outline)))
    if "模型" in body and not imgs:
        want.append(("缺项", "写了研究模型却没有模型图——假设与路径要靠图讲清（菜单第6项可生成）"))
    for im in imgs:
        if not any((d / im).is_file() for d in (base, ROOT, ROOT / "我的工作区")):
            want.append(("缺项", "大纲里引的图「%s」找不到，排成 PPT 会是空框" % im))
    for tag, zh in (("TITLE", "论文题目"), ("TYPE", "研究类型")):
        if prog and not prog.get(tag):
            want.append(("缺项", "进度卡的「%s」还没填——换 AI 接不上，也没法和大纲对账" % zh))
    for tag in ("X", "Y", "M1", "M2", "W"):
        v = (prog or {}).get(tag, "")
        if v and v not in outline:
            want.append(("矛盾", "进度卡里的 %s=%s 在大纲中找不到，两边口径不一致（补进大纲或改进度卡，别留两套）"
                         % (VARNAME[tag], v)))
    if (prog or {}).get("DEF") and not re.search(r"\d{1,2}\s*月", body):
        want.append(("矛盾", "进度卡写了计划答辩时间（%s），大纲的进度安排里没有对应月份" % prog["DEF"]))
    if (prog or {}).get("HYP") and "H1" not in outline.replace("h1", "H1"):
        want.append(("矛盾", "进度卡写了研究假设，大纲里却没有 H1/H2 编号——假设要一条条编号才能和模型图的箭头对上"))
    if any(w in body for w in MINOR) and not any(c in body for c in CONSENT):
        want.append(("风险", "对象涉及未成年人却没写知情同意/监护人同意——伦理硬伤，见 psychology/ethics.md"))
    if any(c in body for c in CROSS):
        # 只抓"导致/证明"这类强因果词；"…对…的影响"是 proposal-guide 第六节认可的标准句式，抓它=工具和自己教的口径打架
        hits = sorted({w for w in CAUSAL if w in body})
        if hits:
            want.append(("风险", "设计是横断（一次施测），却出现强因果措辞：%s。评审常问「横断能说明因果吗」，"
                         "建议改说“预测/关联”并承认局限（proposal-guide 第五节）" % "、".join(hits)))
    bad = sorted({m.group(0) for ln in outline.splitlines() if not ln.strip().startswith(">")
                  for m in [TOOLISH.search(ln)] if m})
    if bad:
        want.append(("风险", "正文里混进了工具脚本名/开关：%s。正式开题文本只写 SPSS/JASP/PROCESS/G*Power 等"
                     "公认软件，脚本只是你自己预览核对用的（proposal-guide 第三节的硬口径）" % "、".join(bad[:8])))
    if not re.search(r"\d{3,}\s*(份|人)|N\s*=|样本量\s*[:：]?\s*\d{3}", body):
        got.append("没看到样本量数字（份/人/N=）——用菜单第8项估算最小 N、叠加无效卷冗余，把依据写进方法")
    if "量表" in body and not re.search(r"\d+\s*题|信度|α|Cronbach", body):
        got.append("写了量表但没写题数/信度——老师会问“这个量表信效度怎么样”，每个量表补题数、维度、α、出处")
    yrs = [int(y) for y in re.findall(r"\b(20[0-2]\d)\b", outline)]
    if yrs and sum(1 for y in yrs if y >= 2021) * 2 < len(yrs):
        got.append("出现的年份里近五年（2021 及以后）偏少：%d 处中只有 %d 处——综述以近五年为主"
                   % (len(yrs), sum(1 for y in yrs if y >= 2021)))
    pages = [p for p in parse_pages(outline) if p["lines"] or "页" in p["t"]]
    npg = len(re.findall(r"第\s*\d+\s*页", outline)) or len(pages)   # 优先按"第N页"数：模板自带的 ## 标题页混进来会多数一页
    if npg < 8 or npg > 12:
        got.append("现在 %d 页，口径是 8-12 页（proposal-guide 第四节）——多了念不完，少了讲不清" % npg)
    fat = [p["t"] for p in pages
           if len([l for l in p["lines"] if l.strip().startswith(("-", "|"))]) > 7
           or any(len(l) > 46 for l in p["lines"] if l.strip().startswith("-"))]
    if fat:
        got.append("这几页要点偏多偏长（每页一个核心信息、字少图多）：%s" % "、".join(fat[:6]))
    return want, got


def main():
    ap = argparse.ArgumentParser(description="开题就绪度自检：只报缺项/矛盾/风险，不代写")
    ap.add_argument("outline", nargs="?", default=str(DEF_OUTLINE), help="开题大纲路径（默认包内那份）")
    ap.add_argument("progress", nargs="?", default=str(DEF_PROGRESS), help="进度卡路径（默认包内那份）")
    ap.add_argument("--no-progress", action="store_true", help="只查大纲，不读进度卡")
    ap.add_argument("--strict", action="store_true", help="发现缺项/矛盾/风险时退出码 1")
    a = ap.parse_args()
    op, pp = Path(a.outline), Path(a.progress)
    if not op.is_file():
        print("找不到开题大纲：%s" % op)
        print("先用菜单第21项把 templates/opening-ppt-outline.md 拷成自己的大纲，再把【】换成内容。")
        return 1
    outline = op.read_text(encoding="utf-8", errors="replace")
    prog = {} if a.no_progress or not pp.is_file() else parse_progress(pp.read_text(encoding="utf-8", errors="replace"))
    want, got = check(outline, prog, base=op.parent)
    print("=" * 58)
    print("开题就绪度自检　大纲：%s（%d 字）　进度卡：%s"
          % (op.name, len(outline), "未读取" if a.no_progress else (pp.name if prog else "没有这份卡：用菜单第22项从模板生成")))
    print("=" * 58)
    for tag, sub in (("缺项", "先补这些，否则老师一定会问"), ("矛盾", "两份材料对不上"),
                     ("风险", "会被当场抓的硬伤")):
        rows = [m for t, m in want if t == tag]
        if rows:
            print("\n[%s] %s" % (tag, sub))
            for m in rows:
                print("  - " + m)
    if got:
        print("\n[提示] 不改也能交，改了更稳")
        for g in got:
            print("  - " + g)
    n = len(want)
    print("\n结论：%s（缺项/矛盾/风险 %d 条、提示 %d 条）"
          % ("可以拿去讲了，把提示扫一遍" if not n else "还没到位，按上面补完再来一遍", n, len(got)))
    print("本工具只报问题、不代写；具体怎么改，最终和导师意见对齐。")
    return 1 if (a.strict and n) else 0


if __name__ == "__main__":
    sys.exit(main())
