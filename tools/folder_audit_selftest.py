#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""folder_audit 的阴性自测夹具：造一个"每条判据都必然踩一次"的坏目录。

为什么单开一份文件（不是洁癖）：`folder_audit.py` 顶在 220 行硬闸上——判据每加一条就得先减一行，
而**夹具不是判据，不该跟判据抢行数**。挪出来之后，加判据才有地方写；夹具本身改起来也不动尺子。
只在 `--selftest` 时被 import，日常体检不加载它。

改这里请注意：**加一条判据就得在这里加一处对应夹具**，否则 `--selftest` 会报"没咬住 Rn"——
那是设计意图（想不出怎么触发的判据，多半是空转的判据），不是障碍。
"""
import datetime
import os
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与 folder_audit.py 同一口径，无条件生效，见 DEVELOPMENT.md 阶段 B）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _write(root, rel, text="x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def build(ws, stale_days=30):
    """在 ws（一个当"我的工作区"用的目录，不存在会建）下造出各条判据要抓的东西。只造文件，不改任何东西。"""
    ws.mkdir(parents=True, exist_ok=True)
    _write(ws, "01-文献PDF/我的论文进度.md")        # R1：同一棵树下两份"唯一权威文件"
    _write(ws, "09-导师沟通记录/我的论文进度.md")
    _write(ws, "01-文献PDF/总览.md")                # R5：同层两份 .md，目录.md 里没写当前版
    _write(ws, "01-文献PDF/总览35篇.md")
    _write(ws, "01-文献PDF/题录.json")              # R2：机器产物与给人看的 .md 并排
    _write(ws, "01-文献PDF/目录.md", "")
    _write(ws, "01-文献PDF/README.md")              # R8：一层出现第二个入口
    _write(ws, "01-文献PDF/_本次核验.py")           # R4：文件名写着时效词
    (ws / "01-文献PDF" / "原文").mkdir()            # R3：搬完留下的空壳
    (ws / "99-自由发挥").mkdir()                    # R7：顶层冒出 LAYOUT 之外的目录
    _write(ws, "02-问卷数据/答卷.csv")              # R6：放了东西却没有 目录.md
    late = _write(ws, "_scratch/核验_文献1信度.py", "#")   # R9：临时区脚本放超过一周没清
    then = (datetime.datetime.now() - datetime.timedelta(days=stale_days)).timestamp()
    os.utime(late, (then, then))
    _write(ws, "跑一遍.py", "#")                    # R10：根一层放脚本（能跑的该进 tools/）
