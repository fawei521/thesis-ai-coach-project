#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""菜单处理器：开题与论文材料检查组（v1.85 起）。
被 menu.py 调用，本身不是入口，不要直接运行。
单独立一个模块的原因：menu_lit.py 已经 213/220 行，再加处理器会撞文件尺寸闸门
（见 tests/size_ratchet.py 与 DEVELOPMENT.md 的"菜单四件套"规矩）。"""
from pathlib import Path

from menu_io import ask_path, run


def t_readiness():
    print("\n【23/23】开题就绪度自检（读开题大纲 + 进度卡，只报问题、不替你写一个字）")
    print("  它会按 workflows/proposal-guide.md 的口径检查：八节写没写全、【】占位换干净没有、")
    print("  模型图在不在、进度卡和大纲的变量/假设/时间对不对得上、未成年人知情同意缺不缺、")
    print("  横断设计里有没有出现\"导致/证明\"这类强因果措辞、脚本名有没有混进正文，")
    print("  再给几条提示（样本量、量表题数与信度、文献年份、页数与每页要点数）。")
    f = ask_path("  你的开题大纲 .md（直接回车=我的工作区\\05-开题报告\\我的开题大纲.md）：",
                 must_exist=False) or "我的工作区/05-开题报告/我的开题大纲.md"
    if not Path(f).exists():
        print("  ✗ 没找到大纲：" + f)
        print("    先用第 21 项那套做法：把 templates\\opening-ppt-outline.md 拷成自己的大纲再填【】。")
        return
    p = ask_path("  你的进度卡（直接回车=我的工作区\\我的论文进度.md；输入 no=不读进度卡）：",
                 must_exist=False)
    args = [f]
    if p.strip().lower() in ("no", "n", "不"):
        args.append("--no-progress")
    elif p:
        args.append(p)
    run("proposal_readiness.py", args)
    print("\n  这份报告只说\"缺什么、哪里对不上\"，不替你补内容。")
    print("  补完再跑一遍；拿不准的按 communication-guide.md 带方案去问导师。")
