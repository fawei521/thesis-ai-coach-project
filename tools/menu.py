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
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 共用交互件在 menu_io.py；处理器按主题分册放：menu_data.py（数据与统计）、
# menu_lit.py（文献与产出）、menu_thesis.py（开题与材料检查）、menu_ref.py（原文与题录核验）、menu_kb.py（文献知识库）。
# 新工具要进菜单先确认没顶到文件尺寸闸门：顶到了就再拆一册，别把它挤在命令行里。
from menu_io import pause
from menu_lit import (t_search, t_lit, t_cards, t_chart, t_demo, t_power, t_preview, t_refs,
                      t_ppt, t_workspace)
from menu_data import (t_preprocess, t_clean, t_stats, t_anonymize, t_effect, t_validity,
                       t_itemanalysis, t_cvi, t_missing, t_assumption, t_paired, t_multcomp)
from menu_ref import t_fetch, t_verify   # v1.98 原文与题录核验组
from menu_kb import t_kb_index, t_kb_search   # v1.99 文献知识库组（攒卡片＋按行号回原文）
from menu_thesis import t_readiness, t_style, t_log, t_audit   # v1.85 开题与材料检查组（menu_lit 已顶到尺寸闸门，另起一册）


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
    ("13", "聚合/区分效度（CFA载荷→CR/AVE/Fornell，或原始数据→HTMT及95%CI）", t_validity),
    ("14", "预试问卷项目分析（高低27%决断值CR、CITC、删题后α，导出项目分析表）", t_itemanalysis),
    ("15", "自编量表内容效度CVI（专家评分→I-CVI、校正κ*、S-CVI/Ave与UA）", t_cvi),
    ("16", "参考文献格式化（题录CSV→GB/T 7714 编号列表，期刊/专著/学位论文/网页）", t_refs),
    ("17", "缺失值分析与Little MCAR检验（逐题缺失率/缺失模式/χ²，给可粘论文的结论）", t_missing),
    ("18", "参数检验前提假设（Shapiro正态性/偏度峰度/Brown-Forsythe方差齐性，给可粘论文结论）", t_assumption),
    ("19", "配对设计差异检验（前后测配对t/d_z/差值正态性/Wilcoxon符号秩，给可粘论文结论）", t_paired),
    ("20", "多重比较校正（Bonferroni/Holm/BH-FDR/BY-FDR，多组两两比较/多量表校正p值）", t_multcomp),
    ("21", "把大纲排成 PPT（开题/答辩汇报 .pptx，只排版不代写）", t_ppt),
    ("22", "检查并补齐「我的工作区」各类目录（开题到答辩全流程归档）", t_workspace),
    ("23", "开题就绪度自检（大纲+进度卡→缺项/矛盾/风险，只报问题不代写）", t_readiness),
    ("24", "AI 腔体检（草稿→套话/句式均一/缺具体信息，只报问题不代写、不测检测率）", t_style),
    ("25", "写作留痕（每版草稿记一行时间/字数/指纹，攒过程证据；不动草稿）", t_log),
    ("26", "文献原文可得性探测与下载（公开全文逐篇取，出六态台账；不绕付费墙）", t_fetch),
    ("27", "题录双源核验（Crossref+OpenAlex 逐字段比，专抓编造标题/错刊名/错 DOI）", t_verify),
    ("28", "清点我的文献知识库（攒了什么、各自核到什么程度、哪张卡缺证据）", t_kb_index),
    ("29", "检索我的文献知识库（BM25 词法检索，命中给文件名＋行号，离线零安装）", t_kb_search),
    ("30", "材料区目录体检（只读：东西在哪、哪份是当前版；一个文件都不改）", t_audit),
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
        print("  CFA后算CR/AVE/Fornell，或直接用原始数据算HTMT及95%CI，用 13")
        print("  预试问卷筛题（决断值CR/CITC/删题α）用 14")
        print("  自编量表请专家评内容效度（I-CVI/κ*/S-CVI）用 15")
        print("  写定稿整理参考文献（GB/T 7714 自动编号）用 16")
        print("  预处理后清洗前分析缺失值、跑Little MCAR检验用 17")
        print("  t/方差分析/回归前查正态性与方差齐性用 18")
        print("  配对差异（配对t、d_z、Wilcoxon符号秩）与单样本对标称常数（如 Likert 中值 3）都用 19")
        print("  多组两两比较/多量表/多时点的 p 值校正（Bonferroni/Holm/BH）用 20")
        print("  开题/答辩要上台：写好大纲用 21 排成 .pptx；目录没建好先用 22 补齐我的工作区")
        print("  开题前心里没底：用 23 跑一次就绪度自检（只报缺项/矛盾/风险，不替你写）")
        print("  综述里每条引用都要有全文：用 26 探测可得性并取公开原文；交稿前用 27 核验题录真伪")
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
