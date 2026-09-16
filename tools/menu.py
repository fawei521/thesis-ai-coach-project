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
            print(" 如果看不懂报错，把这段画面截图发给你的AI导师。）")
    except FileNotFoundError:
        print(f"没找到脚本 {script}，请确认 tools 文件夹完整。")
    except Exception as e:
        print(f"运行出错：{e}")


def pause():
    input("\n按回车键返回主菜单……")


def t_preprocess():
    print("\n【1/8】问卷星数据预处理")
    print("  用途：把问卷星下载的原始表，转成后面能统计的标准数字表。")
    f = ask_path("  把问卷星导出的原始CSV拖进来，回车：")
    if not f:
        return
    run("wjx_preprocess.py", [f])


def t_clean():
    print("\n【2/8】问卷数据清洗（找无效问卷）")
    f = ask_path("  把（预处理后的）数据CSV拖进来，回车：")
    if not f:
        return
    sec = input("  最短答题时间按多少秒算无效？直接回车用默认30秒：").strip()
    args = [f]
    if sec:
        args += ["--min-seconds", sec]
    run("data_cleaner.py", args)


def t_stats():
    print("\n【3/8】自动统计分析")
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
    run("auto_stats.py", args)
    print("\n  脚本已自动做Bootstrap中介；正式结果建议让AI导师带你用")
    print("  JASP/SPSS PROCESS 打开“_量表总分.csv”复核一次。")


def t_search():
    print("\n【4/8】检索英文学术文献（需要联网，免费，不用账号）")
    kw = input("  输入英文关键词（例如 AI dependence adolescent NSSI）：").strip()
    if not kw:
        print("  关键词为空，已取消。")
        return
    num = input("  要几篇？直接回车默认15篇：").strip() or "15"
    out = input("  结果保存成什么文件名？直接回车默认 英文文献.csv：").strip()
    args = ["--query", kw, "--limit", num]
    if out:
        args += ["--output", out]
    else:
        args += ["--output", "英文文献.csv"]
    run("paper_search.py", args)


def t_lit():
    print("\n【5/8】文献去重与分类")
    f = ask_path("  把文献列表（每行一篇的txt）拖进来，回车：")
    if not f:
        return
    run("literature_organizer.py", [f])


def t_chart():
    print("\n【6/8】生成研究模型图")
    print("  链式模型示例变量：AI依赖,孤独感,反刍,NSSI（用英文逗号分隔，4个）")
    print("  简单模型示例变量：AI依赖,NSSI（2个）")
    vars_ = input("  输入变量名（逗号分隔）：").strip()
    if not vars_:
        print("  未输入，已取消。")
        return
    coefs = input("  输入对应路径系数（逗号分隔，可先都填0占位）：").strip() or ""
    out = input("  图片保存成什么文件名？直接回车默认 研究模型图.png：").strip()
    n = len([v for v in vars_.split(",") if v.strip()])
    mtype = "chain" if n >= 3 else "simple"
    args = ["--variables", vars_, "--type", mtype]
    if coefs:
        args += ["--coefs", coefs]
    args += ["--output", out if out else "研究模型图.png"]
    run("chart_generator.py", args)


def t_demo():
    print("\n【7/8】生成演示数据（还没收回问卷时，先拿它练手）")
    print("  会生成一份内置链式中介结构、含反向题的模拟数据，")
    print("  用来跑通第3步统计流程。模拟数据严禁写进真实论文。")
    out = input("  保存到哪个文件夹？可直接拖入一个文件夹，回车默认当前目录：").strip().strip('"').strip("'")
    args = ["--outdir", out] if out else ["--outdir", "."]
    run("generate_demo_data.py", args)


def t_power():
    print("\n【8/8】开题样本量 / 功效估算（G*Power 等价，回答要发多少份）")
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


MENU = [
    ("1", "问卷星数据预处理（原始答卷 → 标准数字表）", t_preprocess),
    ("2", "问卷数据清洗（识别无效问卷）", t_clean),
    ("3", "自动统计分析（频数/信度/效度/EFA/Harman/相关/回归/Bootstrap中介）", t_stats),
    ("4", "检索英文学术文献（联网，免费）", t_search),
    ("5", "文献去重与分类", t_lit),
    ("6", "生成研究模型图", t_chart),
    ("7", "生成演示数据（没收回问卷前先练手）", t_demo),
    ("8", "开题样本量/功效估算（G*Power等价，要发多少份）", t_power),
]


def main():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("=" * 64)
        print("        毕业论文工具箱（心理学问卷研究）")
        print("=" * 64)
        print("  典型顺序：先 1 预处理 → 2 清洗 → 3 统计")
        print("  写文献综述时用 4 检索、5 整理；画图用 6；练手用 7；开题估样本量用 8")
        print("-" * 64)
        for num, name, _ in MENU:
            print(f"  {num}. {name}")
        print("  0. 退出")
        print("-" * 64)
        choice = input("请输入数字后回车：").strip()
        if choice == "0":
            print("再见！记得让AI导师帮你核对每一步结果。")
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
