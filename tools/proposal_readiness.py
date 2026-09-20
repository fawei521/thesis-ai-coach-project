#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开题就绪度自检（v1.85）——只报问题，不替你写一个字。

读你写的开题材料（默认 `我的工作区/05-开题报告/我的开题大纲.md`）与进度卡
（默认 `我的工作区/我的论文进度.md`），按 `workflows/proposal-guide.md` 的口径做**机械体检**，
分四档输出：
  缺项（评审必问、现在就没写）／矛盾（两份材料互相对不上）／
  风险（伦理与因果措辞这类会被当场抓的问题）／提示（能改会更好）。
本工具不修改任何文件、不联网、不生成任何正文——写什么仍然是你自己的事。

自 v1.94 起自动分辨你交进来的是哪一种材料，两套口径分开核（报告体那条路是待办 P8）：
  「第N页」＝PPT 汇报大纲 → proposal-guide 第四节八项，加页数与每页要点数；
  「一、~八、」＝开题报告正文 → 第二节八节**按标题定位**，另核量表四要素、创新点不夸大、
  参考文献篇数与年份、统计方法有没有写明。
`--for-card` 只把结论打印成一段可粘贴的 Markdown（贴进进度卡由 AI 动手，仍不代写内容）。

退出码：0 = 检查跑通（有没有问题看报告）；1 = 用法错误（材料不存在），或 --strict 下有缺项。
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

# 把本脚本所在目录加入 sys.path，确保 readiness 包可导入（与 tools/auto_stats.py 同一做法）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- 输出编码守卫：中文 Windows 控制台默认 GBK，管道/重定向时遇 ↔ χ² 会 UnicodeEncodeError ---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from readiness import common, outline, report  # noqa: E402

KIND_LABEL = {"ppt": "PPT 汇报大纲", "report": "开题报告正文（报告体）"}


def check(text, prog, base=None):
    """先判形态选口径，再把形态专属与跨形态共用的结果并起来；返回 (形态, 问题, 提示)。"""
    kind = common.detect_kind(text)
    kw, kg = (outline if kind == "ppt" else report).kind_checks(text)
    sw, sg = common.shared_checks(text, prog, base)
    return kind, kw + sw, sg + kg


def card_block(name, kind, want, got):
    """把结论排成进度卡「四之二」那一节要的样子：只有工具查出来的事实，没有替你写的内容。"""
    n = len(want)
    rows = ["## 四之二、开题就绪度自检（菜单第 23 项的结果，AI 帮贴、不代写内容）", "",
            "- 自检时间：%s　材料：%s（%s）" % (date.today().isoformat(), name, KIND_LABEL[kind]),
            "- 结论：%s（缺项/矛盾/风险 %d 条、提示 %d 条）"
            % ("可以拿去讲了" if not n else "还没到位", n, len(got))]
    for tag in ("缺项", "矛盾", "风险"):
        hits = [m for t, m in want if t == tag]
        if hits:
            rows.append("- %s %d 条：" % (tag, len(hits)))
            rows += ["  - " + m for m in hits[:6]]
    if got:
        rows.append("- 提示 %d 条：" % len(got))
        rows += ["  - " + g for g in got[:6]]
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description="开题就绪度自检：只报缺项/矛盾/风险，不代写")
    ap.add_argument("outline", nargs="?", default=str(common.DEF_OUTLINE),
                    help="开题材料路径（PPT 大纲或报告体正文，默认包内那份）")
    ap.add_argument("progress", nargs="?", default=str(common.DEF_PROGRESS), help="进度卡路径（默认包内那份）")
    ap.add_argument("--no-progress", action="store_true", help="只查大纲，不读进度卡")
    ap.add_argument("--strict", action="store_true", help="发现缺项/矛盾/风险时退出码 1")
    ap.add_argument("--for-card", action="store_true",
                    help="只打印一段可粘贴的 Markdown，供 AI 贴进进度卡「四之二」那一节")
    a = ap.parse_args()
    op, pp = Path(a.outline), Path(a.progress)
    if not op.is_file():
        print("找不到开题大纲：%s" % op)
        print("先用菜单第21项把 templates/opening-ppt-outline.md 拷成自己的大纲，再把【】换成内容。")
        return 1
    text = op.read_text(encoding="utf-8", errors="replace")
    prog = {} if a.no_progress or not pp.is_file() else common.parse_progress(
        pp.read_text(encoding="utf-8", errors="replace"))
    kind, want, got = check(text, prog, base=op.parent)
    n = len(want)
    if a.for_card:
        print(card_block(op.name, kind, want, got))
        return 1 if (a.strict and n) else 0
    print("=" * 58)
    print("开题就绪度自检　材料：%s（%d 字·%s）　进度卡：%s"
          % (op.name, len(text), KIND_LABEL[kind],
             "未读取" if a.no_progress else (pp.name if prog else "没有这份卡：用菜单第22项从模板生成")))
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
    print("\n结论：%s（缺项/矛盾/风险 %d 条、提示 %d 条）"
          % ("可以拿去讲了，把提示扫一遍" if not n else "还没到位，按上面补完再来一遍", n, len(got)))
    print("本工具只报问题、不代写；具体怎么改，最终和导师意见对齐。")
    print("要把这份结论留档：加 --for-card 打印可粘贴段，由 AI 贴进进度卡「四之二」那一节。")
    return 1 if (a.strict and n) else 0


if __name__ == "__main__":
    sys.exit(main())
