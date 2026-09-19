#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""菜单处理器 · 文献与产出组：检索、文献整理、重点卡片、模型图、演示数据、样本量、网页预览、
参考文献格式化、大纲排 PPT、工作区补齐。"""

from pathlib import Path

from menu_io import ask_path, run

# --- 输出编码守卫：管道/重定向时强制 UTF-8（项目门禁统一要求，见 tests/full_e2e.py 全部脚本有编码守卫）---
import sys as _sys
if hasattr(_sys.stdout, "reconfigure") and not _sys.stdout.isatty():
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def t_search():
    print("\n【4/22】检索英文学术文献（需要联网，免费，不用账号）")
    print("  建议每个概念给 2-4 个同义/近义词，用分号 ; 隔开（概念内 OR、概念间 AND）。")
    print("  例：AI dependence;AI attachment;chatbot reliance")
    kw = input("  输入英文检索词（多个近义词用 ; 隔开；至少给一个）：").strip()
    if not kw:
        print("  检索词为空，已取消。")
        return
    tgt = input("  去重后想要多少篇候选池？直接回车=每词每源约15篇；想凑约90篇就输入 90：").strip()
    out = input("  结果保存成什么文件名？直接回车默认放进 我的工作区\\01-文献PDF\\英文文献.csv：").strip()
    # 支持分号/换行多词：交给 paper_search 的 --queries；同时双源检索
    args = ["--queries", kw, "--source", "all"]
    if tgt.isdigit() and int(tgt) > 0:
        args += ["--min", tgt]
    else:
        args += ["--limit", "15"]
    if out:
        args += ["--output", out]
    else:
        args += ["--output", "我的工作区/01-文献PDF/英文文献.csv"]
    run("paper_search.py", args)


def t_lit():
    print("\n【5/22】文献去重与分类")
    print("  可拖入的有两种：① 每行一篇的 txt；② 第 4 项检索导出的标准 CSV（含 标题/作者 表头）。")
    print("  也可以直接拖知网导出的题录 txt。")
    f = ask_path("  把文献文件拖进来，回车：")
    if not f:
        return
    run("literature_organizer.py", [f])


def t_cards():
    print("\n【10/22】生成重点文献卡片网页（手机友好，挑精读用）")
    print("  吃第 4 项检索导出的 CSV、第 5 项的整理表（可多个，UTF-8/GBK 都行），")
    print("  自动去重、按 精读标记/被引/近年/相关度 选出重点，生成单个 HTML。")
    raw = input("  把一个或多个文献 CSV/整理表拖进来（多个用分号 ; 隔开），回车：").strip()
    if not raw:
        print("  没有输入文件，已取消。")
        return
    paths = [p.strip().strip('"').strip("'") for p in raw.replace("\n", ";").split(";") if p.strip()]
    focus = input("  你的核心变量/主题词（逗号分隔，命中的重点加权；直接回车跳过）：").strip()
    out = input("  网页存成什么文件名？直接回车默认 我的工作区\\04-网页\\重点文献卡片.html：").strip()
    args = paths
    if focus:
        args += ["--focus", focus]
    if out:
        args += ["--output", out]
    else:
        args += ["--output", "我的工作区/04-网页/重点文献卡片.html"]
    run("literature_cards.py", args)


def t_chart():
    print("\n【6/22】生成研究模型图")
    print("  链式中介示例：AI依赖,孤独感,反刍,NSSI（4个，2个中介）")
    print("  简单中介示例：AI依赖,孤独感,NSSI（3个，1个中介）；直接效应示例：AI依赖,NSSI（2个）")
    vars_ = input("  输入变量名（逗号分隔）：").strip()
    if not vars_:
        print("  未输入，已取消。")
        return
    coefs = input("  输入对应路径系数（逗号分隔；还没结果就直接回车，先用0占位出框架图）：").strip() or ""
    out = input("  图片保存成什么文件名？直接回车默认 研究模型图.png：").strip()
    n = len([v for v in vars_.split(",") if v.strip()])
    if n < 2:
        print("  模型图至少需要 2 个变量（直接效应，如：AI依赖,NSSI）。")
        return
    if n > 4:
        print("  链式模型最多 4 个变量（X、M1、M2、Y）；更多变量请在 JASP 或 PPT 中自行绘制。")
        return
    mtype = "chain" if n == 4 else ("simple" if n == 3 else "direct")
    args = ["--variables", vars_, "--type", mtype]
    if coefs:
        args += ["--coefs", coefs]
    args += ["--output", out if out else "研究模型图.png"]
    run("chart_generator.py", args)


def t_demo():
    print("\n【7/22】生成演示数据（还没收回问卷时，先拿它练手）")
    print("  会生成一份内置链式中介结构、含反向题的模拟数据，")
    print("  用来跑通第3步统计流程。模拟数据严禁写进真实论文。")
    out = input("  保存到哪个文件夹？可直接拖入一个文件夹，回车默认放进 我的工作区\\02-问卷数据：").strip().strip('"').strip("'")
    args = ["--outdir", out] if out else ["--outdir", "我的工作区/02-问卷数据"]
    run("generate_demo_data.py", args)
    if not out:
        print("  演示数据已放进「我的工作区\\02-问卷数据」，第3步统计时把里面的 demo_survey.csv 拖进来即可。")


def t_power():
    print("\n【8/22】开题样本量 / 功效估算（G*Power 等价，回答要发多少份）")
    print("  1 相关分析（Pearson r）")
    print("  2 多元回归总体 R²（检验整组预测变量）")
    print("  3 多元回归 R² 增量（检验新增变量，如交互项）")
    print("  4 单因素方差分析 ANOVA（多个组）")
    print("  5 独立两样本 t 检验（两组均数比较，给 Cohen's d）")
    print("  6 配对/单样本 t 检验（前后测，给标准化差值 dz）")
    d = input("  输入 1-6，回车默认先看三档效应量速查表：").strip()
    if d == "1":
        e = input("  相关系数 r（如 .3，回车看小/中/大三档）：").strip()
        args = ["--design", "correlation"] + (["--effect", e] if e else [])
    elif d == "2":
        u = input("  预测变量个数（回车默认5）：").strip() or "5"
        e = input("  效应量 f²（小.02/中.15/大.35，回车看三档）：").strip()
        args = ["--design", "regression", "--predictors", u] + (["--effect", e] if e else [])
    elif d == "3":
        tested = input("  本次新增检验的变量数（回车默认1）：").strip() or "1"
        total = input("  全模型预测变量总数（回车默认6）：").strip() or "6"
        e = input("  效应量 f²（小.02/中.15/大.35，回车看三档）：").strip()
        args = ["--design", "r2-change", "--tested", tested, "--total", total] + (["--effect", e] if e else [])
    elif d == "4":
        k = input("  组数（回车默认4）：").strip() or "4"
        e = input("  效应量 f（小.10/中.25/大.40，回车看三档）：").strip()
        args = ["--design", "anova", "--groups", k] + (["--effect", e] if e else [])
    elif d == "5":
        e = input("  效应量 Cohen's d（小.2/中.5/大.8，回车看三档）：").strip()
        args = ["--design", "ttest-ind"] + (["--effect", e] if e else [])
    elif d == "6":
        e = input("  标准化差值 dz（小.2/中.5/大.8，回车看三档）：").strip()
        args = ["--design", "ttest-paired"] + (["--effect", e] if e else [])
    else:
        args = []
    run("sample_size.py", args)


def t_preview():
    print("\n【9/22】预览我做的网页（本地预览，不上传任何东西）")
    print("  把你做的网页放进「我的工作区\\04-网页」，这里用浏览器打开它。")
    print("  还没有网页？对你的 AI 助手说：")
    print("     「我想做一个网页，你读一下 workflows/webpage-guide.md 带我做一个。」")
    print("  项目里已带 4 个现成范例（含问答式统计方法选择器），也可以先看看效果：")
    print("     templates\\网页范例\\  （双击里面的 index.html 即可）")
    print("-" * 60)
    d = ask_path("  要预览哪个文件夹？（直接回车 = 我的工作区\\04-网页）：", must_exist=False)
    args = [d] if d else []
    lan = input("  手机上也想看吗？（需与电脑连同一WiFi，回车=不看）[y/N]：").strip().lower()
    if lan in ("y", "yes", "是"):
        args.append("--lan")
    print("  预览期间保持这个窗口开着；看完按 Ctrl+C 停止，再按回车回到菜单。")
    run("webpage_preview.py", args)


def t_refs():
    print("\n【16/22】参考文献格式化（题录CSV → GB/T 7714-2015 编号列表，可直接粘进论文）")
    print("  吃第4项检索导出或第5项文献整理表的 CSV；期刊/专著/学位论文/会议/报纸/网页都支持。")
    tpl = input("  还没有题录表？输入 y 先在当前文件夹生成空白模板（直接回车=用已有CSV）：").strip().lower()
    if tpl == "y":
        run("reference_formatter.py", ["--save-template", "参考文献模板.csv"])
        print("\n  把题录逐行填进 参考文献模板.csv 后，再进本项并直接回车。")
        return
    f = ask_path("  把题录CSV拖进来，回车：")
    if not f:
        return
    args = [f]
    if input("  学校要求全角标点（．，：）？输入 y 用全角（直接回车=半角）：").strip().lower() == "y":
        args += ["--fullwidth"]
    if input("  外国作者姓氏按 GB/T 7714-2025 首字母大写？输入 y（直接回车=2015 全大写）：").strip().lower() == "y":
        args += ["--name-case", "2025"]
    run("reference_formatter.py", args)
    print("\n  工具只做格式化、不生成文献；复制进论文前逐条核对作者、年份、卷期页码与 DOI。")


def t_ppt():
    print("\n【21/22】把大纲排成 PPT（开题/答辩汇报 .pptx，只排版不代写）")
    print("  吃一份纯文本大纲：# 大标题、## 第N页：标题、- 要点（行首两个空格升二级）、")
    print("  | 竖线写表格、![题注](图.png) 整页插图、> 讲稿：写进演讲者备注（不上屏）。")
    print("  内容全部你自己写，工具一个字也不替你写。")
    print("  还没有大纲？先拷模板：templates\\opening-ppt-outline.md（12 页开题结构，把【】换成你的内容）")
    f = ask_path("  把你的大纲 .md 拖进来（直接回车=我的工作区\\05-开题报告\\我的开题大纲.md）：",
                 must_exist=False) or "我的工作区/05-开题报告/我的开题大纲.md"
    if not Path(f).exists():
        print("  ✗ 没找到大纲：" + f)
        print("    把 templates\\opening-ppt-outline.md 拷成上面这个路径、填好【】再回来跑这一项。")
        return
    args = [f]
    if input("  先只自检大纲、不出文件？输入 y=只自检（直接回车=直接生成）：").strip().lower() in ("y", "yes", "是", "1"):
        run("outline_to_ppt.py", args + ["--dry-run"])
        print("\n  自检只验大纲结构与图片路径，排版效果以生成的 .pptx 实开一遍为准。")
        return
    out = ask_path("  输出 .pptx 存哪儿？（直接回车=与大纲同名同目录）：", must_exist=False)
    if out:
        args += ["-o", out]
    font = input("  中文用什么字体？直接回车=微软雅黑；学校要求宋体就输入 宋体；输入 none=不改主题字体：").strip()
    if font:
        args += ["--cn-font", font]
    run("outline_to_ppt.py", args)
    print("\n  这一步需要 python-pptx（未装时工具会给出安装提示并退回大纲本身，不会崩）。")
    print("  生成后自己放映一遍：字体已写进文件主题，但换机器仍建议现场打开确认一遍版式。")


def t_workspace():
    print("\n【22/22】检查并补齐「我的工作区」九个目录（文献/问卷/结果/网页/开题/正文/答辩/量表伦理/导师沟通）")
    print("  只新增缺的目录，绝不重命名、移动、删除你已有的东西；重复跑没有副作用。")
    mode = input("  只想看看缺什么、先不动手？输入 c=只检查（直接回车=补齐）：").strip().lower()
    run("setup_workspace.py", ["--check"] if mode in ("c", "check", "检查") else [])
    print("\n  补齐之后，每个阶段的产出都放进对应目录，你自己和 AI 都按同一套目录找东西。")
