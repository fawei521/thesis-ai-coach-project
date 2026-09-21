#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""菜单处理器：文献原文与题录核验组（v1.98 起）。
被 menu.py 调用，本身不是入口，不要直接运行。
另起一册的原因同 menu_thesis.py：menu_lit.py 已顶在 219/220 行的文件尺寸闸门上
（见 tests/size_ratchet.py 与 DEVELOPMENT.md 的"菜单加一项的正确姿势"）。"""
from pathlib import Path

from menu_io import ask_path, run


def t_fetch():
    print("\n【26/27】文献原文可获取性探测与下载（先把\"有没有全文\"查清，再谈能不能引）")
    print("  它读一份文献清单（CSV/JSON：id,doi,pmcid,arxiv,url,expect_title），")
    print("  逐篇到出版方或机构库的**公开**入口试一次，返回六态之一：")
    print("  可获取／已获取／非PDF／失败／需数据库／标题对不上。")
    print("  为什么值得跑：`core/evidence-rigor.md` 把\"读的是什么材料\"列为引用四要素之一——")
    print("  **只有摘要时不得输出\"该研究发现 X\"级别的结论**。这一项把\"光有摘要不能引\"变成一次可复跑的检查。")
    print("  ⛔ 它不绕付费墙、不碰要登录的数据库（知网那部分走 workflows/literature-auto-search.md，")
    print("     登录一律你本人输入）；逐篇下载、单次默认上限 30 篇，与你校《电子资源使用规定》一致，一律从严。")
    f = ask_path("  文献清单（CSV 或 JSON；回车=用 templates\\文献原文清单模板.csv 自己复制一份去填）：",
                 must_exist=False)
    if not f or not Path(f).exists():
        print("  先把模板复制成自己的清单：copy templates\\文献原文清单模板.csv 我的工作区\\01-文献PDF\\我的清单.csv")
        print("  模板里附了本次真实用过的列写法，一行一篇。")
        return
    mode = input("  先探测不落盘（回车=探测，输入 g=直接下载公开全文）：").strip().lower()
    args = [f, "--probe" if mode != "g" else "--go"]
    out = ask_path("  原文落盘目录（回车=我的工作区\\01-文献PDF\\原文）：", must_exist=False)
    if out:
        args += ["--out", out]
    rep = ask_path("  台账输出 .md（回车=我的工作区\\01-文献PDF\\原文获取台账.md）：", must_exist=False)
    if rep:
        args += ["--report", rep]
    run("lit_fetch.py", args)
    print("\n  台账里\"需数据库\"那些行不是失败——那是只能从知网/图书馆拿的，按 workflow 第五步逐篇人工下。")
    print("  \"标题对不上\"必须当场改 DOI：一位数字错了，取回来的就是别人的文章。")


def t_verify():
    print("\n【27/27】题录双源核验（这条参考文献是真的吗？字段对不对？")
    print("  两个独立登记处逐字段比：Crossref（出版方 DOI 元数据）＋ OpenAlex（另一家索引库）。")
    print("  五种结果：双源一致／单源／有出入／双源互斥／登记处查无。")
    print("  专抓三种最要命的错：**编出来的标题**、**把 A 刊写成 B 刊**、**DOI 猜一位指向了另一篇**——")
    print("  这三种都是\"格式齐、内容错\"，人眼扫不出来；写进开题就是一次对他人文献的错指控。")
    print("  ⚠ 它不生成文献、不替你补字段：查无就是查无，缺哪格标哪格，绝不填一个看着像的值。")
    f = ask_path("  你的题录表 CSV（列：题名,作者,年份,期刊,卷,期,页,DOI）：")
    if not f:
        print("  得先说核验哪张表——菜单第 4 项的检索导出、第 5 项的整理表都能直接喂进来。")
        return
    gbt = input("  顺便生成 GB/T 7714 条目（字段取自登记处）？回车=不，输入 y=要：").strip().lower()
    strict = input("  有不一致条目时返回失败码（第 23 项自检串用）？回车=不，输入 y=要：").strip().lower()
    args = [f] + (["--gbt"] if gbt in ("y", "yes", "是") else []) \
        + (["--strict"] if strict in ("y", "yes", "是") else [])
    run("lit_verify.py", args)
    print("\n  报告里\"有出入/双源互斥/登记处查无\"的行：回原文（知网或出版社页面版权页）定夺，")
    print("  补不到就把这条删掉——`core/evidence-rigor.md` 第九节：宁可少引一篇真文献。")
    print("  定完再跑第 16 项整序、第 23 项就绪度自检。")
