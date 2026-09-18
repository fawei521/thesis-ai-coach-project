#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大纲 → .pptx 生成器
==================
把一份**纯文本大纲**渲染成真正的 PowerPoint 文件。内容（讲什么、怎么讲）由你和 AI 一起填，
本工具只做机械排版，不替你写一个字——所以它不碰 CONSTITUTION 的"不代写"红线。

大纲格式（严格但直观，写错会中文报错并指出行号，不会静默少页）：

    # 开题报告
    副标题：孤独感与反刍思维的链式中介作用
    汇报人：XXX        专业：应用心理学        指导教师：XXX
    比例：16:9

    ## 第1页：选题背景与意义
    > 讲稿：这一页说清楚"为什么值得做"，30 秒。
    - AI 陪伴普及，但青少年用得越多是否越孤独
    - 知网"AI情感依赖+青少年+自伤"三词组合 0 篇
      - 这是空白，也是本研究的出发点        ← 行首两个空格 = 二级
    | 变量 | 量表 | 题数 |
    | X | AIED | 5 |
    ![图1 研究技术路线](我的工作区/02-开题报告/模型图.png)

    ## 第2页：研究问题与假设     ← 只有一行标题的页 = 节标题页
规则：
  - `#` 一级 = 封面标题；`## 第N页：标题` = 每页开始（也接受 `## 标题`，自动编号）。
  - `-` 开头 = 要点，缩进 2 空格升一级（最多 4 级）。
  - `|` 开头的连续行 = 表格，第一行当表头。
  - `![题注](路径)` = 整页图片（技术路线图 / 模型图），只吃 PNG。
  - `> 讲稿：…` 或 `> 备注：…` = 写进**演讲者备注**，不会出现在幻灯片上。
  - 段落行（不以这几种符号开头的非空行）会作为普通要点，不会丢。
  - `比例：16:9` / `比例：4:3` 决定页面尺寸，默认 16:9。

用法：
  python tools/outline_to_ppt.py 我的开题大纲.md
  python tools/outline_to_ppt.py 大纲.md -o 我的工作区/07-答辩材料/答辩.pptx

依赖 python-pptx（见 requirements.txt）。未安装时给出安装提示并退回"大纲本身即可用"，
退出码 1，不会崩在 ImportError 上。
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pptx_writer as W  # noqa: E402

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与其他工具同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_META = re.compile(r"^\s*(副标题|汇报人|专业|指导教师|日期|比例|备注)\s*[：:]\s*(.*)$")
_PAGE = re.compile(r"^##\s+(?:第\s*(\d+)\s*页\s*[：:，、\s]\s*)?(.+?)\s*$")
_IMG = re.compile(r"^!\[(?P<cap>[^\]]*)\]\((?P<path>[^)]+)\)\s*$")
_NOTE = re.compile(r"^>\s*(?:讲稿|备注|notes?)\s*[：:]?\s*(.*)$", re.I)


def die(msg, code=1):
    print(f"✗ {msg}")
    sys.exit(code)


def parse_outline(text, src_name=""):
    """把大纲切成 [封面信息, [页,…]]；每页 = dict(kind,title,items,table,image,notes)。"""
    where = (src_name + ":") if src_name else ""
    meta = {"title": "", "subtitle": "", "presenter": "", "major": "", "advisor": "",
            "date": "", "ratio": "16:9"}
    pages = []
    cur = None
    lines = text.splitlines()
    in_comment = False

    def new_page(title):
        return {"kind": "bullets", "title": title.strip(), "items": [],
                "table": [], "image": None, "caption": "", "notes": []}

    for ln, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        # <!-- ... --> 是模板写给"人"看的说明，永远不该变成幻灯片内容
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if line.lstrip().startswith("<!--"):
            if "-->" not in line:
                in_comment = True
            continue
        line = re.sub(r"<!--.*?-->", "", line).rstrip()
        if not line.strip():
            continue
        if line.startswith("# ") and not line.startswith("## "):
            if meta["title"]:
                die(f"{where}第{ln}行：出现第二个 `# 一级标题`，封面标题只能有一个。")
            meta["title"] = line[2:].strip()
            continue
        m = _PAGE.match(line)
        if m:
            cur = new_page(m.group(2))
            pages.append(cur)
            continue
        if not line.lstrip().startswith(("-", "|", "!", ">")) and _META.match(line):
            k, v = _META.match(line).group(1), _META.match(line).group(2).strip()
            if pages:
                pass                              # 页内的"备注：x"按普通要点处理，见下
            else:
                if k == "比例":
                    if v not in ("16:9", "4:3"):
                        die(f"{where}第{ln}行：比例只能写 16:9 或 4:3，读到「{v}」。")
                    meta["ratio"] = v
                elif k == "副标题":
                    meta["subtitle"] = v
                elif k in ("汇报人", "专业", "指导教师", "日期"):
                    meta[{"汇报人": "presenter", "专业": "major",
                          "指导教师": "advisor", "日期": "date"}[k]] = v
                continue
        if cur is None:
            if line.lstrip().startswith(">"):
                continue        # 首页之前的引用行 = 模板写给学生的使用说明，不上幻灯片
            die(f"{where}第{ln}行出现在第一页（`## …`）之前，且不是封面信息：{line[:40]}\n"
                f"  封面写 `# 标题` + `副标题：…`，正文每页以 `## 第N页：标题` 开头。")
        nm = _NOTE.match(line)
        if nm:
            cur["notes"].append(nm.group(1).strip())
            continue
        if line.lstrip().startswith(">"):
            continue        # 非"讲稿："的引用行是模板说明，不上幻灯片也不当要点
        im = _IMG.match(line.strip())
        if im:
            cur["image"] = im.group("path").strip()
            cur["caption"] = im.group("cap").strip()
            cur["kind"] = "picture"
            continue
        if line.strip().startswith("!["):
            die(f"{where}第{ln}行图片语法不完整：{line.strip()[:60]}\n"
                f"  必须是 ![题注](路径.png) —— 缺了圆括号里的路径。"
                f" 不会替你猜，也不会把它当普通文字排版。")
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells) and any(cells):
                continue                            # markdown 的 |---|---| 分隔行，跳过
            cur["table"].append(cells)
            cur["kind"] = "table"
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith(("- ", "* ", "· ")):
            body = stripped[2:].strip()
        elif stripped.startswith(("-", "*")):
            body = stripped[1:].strip()
        else:
            body = stripped                                   # 裸行也算一条要点，不丢内容
        if not body:
            continue
        cur["items"].append((min(indent // 2, 4), body))
    if not pages:
        die(f"{where}没找到任何一页。正文每页请以 `## 第N页：标题` 开头。")
    if meta["title"]:
        pages.insert(0, {"kind": "cover", "title": meta["title"], "items": [],
                         "table": [], "image": None, "caption": "",
                         "notes": ["封面：报题目与一句话动机即可，不要念 PPT。"],
                         "meta": meta})
    return meta, pages


def build(meta, pages, out_path):
    pr = W.Presentation(title=meta["title"] or "报告",
                        author=" / ".join(x for x in (meta["presenter"],) if x) or "",
                        ratio=meta["ratio"])
    made = {"cover": 0, "bullets": 0, "section": 0, "table": 0, "picture": 0}
    for i, pg in enumerate(pages, 1):
        note = "\n".join(pg["notes"]) or ""
        kind = pg["kind"]
        if kind == "cover":
            m = pg["meta"]
            sub_bits = [x for x in (m["subtitle"],
                                    "  ".join(y for y in (
                                        f"汇报人：{m['presenter']}" if m["presenter"] else "",
                                        f"专业：{m['major']}" if m["major"] else "",
                                        f"指导教师：{m['advisor']}" if m["advisor"] else "",
                                        m["date"]) if y)) if x]
            pr.add_title(m["title"], "    ".join(sub_bits), notes=note)
            made["cover"] += 1
        elif kind == "table":
            hdr, *rows = pg["table"]
            pr.add_table(pg["title"], hdr, rows, notes=note,
                         font_sz=14 if len(rows) <= 8 else 12)
            made["table"] += 1
        elif kind == "picture":
            p = Path(pg["image"])
            if not p.is_absolute():
                p = Path.cwd() / p
            if not p.exists():
                cand = Path("我的工作区") / pg["image"]
                p = cand if cand.exists() else p
            if not p.exists():
                die(f"第{i}页的图片找不到：{pg['image']}\n"
                    f"  技术路线图/模型图请先生成（菜单第10项或 tools/chart_generator.py），"
                    f"再回填这个路径。")
            if p.suffix.lower() != ".png":
                die(f"第{i}页只支持 PNG，读到 {p.suffix}。"
                    f" 用 chart_generator 导出时加 --format png，或先转成 PNG。")
            pr.add_picture(pg["title"], str(p), caption=pg["caption"], notes=note)
            made["picture"] += 1
        elif not pg["items"]:
            pr.add_section(pg["title"], notes=note)
            made["section"] += 1
        else:
            long_any = max(len(t) for _, t in pg["items"]) > 60
            flat = [(lvl, t) for lvl, t in pg["items"]]
            pr.add_bullets(pg["title"], flat, notes=note)
            made["bullets"] += 1
            if long_any:
                print(f"  ⚠ 第{i}页「{pg['title']}」有超过 60 字的要点——"
                      f"幻灯片是提词的，长句请放进备注当讲稿。")
    saved = pr.save(out_path)
    return saved, made


def main():
    ap = argparse.ArgumentParser(description="把大纲 .md 渲染成 .pptx（不代写内容）")
    ap.add_argument("outline", nargs="?", help="大纲 markdown 文件")
    ap.add_argument("-o", "--output", default="", help="输出 .pptx 路径（默认同名同目录）")
    ap.add_argument("--dry-run", action="store_true", help="只校验大纲并打印分页结构，不出文件")
    args = ap.parse_args()
    if not args.outline:
        ap.print_help()
        sys.exit(1)
    src = Path(args.outline)
    if not src.exists():
        die(f"找不到大纲文件：{args.outline}")
    if not W.available():
        die(f"生成 .pptx 需要 python-pptx，请先执行：{W.INSTALL_HINT}\n"
            f"  不想装也可以：把 {src.name} 直接投屏当提纲用，内容是完整的。")
    try:
        text = src.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = src.read_text(encoding="gb18030")
        except UnicodeDecodeError:
            die(f"{src.name} 编码无法识别，请另存为 UTF-8。")
    meta, pages = parse_outline(text, src.name)
    print(f"解析到 {len(pages)} 页（封面{'有' if meta['title'] else '无'}，"
          f"页面比例 {meta['ratio']}）")
    if args.dry_run:
        for i, pg in enumerate(pages, 1):
            bits = []
            if pg["items"]:
                bits.append(f"要点{len(pg['items'])}")
            if pg["table"]:
                bits.append(f"表格{len(pg['table'])}行")
            if pg["image"]:
                bits.append("图片")
            if pg["notes"]:
                bits.append(f"讲稿{len(pg['notes'])}条")
            print(f"  {i:>2}. [{pg['kind']:<7}] {pg['title'][:32]:<34} {'、'.join(bits) or '（空页）'}")
        print("大纲校验通过。")
        return
    out = Path(args.output) if args.output else src.with_suffix(".pptx")
    saved, made = build(meta, pages, out)
    print("已生成：" + str(saved))
    print("  " + "  ".join(f"{k}={v}" for k, v in made.items() if v))
    print("红线：以上是按你的大纲排版的**你自己的内容**；答辩前请把每页数字与"
          "开题报告正文逐一核对，工具不替你判断对错。")


if __name__ == "__main__":
    main()
