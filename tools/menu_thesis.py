#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""菜单处理器：开题与论文材料检查组（v1.85 起）。
被 menu.py 调用，本身不是入口，不要直接运行。
单独立一个模块的原因：menu_lit.py 已经 213/220 行，再加处理器会撞文件尺寸闸门
（见 tests/size_ratchet.py 与 DEVELOPMENT.md 的"菜单四件套"规矩）。"""
from pathlib import Path

from menu_io import ask_path, run


def t_readiness():
    print("\n【23/27】开题就绪度自检（读开题材料 + 进度卡，只报问题、不替你写一个字）")
    print("  它先分辨你交上来的是哪一种材料，两套口径分开核（拿错的口径判会假报缺项）：")
    print("  写着\"第N页\"→ 按 PPT 汇报八项核，加页数与每页要点数；")
    print("  写着\"一、~八、\"→ 按报告体八节**按标题定位**核，另核量表四要素、创新点有没有夸大、")
    print("  参考文献篇数与年份、数据处理写没写统计方法。")
    print("  两种材料都要过的：【】与下划线空位换干净没有、模型图在不在、进度卡和材料的")
    print("  变量/假设/时间对不对得上、未成年人知情同意缺不缺、横断设计里有没有\"导致/证明\"")
    print("  这类强因果措辞、脚本名有没有混进正文。")
    f = ask_path("  你的开题材料 .md（大纲或报告正文；直接回车=我的工作区\\05-开题报告\\我的开题大纲.md）：",
                 must_exist=False) or "我的工作区/05-开题报告/我的开题大纲.md"
    if not Path(f).exists():
        print("  ✗ 没找到开题材料：" + f)
        print("    PPT 那条路：把 templates\\opening-ppt-outline.md 拷成自己的大纲再填【】；")
        print("    报告正文那条路：按 templates\\proposal-template.md 写，写完同样能用这一项自查。")
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


def t_style():
    print("\n【24/27】AI 腔体检（只报「像模板写的」地方，不替你改一个字）")
    print("  它看四类：句首套话与空转词、段落句子一样长、三连排比，以及最要紧的一条——")
    print("  **通篇没有一个只有你写得出的具体信息**（样本量、α、人数、时间、地点）。")
    print("  汇报/PPT 大纲另看：是不是每页都恰好三条要点、每页字数齐不齐、标题有没有结论。")
    print("  ⚠ 它不测 AIGC 率，也不承诺任何检测结果；改文字是为了让论文回到你自己的口吻。")
    f = ask_path("  要体检的草稿 .md 或 .txt（正文节选、开题报告、PPT 大纲都行）：")
    if not f:
        print("  得先说读哪份稿子——把文件从文件夹拖进这个窗口就行。")
        return
    strict = input("  有缺项时让命令返回失败码（自检用）？回车=不用，输入 y=用：").strip().lower()
    run("style_check.py", [f] + (["--strict"] if strict in ("y", "yes", "是") else []))
    print("\n  结果只是提示，改不改、怎么改由你判断；改完再跑一次，看条数少了几条。")
    print("  改法看 workflows/writing-guide.md 第三节那四步。")


def t_log():
    print("\n【25/27】写作留痕（记一行「什么时候改了哪份稿子」，攒过程证据）")
    print("  它只往 我的工作区\\06-论文正文\\我的写作留痕.md 追加一行：时间、文件、汉字数、")
    print("  与上次的差、内容指纹、你写的一句备注。**你的草稿一个字节都不动。**")
    print("  用处：学校 AIGC 检测偶有误伤，那时能说明这篇论文是一步步写出来的，")
    print("  靠的是过程证据，不是把句子洗成不像 AI。")
    f = ask_path("  这一版草稿的文件（回车=取消）：")
    if not f:
        return
    note = input("  一句话备注（这次改了什么，回车=不写）：").strip()
    args = [f] + (["--note", note] if note else [])
    run("authorship_log.py", args)
    print("\n  想接着看已有留痕：菜单里再选一次然后直接回车；或在命令行跑")
    print("  python tools/authorship_log.py --show")
