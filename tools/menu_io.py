#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""菜单共用交互件：拖文件输入、跑子脚本、回车返回、读数字。
被 menu.py 与各分组处理器（menu_data.py / menu_lit.py）共同使用；本身不是入口，不要直接运行。"""

import subprocess
import time
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent   # tools/ 目录
PY = sys.executable

# --- 输出编码守卫：管道/重定向时强制 UTF-8（项目门禁统一要求，见 tests/full_e2e.py 全部脚本有编码守卫）---
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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


def choose_from(subdir, what):
    """目录里往往不止一份同类文件：列出候选让人挑，**不写死名字静默用其中一份**。

    09-23 真人走查撞到的原病：第 21 项"直接回车"用写死的大纲文件名，而那份是十天前的旧稿，
    目录里改过的新稿没人认领——PPT 照样排得出来，内容却是过期的，且不告诉任何人来源。
    返回相对仓库根的路径（/ 分隔）；目录里一份都没有时返回 ""（由调用方给指引）。
    """
    cands = sorted([p for p in Path(subdir).glob("*.md") if p.is_file()],
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        return ""
    pick = cands[0]
    if len(cands) > 1:
        print(f"  {subdir} 里有 {len(cands)} 份 .md（最近改的排第一）：")
        for i, p in enumerate(cands, 1):
            print("    %d. %s　改于 %s｜%s 字节" % (
                i, p.name, _stamp(p), format(p.stat().st_size, ",")))
        s = input(f"  要哪一份？输入序号选{what}（直接回车=第 1 份，即最近改的那份）：").strip()
        if s.isdigit() and 1 <= int(s) <= len(cands):
            pick = cands[int(s) - 1]
        elif s:
            print("  没认这个序号，按最近改的那份走。")
        if pick != cands[0]:
            print(f"  ⚠ 你选的不是最新那份——{cands[0].name} 改得更近，确认没拿错再继续。")
    n = sum(1 for c in pick.read_text(encoding="utf-8-sig", errors="replace") if "\u4e00" <= c <= "\u9fa5")
    print(f"  用的是：{pick}｜约 {n:,} 个汉字｜改于 {_stamp(pick)}")
    return pick.as_posix()


def _stamp(p):
    """文件的修改时间，只到分钟——够用来认出哪份最新。"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
