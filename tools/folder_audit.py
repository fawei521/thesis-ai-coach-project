#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""材料区目录体检（只读裁判，纯标准库，一个文件都不改）。

**挂在图形菜单第 30 项**（处理器在 `menu_thesis.t_audit`）：学生双击就能跑，AI 也能直接命令行调用。
它只报位置和形制，不替你写一个字——归位与 目录.md 由学生和它的 AI 完成，
规则在 `core/literature-kb.md` 第九、十节。

为什么要有它：仓里写过三条"要归位／要登记／用完即删"，**三条全部落空**——它们管开发仓，材料却落在没有 git、
没有门禁的那份副本里。写第四条"要注意卫生"一样不会有用的，所以这里只做一件事：**把卫生翻译成能判红的形制**。

八条判据（红＝会误导人下错判断；黄＝该收一下）：
  R1 红 同一棵树里两份以上"唯一权威文件"（进度卡）——两张卡必然有一张是错的
  R2 黄 人读目录（同层有 .md）里 `.json/.xml/.log/.py` 与 .md 并排——机器产物跟给人看的混放
  R3 黄 子项为 0 的目录壳——搬完没留指针，别人只会以为东西没了
  R4 黄 文件名含"本次/最新/终版/最终/新建/副本/未命名"——这类词三天后失去含义
  R5 红 同目录两份以上 .md，却没有 `目录.md` 指出当前版——翻到哪份算哪份
  R6 黄 目录里有实文件（占位说明不算）却没有 `目录.md`
  R7 红 顶层冒出 LAYOUT 之外的目录——名单只有一份，从 `setup_workspace.py` 解析，不抄第二遍
  R8 红 同一层出现两个"入口"（`目录.md` 与 `README/索引/说明/00-` 式文件并存）——一层只准一个法律

用法（**只扫材料区**，拿它扫代码仓会一堆假红）：
  python folder_audit.py 我的工作区            # 打印报告
  python folder_audit.py 我的工作区 --strict    # 有红项返回非零（给门禁串用）
  python folder_audit.py --copies D:\桌面        # 跨副本看同一个进度卡有几份在用
  python folder_audit.py --selftest             # 造一个坏目录，七条必须全命中（判据的阴性自测）
"""
import argparse
import datetime
import re
import sys
import tempfile
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 默认 GBK，遇 ⚠ ↔ ² 会崩）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
MACHINE = {".json", ".xml", ".log", ".py", ".pyc"}
STALE_WORDS = ("本次", "最新", "终版", "最终", "新建", "副本", "未命名")
AUTHORITY = {"我的论文进度.md"}
SKIP_DIRS = {".git", "__pycache__", ".tmp_e2e", "node_modules", ".mypy_cache"}
PLACEHOLDER = re.compile(r"^把.*放这里\.txt$")
ENTRY = re.compile(r"^(目录\.md|README.*\.md|00-.*\.md|.*索引\.md|.*说明\.md)$")
INDEX = "目录.md"
CURRENT_MARK = ("当前版", "该看哪份")


def archived(rel):
    """路径里任一段是"声明过只存旧东西"的层 = 归档/临时区（`_` 开头，或 `旧版/`），
    不按"当前版在哪"要求它——它存的就是旧东西。但空壳（R3）与时效词文件名（R4）照抓。
    收 Path 也收 parts 元组，调用方不用换算。"""
    parts = [str(p) for p in getattr(rel, "parts", rel)]
    return any(p.startswith("_") or p == "旧版" for p in parts)


def walk(root):
    """只往下走材料区，跳过代码仓的临时与缓存目录。"""
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        yield p


def layout_names(src=None):
    """从 setup_workspace.py 的 LAYOUT 解析顶层目录名单——**不在这里抄第二份**。
    读不到就返回 None、R7 整条跳过，`--selftest` 于是报"没咬住 R7"，不静默放行。"""
    src = Path(src) if src else REPO / "tools" / "setup_workspace.py"
    if not src.is_file():
        print(f"  [警告] 读不到 LAYOUT 来源：{src}（R7 本轮回跳过，不算通过）")
        return None
    block = src.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^LAYOUT\s*=\s*\[(.*?)^\]", block, re.S | re.M)
    if not m:
        return None
    return set(re.findall(r'\(\s*"([^"/]+?)"\s*,', m.group(1)))


def audit(root, layout=None):
    """返回 [(级别, 判据, 位置, 该补什么)]。只报位置和形制，不替你判断内容对不对。"""
    hits = []
    dirs = [root] + [p for p in walk(root) if p.is_dir()]
    files = [p for p in walk(root) if p.is_file()]
    by_dir = {}
    for f in files:
        by_dir.setdefault(f.parent, []).append(f)

    for name in sorted(AUTHORITY):
        found = [p for p in files if p.name == name and not archived(p.relative_to(root))]
        if len(found) > 1:
            hits.append(("红", "R1", "；".join(str(p.relative_to(root)) for p in found),
                         f"{name} 在这棵树里有 {len(found)} 份在用的，留一份当权威、其余移进 _归档 或改名标旧副本"))

    for d, fs in sorted(by_dir.items()):
        rel = Path(".") if d == root else d.relative_to(root)
        mds = [f for f in fs if f.suffix == ".md" and f.name != INDEX]
        skip = archived(rel)
        if not skip and mds and any(f.suffix in MACHINE for f in fs):
            bad = [f.name for f in fs if f.suffix in MACHINE]
            hits.append(("黄", "R2", f"{rel}/", f"机器产物 {len(bad)} 个（{'、'.join(bad[:4])}）"
                                              f"与 {len(mds)} 份 .md 并排，挪进中间产物子层"))
        for f in fs:
            if any(w in f.name for w in STALE_WORDS) and f.name != INDEX:
                hits.append(("黄", "R4", str(f.relative_to(root)),
                             "这类词过几天没人知道指哪一次，改成语义名或带日期 YYYYMMDD"))
        real = [f for f in fs if not PLACEHOLDER.match(f.name) and f.name != INDEX]
        idx = d / INDEX
        if skip:
            continue
        entries = [f.name for f in fs if ENTRY.match(f.name)]
        if len(entries) > 1:
            hits.append(("红", "R8", f"{rel}/", f"{len(entries)} 个入口并存（{'、'.join(entries)}）——一层只准一个法律"))
        if len(mds) >= 2:
            if not idx.is_file():
                hits.append(("红", "R5", f"{rel}/",
                             f"{len(mds)} 份 .md 没有一份被指为当前版，补 {INDEX}"))
            else:
                txt = idx.read_text(encoding="utf-8", errors="replace")
                if not any(k in txt for k in CURRENT_MARK):
                    hits.append(("红", "R5", f"{rel}/{INDEX}",
                                 f"{len(mds)} 份 .md，但 {INDEX} 里没写当前版是哪份"))
        elif real and not idx.is_file() and not all(f.suffix in MACHINE for f in real):
            hits.append(("黄", "R6", f"{rel}/", f"{len(real)} 个文件却没有任何说明，补 {INDEX}"))

    names = layout_names(layout)
    for sub in dirs[1:]:
        try:
            empty = not any(sub.iterdir())
        except OSError:
            empty = False
        if empty:
            hits.append(("黄", "R3", f"{sub.relative_to(root)}/",
                         "空目录，删掉或留一句东西搬去哪了"))
        if sub.parent == root and names and sub.name not in names and not sub.name.startswith("_"):
            hits.append(("红", "R7", f"{sub.name}/",
                         "不在 setup_workspace 的 LAYOUT 里；顶层目录要加得先改 LAYOUT，别就地建"))
    return hits


def report(root, hits):
    print(f"材料区：{root}")
    for level, rule, where, todo in sorted(hits, key=lambda h: (h[0] != "红", h[1], h[2])):
        print(f"  [{level}] {rule} {where}\n        → {todo}")
    red = sum(1 for h in hits if h[0] == "红")
    yellow = len(hits) - red
    print(f"结论：红 {red} 项、黄 {yellow} 项（判定只看形制，内容对不对不在本工具范围内）")
    return red


def copies(base):
    """跨副本清点权威文件有几份在同时被用——两张进度卡并存，正是今天这摊乱的根因。

    七条判据只在**一个材料区内**有效，看不见"同一台机器上有两份副本"这件事，所以单列这一项。
    """
    found = sorted(p for p in Path(base).rglob("*")
                   if p.name in AUTHORITY and ".git" not in p.parts and not archived(p.parts))
    print(f"基准：{base} —— 找到 {len(found)} 份权威文件")
    for p in found:
        stamp = datetime.datetime.fromtimestamp(p.stat().st_mtime)
        print(f"  {stamp:%Y-%m-%d %H:%M}  {p}")
    red = max(0, len(found) - 1)
    print(f"结论：{'只有一份，没分叉' if not red else f'{len(found)} 份并存，红 {red} 项——留一份当权威，其余移进 _归档 或整份封存'}")
    return red


def selftest(layout=None):
    """阴性自测：造一个必坏的目录，七条判据必须全部命中——判据抓不住就是尺子在空转。"""
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "我的工作区"
        (ws / "01-文献PDF").mkdir(parents=True)
        (ws / "01-文献PDF" / "我的论文进度.md").write_text("x", encoding="utf-8")
        (ws / "09-导师沟通记录").mkdir()
        (ws / "09-导师沟通记录" / "我的论文进度.md").write_text("x", encoding="utf-8")
        (ws / "01-文献PDF" / "总览.md").write_text("x", encoding="utf-8")
        (ws / "01-文献PDF" / "总览35篇.md").write_text("x", encoding="utf-8")
        (ws / "01-文献PDF" / "题录.json").write_text("{}", encoding="utf-8")
        (ws / "01-文献PDF" / "目录.md").write_text("", encoding="utf-8")
        (ws / "01-文献PDF" / "README.md").write_text("x", encoding="utf-8")   # 第二个入口
        (ws / "01-文献PDF" / "_本次核验.py").write_text("#", encoding="utf-8")
        (ws / "01-文献PDF" / "原文").mkdir()                      # 空壳
        (ws / "99-自由发挥").mkdir()                              # LAYOUT 之外
        (ws / "02-问卷数据").mkdir()
        (ws / "02-问卷数据" / "答卷.csv").write_text("a", encoding="utf-8")   # 无目录.md
        got = {h[1] for h in audit(ws, layout)}
        dup = copies(ws.parent)          # 跨副本那条也得抓到自测里这两份卡
    want = {"R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"}
    miss = want - got
    print(f"自测：判据命中 {sorted(got)}；跨副本另抓到 {dup} 项")
    print(f"结论：{'八条全咬住，跨副本也咬住' if not miss and dup else '没咬住 ' + str(sorted(miss)) + '，或跨副本为 0——尺子在空转'}")
    return 1 if (miss or not dup) else 0


def main():
    ap = argparse.ArgumentParser(description="材料区目录体检（只读）")
    ap.add_argument("target", nargs="?", help="材料区目录，如 我的工作区")
    ap.add_argument("--strict", action="store_true", help="有红项时返回非零")
    ap.add_argument("--layout", help="setup_workspace.py 的路径（草稿期用；落仓后默认即可）")
    ap.add_argument("--selftest", action="store_true", help="判据的阴性自测")
    ap.add_argument("--copies", metavar="父目录", help="跨副本清点权威文件（一台机器上有多份副本时用）")
    a = ap.parse_args()
    if a.copies:
        return 1 if copies(a.copies) else 0
    if a.selftest:
        return selftest(a.layout)
    if not a.target:
        print("要给一个目录，或用 --selftest", file=sys.stderr)
        return 2
    root = Path(a.target)
    if not root.is_dir():
        print(f"目录不存在：{root}", file=sys.stderr)
        return 2
    return 1 if (report(root, audit(root, a.layout)) and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
