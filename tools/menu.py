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
    print("\n【1/7】问卷星数据预处理")
    print("  用途：把问卷星下载的原始表，转成后面能统计的标准数字表。")
    f = ask_path("  把问卷星导出的原始CSV拖进来，回车：")
    if not f:
        return
    run("wjx_preprocess.py", [f])


def t_clean():
    print("\n【2/7】问卷数据清洗（找无效问卷）")
    f = ask_path("  把（预处理后的）数据CSV拖进来，回车：")
    if not f:
        return
    sec = input("  最短答题时间按多少秒算无效？直接回车用默认30秒：").strip()
    args = [f]
    if sec:
        args += ["--min-seconds", sec]
    run("data_cleaner.py", args)


def t_stats():
    print("\n【3/7】自动统计分析")
    print("  自动完成：反向计分、信度α、共同方法偏差Harman、量表总分、")
    print("  描述统计、相关、回归、Bootstrap中介（模型4/6），并导出三线表。")
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
    run("auto_stats.py", args)
    print("\n  脚本已自动做Bootstrap中介；正式结果建议让AI导师带你用")
    print("  JASP/SPSS PROCESS 打开“_量表总分.csv”复核一次。")


def t_search():
    print("\n【4/7】检索英文学术文献（需要联网，免费，不用账号）")
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
    print("\n【5/7】文献去重与分类")
    f = ask_path("  把文献列表（每行一篇的txt）拖进来，回车：")
    if not f:
        return
    run("literature_organizer.py", [f])


def t_chart():
    print("\n【6/7】生成研究模型图")
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
    print("\n【7/7】生成演示数据（还没收回问卷时，先拿它练手）")
    print("  会生成一份内置链式中介结构、含反向题的模拟数据，")
    print("  用来跑通第3步统计流程。模拟数据严禁写进真实论文。")
    out = input("  保存到哪个文件夹？可直接拖入一个文件夹，回车默认当前目录：").strip().strip('"').strip("'")
    args = ["--outdir", out] if out else ["--outdir", "."]
    run("generate_demo_data.py", args)


MENU = [
    ("1", "问卷星数据预处理（原始答卷 → 标准数字表）", t_preprocess),
    ("2", "问卷数据清洗（识别无效问卷）", t_clean),
    ("3", "自动统计分析（反向计分/信度/Harman/相关/回归）", t_stats),
    ("4", "检索英文学术文献（联网，免费）", t_search),
    ("5", "文献去重与分类", t_lit),
    ("6", "生成研究模型图", t_chart),
    ("7", "生成演示数据（没收回问卷前先练手）", t_demo),
]


def main():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("=" * 64)
        print("        毕业论文工具箱（心理学问卷研究）")
        print("=" * 64)
        print("  典型顺序：先 1 预处理 → 2 清洗 → 3 统计")
        print("  写文献综述时用 4 检索、5 整理；画图用 6；练手用 7")
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
