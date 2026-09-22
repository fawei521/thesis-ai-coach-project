#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CHANGELOG 生成器：把"每版手写长文＋攒够就手工搬"换成"一版一个文件＋按预算自动滚动"。

**维护者工具**：不进图形菜单、学生不需要跑（`case_26` 认这一行——带 `__main__` 的 tools 脚本
要么挂在菜单上，要么写明是维护者工具，两者都不占＝判红）。

正文来源（都在 `维护档案/CHANGELOG/`，该目录被 `.gitattributes` export-ignore，**不进发布包**）：
    00-头部.md  01-索引.md  02-维护决定.md  03-详情前言.md      ← 四段静态/半静态内容，原样拼
    版本详情/v1.99.md …                                        ← 一版一个文件；首行 `**vX 主题**`，
                                                                  次行 `> 发布：YYYY-MM-DD`
包内 `CHANGELOG.md` 是**构建产物**：索引（缺的行会按详情文件自动补）＋ 最近若干版详情，
留几版由预算决定——默认拼到 ≤300 行为止，超出的老版本自动"只在仓库里"，**没有人再搬**。

用法：
    python tools/changelog_build.py              # 检查：CHANGELOG.md 是否等于生成结果（不同步退出码 1）
    python tools/changelog_build.py --write      # 重拼并写回（同时 upsert 索引）
    python tools/changelog_build.py --keep-all   # 拼回全部详情（搬家验收用）
    python tools/changelog_build.py --budget 300 # 换预算

为什么这么改（三条实测病灶）：加一版要动四处、手工搬运最贵；`ROADMAP.md` 里"见 CHANGELOG v1.64"
这类引用早就指向被搬走的正文而没人发现；两个会话同时发版会抢同一个文件。
"""
import re
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 控制台默认 GBK，⚠ ／ ≤ 这类字符会崩）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "维护档案" / "CHANGELOG"
OUT = ROOT / "CHANGELOG.md"
PARTS = ("00-头部.md", "01-索引.md", "02-维护决定.md", "03-详情前言.md")
DEFAULT_BUDGET = 300


def ver_key(v):
    """版本号排序键：v1.99 → (1,99,0)；带尾缀的（v1.56.4 之类）按数字段补齐。"""
    nums = re.findall(r"\d+", v)
    return tuple([int(x) for x in nums] + [0] * (4 - len(nums))) if nums else (0,)


def read(path):
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n").rstrip("\n")


def load_details():
    """返回 [(版本, 主题, 日期, 正文行列表)]，按版本倒序。"""
    d = SRC / "版本详情"
    out = []
    for p in sorted(d.glob("*.md"), key=lambda x: ver_key(x.stem), reverse=True):
        lines = read(p).split("\n")
        m = re.match(r"^\*\*(v[\d.]+)\s+(.*)\*\*$", lines[0].strip())
        if not m:
            raise SystemExit(f"[停止] {p.name} 首行不是 `**vX 主题**`：{lines[0][:40]}")
        date = ""
        body = lines[1:]
        if len(lines) > 1 and lines[1].startswith("> 发布："):
            date = lines[1][len("> 发布："):].strip()
            body = lines[2:]
        out.append((m.group(1), m.group(2), date, body))
    return out


def upsert_index(index_lines, details):
    """详情文件里有、索引表里没有的版本 → 按版本序补一行。返回（新索引行, 补了几行）。"""
    have = {m.group(1) for ln in index_lines for m in [re.match(r"^\| \*\*(v[\d.]+)\*\*", ln.strip())] if m}
    added = 0
    for ver, subj, date, _ in details:
        if ver in have:
            continue
        row = "| **%s** | %s | %s | 见下方详情 |" % (ver, date or "—", subj)
        nums = [i for i, ln in enumerate(index_lines) if ln.startswith("| **v")]
        at = next((i for i in nums if ver_key(index_lines[i].split("**")[1]) < ver_key(ver)),
                  (nums[-1] + 1) if nums else len(index_lines))
        index_lines.insert(at, row)
        added += 1
    return index_lines, added


def build(keep_all=False, budget=DEFAULT_BUDGET):
    """返回 (包内文本, 保留几版, 索引补了几行, 新的索引段文本)。"""
    parts = [read(SRC / p).split("\n") for p in PARTS]
    details = load_details()
    parts[1], added = upsert_index(parts[1], details)      # 01-索引.md
    prefix = sum(len(p) for p in parts) + (len(parts) - 1)  # 段间各一个空行
    kept, cur = [], prefix
    for i, (ver, subj, date, body) in enumerate(details):
        if not keep_all and i and cur + len(body) + 2 > budget:
            print("  滚动出去：%s 及更老的 %d 版只在仓库档案里（包内 %d 行／预算 %d）"
                  % (ver, len(details) - i, cur, budget))
            break
        kept.append((ver, subj, date, body))
        cur += len(body) + 2
    text = []
    for k, p in enumerate(parts):
        text += p
        if k < len(parts) - 1:
            text.append("")
    for ver, subj, date, body in kept:
        text += ["**%s %s**" % (ver, subj)] + body + [""]
    while text and text[-1] == "":
        text.pop()
    text += archive_section(details, [v for v, _, _, _ in kept])
    return ("\n".join(text) + "\n", len(kept), added, "\n".join(parts[1]) + "\n")


def archive_section(details, kept_vers):
    """把"更早的详情在哪个档案文件"这一段**从磁盘现算**，不再手写。
    以前这行指针埋在某个版本的详情块里，一滚出去就成孤儿（`case_15` 当场抓到）——所以它必须是生成物。"""
    lines = ["", "", "## 历史详情档案（维护者留档，不随发布包分发）", ""]
    for p in sorted((ROOT / "维护档案").glob("CHANGELOG-历史详情-*.md")):
        # 指针必须写**完整仓库路径**：consistency_check 的"包外文件"豁免按 `维护档案/` 前缀认，
        # 裸文件名在开发树里靠"全项目同名兜底"能过，到学生副本里就成假悬空（2026-09-22 实测）。
        lines.append("- `%s` — %s" % (p.relative_to(ROOT).as_posix(),
                                      p.read_text(encoding="utf-8").split("\n")[0].lstrip("# ")))
    out = [v for v, _, _, _ in details if v not in kept_vers]
    lines.append("- 一版一个文件的近期详情在 `维护档案/CHANGELOG/版本详情/`；当前未拼进本文件的：%s"
                 % ("、".join(out) if out else "无"))
    return lines


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="生成包内 CHANGELOG.md（正文来源在 维护档案/CHANGELOG/）")
    ap.add_argument("--write", action="store_true", help="写回 CHANGELOG.md（并按需补索引行）")
    ap.add_argument("--check", action="store_true", help="只比对同步状态（默认行为，退出码 0=同步）")
    ap.add_argument("--keep-all", action="store_true", dest="keep_all",
                    help="把全部详情拼回去，只用于搬家核对，不参与同步判定")
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                    help="包内详情区的行数预算（默认 %d）" % DEFAULT_BUDGET)
    a = ap.parse_args(argv)
    keep_all, budget = a.keep_all, a.budget
    want, kept, added, index_text = build(keep_all, budget)
    have = OUT.read_bytes().decode("utf-8").replace("\r\n", "\n") if OUT.exists() else ""
    if a.write:
        if added:
            print("  索引自动补了 %d 行（取自详情文件首两行）→ 写回 01-索引.md" % added)
            (SRC / "01-索引.md").write_bytes(index_text.replace("\n", "\r\n").encode("utf-8"))
        OUT.write_bytes(want.replace("\n", "\r\n").encode("utf-8"))
        print("已生成 CHANGELOG.md：%d 行、包内 %d 版详情" % (len(want.split("\n")) - 1, kept))
        return 0
    if keep_all:
        # --keep-all 是搬家审计用的：只报"全拼回去长什么样"，不参与同步判定
        same = want.rstrip() == have.rstrip()
        print("全拼回去：%d 行、%d 版详情（与现文件%s）——这条只用于搬家核对"
              % (len(want.split("\n")) - 1, kept, "相同" if same else "不同：现文件按预算少拼了老版本"))
        return 0
    if want.rstrip() != have.rstrip():
        a, b = want.split("\n"), have.split("\n")
        first = next((i for i in range(max(len(a), len(b))) if (a[i:i + 1] != b[i:i + 1])), 0)
        print("不同步：共 %d 行 vs %d 行，第一处在第 %d 行" % (len(a) - 1, len(b) - 1, first + 1))
        print("  应得：%s" % (a[first] if first < len(a) else "<无>")[:90])
        print("  现在：%s" % (b[first] if first < len(b) else "<无>")[:90])
        return 1
    print("同步：CHANGELOG.md == 生成结果（%d 行、包内 %d 版详情）" % (len(want.split("\n")) - 1, kept))
    return 0


if __name__ == "__main__":
    sys.exit(main())
