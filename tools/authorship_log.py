#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写作留痕：给草稿记一行"什么时候、哪个文件、多少字、内容指纹是什么"。
用法：python tools/authorship_log.py 我的工作区/06-论文正文/讨论_第二稿.md [--note "重写中介那段"]
      python tools/authorship_log.py --show          # 只看现有留痕
      python tools/authorship_log.py A.md --compare B.md   # 两份稿子之间真实改了多少行
**它只往留痕文件追加一行，绝不改动你的草稿**（草稿字节与时间戳都不碰）。
留痕的用处是**证明这篇论文是一步步写出来的**——学校 AIGC 检测有误伤时，过程证据比改句式管用。
"""
import argparse
import datetime
import hashlib
import re
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 控制台默认 GBK，遇 ⚠ ↔ 等字符会直接崩；门禁与 AI 都以管道读输出）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DEF_LOG = ROOT / "我的工作区" / "06-论文正文" / "我的写作留痕.md"
CJK = re.compile(r"[\u4e00-\u9fff]")
HEAD = "# 我的写作留痕（自动追加，别手改已记下的行）\n\n> 由菜单第 25 项或 `tools/authorship_log.py` 追加。" \
       "每一行都是「我当时改成这样」的一份证据：时间、文件、字数、内容指纹。\n" \
       "> 指纹只取 SHA-256 前 12 位，够用且看不出内容；换机器重算也一样。\n\n" \
       "| 时间 | 文件 | 汉字数 | 与上次差 | 内容指纹 | 备注 |\n|---|---|---:|---:|---|---|\n"


def read_text(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def prior_count(log):
    """留痕里上一行的汉字数，用来算"比上次多写/少写了多少字"。"""
    if not log.is_file():
        return None
    rows = [l for l in log.read_text(encoding="utf-8").splitlines() if l.startswith("| 20") or l.startswith("| 19")]
    if not rows:
        return None
    cells = [c.strip() for c in rows[-1].split("|")]
    for c in cells:
        if re.fullmatch(r"\d+", c):
            return int(c)
    return None


def diff_lines(a, b):
    import difflib
    la, lb = read_text(a).splitlines(), read_text(b).splitlines()
    ch = sum(1 for l in difflib.unified_diff(la, lb, n=0, lineterm="")
             if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    return ch, len(la), len(lb)


def main(argv=None):
    ap = argparse.ArgumentParser(description="写作留痕：记一行过程证据，绝不动草稿")
    ap.add_argument("file", nargs="?", help="要留痕的草稿（.md/.txt）")
    ap.add_argument("--note", default="", help="一句话备注：这次改了什么")
    ap.add_argument("--log", default=str(DEF_LOG), help="留痕文件路径（默认工作区 06-论文正文 下）")
    ap.add_argument("--show", action="store_true", help="只打印现有留痕，不写任何东西")
    ap.add_argument("--compare", help="与另一份草稿逐行比对，报真实改动的行数")
    a = ap.parse_args(argv)
    log = Path(a.log) if Path(a.log).is_absolute() else ROOT / a.log
    if a.show:
        print(log.read_text(encoding="utf-8") if log.is_file() else "还没有留痕：%s\n跑一句 python tools/authorship_log.py 你的稿子.md 就有了。" % a.log)
        return 0
    if not a.file:
        print("要留痕就得给出文件路径。（只想看已有留痕：加 --show）")
        return 2
    f = Path(a.file) if Path(a.file).is_absolute() else (
        (ROOT / a.file) if (ROOT / a.file).is_file() else Path.cwd() / a.file)
    if not f.is_file():
        print("读不到文件：%s\n先确认路径；不确定就把文件从文件夹拖进这个窗口。" % a.file)
        return 2
    text = read_text(f)
    before = f.stat().st_mtime, f.stat().st_size
    chars = len(CJK.findall(text))
    prev = prior_count(log)
    delta = "%+d" % (chars - prev) if prev is not None else "首次"
    fp = digest(text)
    note = a.note.strip().replace("|", "／") or "—"
    row = "| %s | %s | %d | %s | `%s` | %s |\n" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), f.name, chars, delta, fp, note)
    log.parent.mkdir(parents=True, exist_ok=True)
    first = not log.is_file()
    with open(log, "a", encoding="utf-8", newline="\r\n") as fh:
        if first:
            fh.write(HEAD)
        fh.write(row)
    if (f.stat().st_mtime, f.stat().st_size) != before:
        print("异常：草稿的时间戳/大小变了，请立即检查（本工具设计上不写草稿）")
        return 1
    print("已记一行留痕：%s（%d 汉字 · 指纹 %s）→ %s" % (f.name, chars, fp, log.relative_to(ROOT) if log.is_relative_to(ROOT) else log))
    if a.compare:
        g = Path(a.compare) if Path(a.compare).is_absolute() else ROOT / a.compare
        if not g.is_file():
            print("要比对的文件读不到：%s" % a.compare)
            return 2
        ch, la, lb = diff_lines(g, f)
        print("与「%s」相比：改动 %d 行（那份 %d 行 → 这份 %d 行）" % (a.compare, ch, la, lb))
        print("这类「两份稿子之间真实改了多少行」的记录，比句式打扮更能说明是谁写的。")
    print("提醒：留痕是给自己看、必要时给学校看的**过程证据**，不是检测工具——它不测 AIGC 率。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
