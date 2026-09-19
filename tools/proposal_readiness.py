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
# 真实控制台走 Windows 宽字符写入路径，不受影响，故沿用全套件的 isatty 判断口径。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DEF_OUTLINE = ROOT / "我的工作区" / "05-开题报告" / "我的开题大纲.md"
DEF_PROGRESS = ROOT / "我的工作区" / "我的论文进度.md"

# 开题报告八节（proposal-guide.md 第二节）：任一关键词命中即认为写了
SECTIONS = [("选题背景与意义", ["背景", "意义"]),
            ("国内外研究现状", ["文献", "综述", "研究现状"]),
            ("研究问题与假设", ["假设", "研究问题", "H1"]),
            ("研究方法与设计", ["方法", "设计", "程序"]),
            ("研究创新点", ["创新"]),
            ("研究进度安排", ["进度", "安排", "时间表"]),
            ("预期困难与对策", ["困难", "局限", "对策"]),
            ("参考文献", ["参考文献"])]
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


def parse_progress(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s*([^：:]+)[：:]\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1).strip(), m.group(2).strip()
        for zh, tag in FIELDS:
            if zh in key and tag not in out:
                filled = bool(val) and " / " not in val and "默认" not in val and val != "暂定"
                out[tag] = val if filled else ""
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
    for name, keys in SECTIONS:
        if not any(k in body for k in keys):
            want.append(("缺项", "八节里的「%s」没找到——按 proposal-guide 第二节补上这一节" % name))
    ph = [i + 1 for i, l in enumerate(outline.splitlines()) if "【" in l]
    if ph:
        want.append(("缺项", "还有 %d 行留着【】没换成你自己的内容（第 %s 行）——占位没换就交是硬伤"
                     % (len(ph), "、".join(map(str, ph[:12])) + ("…" if len(ph) > 12 else ""))))
    imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", outline) + re.findall(r"([^\s（）()]+\.png)", outline)
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
        # 只看"导致/证明"这类强因果词。题目里"…对…的影响"是本包 proposal-guide 第六节
        # 认可的标准句式，不能当违规抓——否则工具会和自己教的口径打架。
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
    # 页数优先按"第N页"这种真实分页标题数（模板自带一个 ## 标题页，混进来会多数一页）
    npg = len(re.findall(r"第\s*\d+\s*页", outline)) or len(pages)
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
          % (op.name, len(outline), "未读取" if not prog else pp.name))
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
