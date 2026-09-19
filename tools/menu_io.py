#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""菜单共用交互件：拖文件输入、跑子脚本、回车返回、读数字。
被 menu.py 与各分组处理器（menu_data.py / menu_lit.py）共同使用；本身不是入口，不要直接运行。"""

import subprocess
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
