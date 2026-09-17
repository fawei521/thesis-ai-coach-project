#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
毕业论文工具箱 —— 统一菜单（给不想记命令的同学）
====================================================================
运行方式：
  方式一（推荐）：双击项目文件夹里的「启动工具箱.bat」
  方式二：在本文件所在目录执行  python menu.py

然后照着屏幕上的数字提示操作即可。每一步都会问你要文件，
你可以直接把文件从文件夹里“拖进这个黑窗口”，路径会自动填好。
====================================================================
"""

import os
import sys
import subprocess
from pathlib import Path
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent          # tools/ 目录
PY = sys.executable                              # 当前Python解释器


def ask_path(prompt, must_exist=True):
    """让用户输入/拖入一个文件路径，自动去掉拖拽带来的引号。"""
    while True:
        raw = input(prompt).strip().strip('"').strip("'")
        if raw == "":
            return ""
        p = Path(raw)
        if must_exist and not p.exists():
            print(f"  没找到这个文件：{raw}\n  请检查路径，或把文件直接拖进来。")
            continue
        return raw


def run(script, args):
    """以子进程方式运行 tools/ 下的脚本，参数用列表传递（不怕空格/中文）。"""
    cmd = [PY, str(HERE / script)] + [a for a in args if a != ""]
    print("\n" + "=" * 64)
    print("正在执行：", script, " ".join(args))
    print("=" * 64)
    try:
        result = subprocess.run(cmd, cwd=str(HERE.parent))
        if result.returncode != 0:
            print(f"\n（提示：{script} 运行返回码 {result.returncode}，")
            print(" 如果看不懂报错，把这段画面截图发给你的 AI 助手。）")
    except FileNotFoundError:
        print(f"没找到脚本 {script}，请确认 tools 文件夹完整。")
    except Exception as e:
        print(f"运行出错：{e}")


def pause():
    input("\n按回车键返回主菜单……")


def t_preprocess():
    print("\n【1/12】问卷星数据预处理")
    print("  用途：把问卷星下载的原始表，转成后面能统计的标准数字表。")
    f = ask_path("  把问卷星导出的原始CSV拖进来，回车：")
    if not f:
        return
    run("wjx_preprocess.py", [f])


def t_clean():
    print("\n【2/12】问卷数据清洗（找无效问卷）")
    f = ask_path("  把（预处理后的）数据CSV拖进来，回车：")
    if not f:
        return
    args = [f]
    sec = input("  最短答题时间按多少秒算无效？直接回车用默认30秒：").strip()
    if sec:
        args += ["--min-seconds", sec]
    sc = ask_path("  如果有 scales.txt，拖进来（让质量判断只针对量表题，更准；没有直接回车）：")
    if sc:
        args += ["--scales", sc]
    att = input("  问卷里有没有注意力检查题（如“本题请选3”）？有就输入 列名关键词=正确答案，多道用分号隔开；没有直接回车：").strip()
    if att:
        args += ["--attention", att]
    print("  （另自动检查长直线作答、作答几乎无变异SD、缺失率超两成；阈值默认即可，高级用法见说明书）")
    run("data_cleaner.py", args)


def t_stats():
    print("\n【3/12】自动统计分析")
    print("  自动完成：人口学频数表、反向计分、信度α、结构效度(KMO/Bartlett/载荷)、")
    print("  共同方法偏差Harman、量表总分、描述统计、相关、回归、")
    print("  Bootstrap中介（模型4/6），并导出三线表和频数表。")
    print("  自编/修订量表还可选做完整探索性因子分析EFA（多因子+方差最大旋转）。")
    f = ask_path("  把清洗后的数据CSV拖进来，回车：")
    if not f:
        return
    print("  量表配置文件 scales.txt 告诉程序哪些题属于哪个量表、哪些是反向题。")
    print("  格式示例：孤独感:5=M1,M2(R),M3,M4  （:5是5点量表，(R)是反向题）")
    sc = ask_path("  有 scales.txt 就拖进来（没有就直接回车，先做全量分析）：",
                  must_exist=False)
    args = [f]
    if sc:
        args += ["--scales", sc]
        y = input("  因变量量表名（如 NSSI，没有就直接回车）：").strip()
        x = input("  自变量量表名（如 AI情感依赖，没有就回车）：").strip()
        med = ""
        if y and x:
            med = input("  中介变量（简单中介填1个如 孤独感；链式填2个逗号分隔如 孤独感,反刍思维；不做直接回车）：").strip()
        if y and x:
            args += ["--y", y, "--x", x]
            if med:
                args += ["--mediators", med]
        efa = input("  是否做完整探索性因子分析EFA（自编/重大修订量表才需要；含平行分析定因子数、自动碎石图；输入y=是，直接回车=跳过）：").strip().lower()
        if efa in ("y", "yes", "是", "1"):
            names = input("    对哪个量表做？多个用逗号分隔，直接回车=对全部量表：").strip()
            args += ["--efa"] + ([names] if names else [])
        nprm = input("  人口学差异是否用非参数检验（因变量明显偏态/有序等级、t检验前提不满足时选是；2组Mann-Whitney U、多组Kruskal-Wallis；y=是，回车=默认t/ANOVA）：").strip().lower()
        if nprm in ("y", "yes", "是", "1"):
            args += ["--nonparametric"]
        sp = input("  相关分析是否用 Spearman 秩相关（变量明显偏态/有序等级时选是；回车=默认Pearson）：").strip().lower()
        if sp in ("y", "yes", "是", "1"):
            args += ["--spearman"]
        pc = input("  是否做偏相关（控制性别/年级等后看净相关，回车=不做；要做就填控制变量，如 性别,年级）：").strip()
        if pc:
            args += ["--partial", pc]
    run("auto_stats.py", args)
    print("\n  脚本已自动做Bootstrap中介；正式结果建议让 AI 助手带你用")
    print("  JASP/SPSS PROCESS 打开“_量表总分.csv”复核一次。")


def t_search():
    print("\n【4/12】检索英文学术文献（需要联网，免费，不用账号）")
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
    print("\n【5/12】文献去重与分类")
    print("  可拖入的有两种：① 每行一篇的 txt；② 第 4 项检索导出的标准 CSV（含 标题/作者 表头）。")
    print("  也可以直接拖知网导出的题录 txt。")
    f = ask_path("  把文献文件拖进来，回车：")
    if not f:
        return
    run("literature_organizer.py", [f])


def t_cards():
    print("\n【10/12】生成重点文献卡片网页（手机友好，挑精读用）")
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
    print("\n【6/12】生成研究模型图")
    print("  链式模型示例变量：AI依赖,孤独感,反刍,NSSI（用英文逗号分隔，4个）")
    print("  简单模型示例变量：AI依赖,NSSI（2个）")
    vars_ = input("  输入变量名（逗号分隔）：").strip()
    if not vars_:
        print("  未输入，已取消。")
        return
    coefs = input("  输入对应路径系数（逗号分隔；还没结果就直接回车，先用0占位出框架图）：").strip() or ""
    out = input("  图片保存成什么文件名？直接回车默认 研究模型图.png：").strip()
    n = len([v for v in vars_.split(",") if v.strip()])
    mtype = "chain" if n >= 3 else "simple"
    args = ["--variables", vars_, "--type", mtype]
    if coefs:
        args += ["--coefs", coefs]
    args += ["--output", out if out else "研究模型图.png"]
    run("chart_generator.py", args)


def t_demo():
    print("\n【7/12】生成演示数据（还没收回问卷时，先拿它练手）")
    print("  会生成一份内置链式中介结构、含反向题的模拟数据，")
    print("  用来跑通第3步统计流程。模拟数据严禁写进真实论文。")
    out = input("  保存到哪个文件夹？可直接拖入一个文件夹，回车默认放进 我的工作区\\02-问卷数据：").strip().strip('"').strip("'")
    args = ["--outdir", out] if out else ["--outdir", "我的工作区/02-问卷数据"]
    run("generate_demo_data.py", args)
    if not out:
        print("  演示数据已放进「我的工作区\\02-问卷数据」，第3步统计时把里面的 demo_survey.csv 拖进来即可。")


def t_power():
    print("\n【8/12】开题样本量 / 功效估算（G*Power 等价，回答要发多少份）")
    print("  1 相关分析（Pearson r）")
    print("  2 多元回归总体 R²（检验整组预测变量）")
    print("  3 多元回归 R² 增量（检验新增变量，如交互项）")
    print("  4 单因素方差分析 ANOVA（多个组）")
    d = input("  输入 1-4，回车默认先看三档效应量速查表：").strip()
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
    else:
        args = []
    run("sample_size.py", args)



def t_preview():
    print("\n【9/12】预览我做的网页（本地预览，不上传任何东西）")
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


def t_anonymize():
    print("\n【11/12】数据去标识化（发给AI/上传/给外校前，隐去姓名学号手机等）")
    print("  自动识别并假名化/删除姓名、学号、手机、邮箱、身份证、微信/QQ、IP、住址等，")
    print("  并对性别/年级/专业/生源等组合做 k-匿名风险体检；只读原文件、另存新文件，绝不改原数据。")
    f = ask_path("  把要外发的原始数据CSV拖进来，回车：")
    if not f:
        return
    args = [f]
    d = input("  只先体检、不写文件吗？（回车=正式处理并另存；输入 y=只体检）：").strip().lower()
    if d in ("y", "yes", "是", "1"):
        args += ["--dry-run"]
        run("anonymize_data.py", args)
        return
    nk = input("  要不要保留“编号↔姓名”对照表用于前后测配对？（回车=保留对照表并单独收好；输入 n=彻底不留、不可复原）：").strip().lower()
    if nk in ("n", "no", "否", "0"):
        args += ["--no-key"]
    run("anonymize_data.py", args)
    print("\n  提醒：若生成了“假名对照表”，它是唯一能还原身份的钥匙，")
    print("  必须和数据分开单独保管，绝不发给AI/上传，配对完尽早删除。")


def _ask_num(prompt, kind=float):
    """读一个数字；留空返回 None（用于取消/可选）。"""
    raw = input(prompt).strip()
    if raw == "":
        return None
    try:
        return kind(raw)
    except ValueError:
        print("  没看懂这个数字，已取消这一步。")
        return None


def t_effect():
    print("\n【12/12】效应量换算与复核（写结果时，由 t/F/χ²/r 或均值标准差算效应量）")
    print("  论文不能只报 p 值，还要报效应量及（能给时）置信区间。选你手上已有的结果：")
    print("   1 两组均值/标准差/n → Cohen's d、Hedges' g")
    print("   2 已知 t 值 → d（独立两组）或配对 d_z")
    print("   3 已知 r 和 n → r 的95%CI，并换算 d")
    print("   4 已知 F 值（方差分析）→ 偏 η²")
    print("   5 已知 χ²（卡方）→ Cramér's V / φ")
    print("   6 r 与 d 互转")
    c = input("  输入 1-6，回车取消：").strip()
    if c == "1":
        m1 = _ask_num("  第1组均值："); sd1 = _ask_num("  第1组标准差："); n1 = _ask_num("  第1组n：", int)
        m2 = _ask_num("  第2组均值："); sd2 = _ask_num("  第2组标准差："); n2 = _ask_num("  第2组n：", int)
        if None in (m1, sd1, n1, m2, sd2, n2):
            return
        args = ["d", "--m1", str(m1), "--sd1", str(sd1), "--n1", str(n1),
                "--m2", str(m2), "--sd2", str(sd2), "--n2", str(n2)]
    elif c == "2":
        t = _ask_num("  t 值（带正负号）：")
        if t is None:
            return
        paired = input("  是配对（前后测）吗？[y/N]：").strip().lower()
        if paired in ("y", "yes", "是", "1"):
            n = _ask_num("  配对人数 n：", int)
            if n is None:
                return
            args = ["paired-d", "--t", str(t), "--n", str(n)]
        else:
            n1 = _ask_num("  第1组n：", int); n2 = _ask_num("  第2组n：", int)
            if n1 is None or n2 is None:
                return
            args = ["d-t", "--t", str(t), "--n1", str(n1), "--n2", str(n2)]
    elif c == "3":
        r = _ask_num("  相关系数 r（-1~1）："); n = _ask_num("  样本量 n：", int)
        if r is None or n is None:
            return
        args = ["r", "--r", str(r), "--n", str(n)]
    elif c == "4":
        f = _ask_num("  F 值："); d1 = _ask_num("  分子自由度 df1：", int); d2 = _ask_num("  分母自由度 df2：", int)
        if f is None or d1 is None or d2 is None:
            return
        args = ["eta", "--F", str(f), "--df1", str(d1), "--df2", str(d2)]
    elif c == "5":
        chi = _ask_num("  χ² 值："); n = _ask_num("  总样本量 N：", int)
        rows = _ask_num("  行数（如2）：", int); cols = _ask_num("  列数（如2）：", int)
        if chi is None or n is None or rows is None or cols is None:
            return
        args = ["v", "--chi2", str(chi), "--n", str(n), "--rows", str(rows), "--cols", str(cols)]
    elif c == "6":
        kind = input("  手上是 r 还是 d？输入 r 或 d（留空取消）：").strip().lower()
        val = _ask_num("  数值：")
        if not kind or val is None:
            return
        args = ["convert", "--r", str(val)] if kind in ("r", "相关") else ["convert", "--d", str(val)]
    else:
        print("  已取消。")
        return
    run("effect_size.py", args)
    print("\n  以上为快速复核；精确 p 值与区间以 JASP/SPSS 正式输出为准，效应量必须来自你的真实结果。")


MENU = [
    ("1", "问卷星数据预处理（原始答卷 → 标准数字表）", t_preprocess),
    ("2", "问卷数据清洗（识别无效问卷）", t_clean),
    ("3", "自动统计分析（频数/信度/效度/EFA/Harman/相关/回归/Bootstrap中介）", t_stats),
    ("4", "检索英文学术文献（联网，免费）", t_search),
    ("5", "文献去重与分类", t_lit),
    ("6", "生成研究模型图", t_chart),
    ("7", "生成演示数据（没收回问卷前先练手）", t_demo),
    ("8", "开题样本量/功效估算（G*Power等价，要发多少份）", t_power),
    ("9", "预览我做的网页（本地预览，不上传）", t_preview),
    ("10", "生成重点文献卡片网页（检索/整理 CSV → 手机友好 HTML）", t_cards),
    ("11", "数据去标识化（外发前隐去姓名/学号/手机，附k-匿名体检）", t_anonymize),
    ("12", "效应量换算与复核（由t/F/χ²/r或均值标准差算d、r、η²、V及区间）", t_effect),
]


def main():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("=" * 64)
        print("        毕业论文工具箱（心理学问卷研究）")
        print("=" * 64)
        print("  典型顺序：先 1 预处理 → 2 清洗 → 3 统计")
        print("  写文献综述时用 4 多词检索（可凑约90篇候选池）→ 5 整理 → 10 生成重点卡片")
        print("  画图用 6；练手用 7；开题估样本量用 8；预览自己的网页用 9")
        print("  数据外发前用 11 去标识化；写结果补效应量用 12")
        print("-" * 64)
        for num, name, _ in MENU:
            print(f"  {num}. {name}")
        print("  0. 退出")
        print("-" * 64)
        choice = input("请输入数字后回车：").strip()
        if choice == "0":
            print("再见！记得让 AI 助手帮你核对每一步结果。")
            break
        action = None
        for num, name, fn in MENU:
            if choice == num:
                action = fn
                break
        if action is None:
            print("没有这个选项，请重新输入。")
            input("回车继续……")
            continue
        action()
        pause()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n已退出。")
