#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""菜单处理器：文献知识库组（v1.99 起）。
被 menu.py 调用，本身不是入口，不要直接运行。
另起一册的原因同 menu_ref.py：menu_lit.py 顶在文件尺寸闸门上（见 tests/size_ratchet.py）。"""
from menu_io import ask_path, run

KB = "我的工作区/10-知识库"
YES = ("y", "yes", "是")


def t_kb_index():
    print("\n【28/30】文献知识库清点（回答一个问题：我本地到底攒了些什么、各自核到什么程度）")
    print("  它扫 `%s/` 里的每一张卡片，报三件事：" % KB)
    print("    ① 按「我读到哪一层」分档——只有摘要的卡不能拿来下结论，这一步把这件事变成看得见的数；")
    print("    ② 哪张卡缺逐字原文／缺位置／缺核对状态，哪张卡写的原文路径已经失效；")
    print("    ③ 与 v1.98 的 `原文获取台账.md` 和 `01-文献PDF/原文/` 对账：取了全文却没建卡的，列出来。")
    print("  ⛔ 它只读不改：不生成卡片、不补任何一格、不删任何文件（缺的东西得你自己填进去）。")
    d = ask_path("  库目录（回车=%s）：" % KB, must_exist=False) or KB
    args = ["--kb", d]
    if input("  顺手把索引存成 `知识库索引.md`（换对话时交给 AI）？回车=不，y=要：").strip().lower() in YES:
        args.append("--write")
    run("kb_index.py", args)
    print("\n  第一次跑多半是空的——先照 workflows/knowledge-base-setup.md 建第一张卡（复制模板改格子，十分钟）。")
    print("  库里「仅摘要」那一档的张数，就是你下一篇该去下全文的清单。")


def t_kb_search():
    print("\n【29/30】查自己的文献库（写论文时被问「这个数哪来的」，就用它回答）")
    print("  词法检索（BM25＋中文二元切分，纯标准库、离线、零安装），每条命中给出**文件名＋行号**——")
    print("  这样你能立刻打开那一行看上下文，而不是听 AI 复述。")
    print("  ⚠ 两个诚实的边界：① 近义说法会漏，换词再查，别据此说库里没有；")
    print("     ② 卡片是定位器、不是证据本身：摘要级的卡照样不能下结论（core/literature-kb.md 第二节）。")
    q = input("  检索词（可多个，空格隔开）：").strip()
    if not q:
        print("  得先说要查什么。例：孤独感 反刍 ／ CAIDS ／ 中介效应")
        return
    args = q.split()
    if input("  只看「全文PDF」级的卡？回车=不，y=要：").strip().lower() in YES:
        args.append("--full-only")
    if input("  只看你已逐字比对过的卡？回车=不，y=要：").strip().lower() in YES:
        args.append("--checked-only")
    if input("  只在「逐字原文」那几行里搜（找具体某句话时用）？回车=不，y=要：").strip().lower() in YES:
        args.append("--verbatim")
    d = ask_path("  库目录（回车=%s）：" % KB, must_exist=False)
    if d:
        args += ["--dir", d]
    run("kb_search.py", args)
    print("\n  命中之后：打开那张卡那一行读上下文；要写进正式稿，回它「本地原文」那个文件再核一遍原句。")
