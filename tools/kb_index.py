#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文献知识库清点与对账（v1.99，菜单第 28 项）。

它回答一个此前全包没人能回答的问题：**本地到底有哪些文献、各自读到哪一层、哪张卡还缺证据**。
`core/evidence-rigor.md` 第三节写"本轮要用请重新读一次文件"，可 AI 与学生都不知道该读哪个文件——
本工具就是那份清单，并且顺手与 v1.98 的原文台账对账（取了全文却没建卡 = 白取）。

三件事：
  1. **分档清点**：按"我读到哪一层"与"学生核对过没有"分类计数——摘要级与 AI 起草的卡**不能**当已核实证据。
  2. **缺项点名**：逐张卡检查引用四要素与取证栏，缺哪格报哪个文件第几行（只报位置，不替你补一个字）。
  3. **对账**：`原文获取台账.md` 里标 `已获取/可获取` 的篇目、`01-文献PDF/原文/` 里的 PDF，
     库里有没有对应的卡；反过来卡里写的"本地原文"文件在不在。**两边都查，缺哪边补哪边。**

**只读**：默认只打印。加 `--write` 才把索引写成 `知识库索引.md`（该文件由本工具生成，不参与对账）。
用法：
  python tools/kb_index.py                  # 打印清点结果
  python tools/kb_index.py --write          # 顺手把索引存进库里（换对话时交给 AI）
  python tools/kb_index.py --strict         # 有坏链或缺四要素的卡时返回失败码（给自检串用）
"""
import argparse
import re
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 默认 GBK，遇 ⚠ ↔ ² 会崩）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
NULLS = ("", "无", "原文未报告", "未核验", "未声明")
# 一张合格卡必须有这几样。缺项不是格式洁癖：缺"位置"就没法回原文，缺"读到哪一层"就可能拿摘要下结论。
REQUIRED = (("作者与年份", "谁（作者+年份）"), ("题名", "哪句的出处（题名）"),
            ("我读到哪一层", "读的是什么材料"), ("逐字原文", "逐字原文"),
            ("**位置**", "位置（节/表/页）"), ("学生核对过没有", "谁写进库的"))
SCOPE = re.compile(r"我读到哪一层.*?`([^`]+)`")
CHECKED = re.compile(r"学生核对过没有.*?`([^`]+)`")
LOCAL = re.compile(r"本地原文在哪.*?`([^`]+)`")


def cards_of(kb: Path):
    out = []
    for p in sorted(kb.rglob("*.md")):
        if p.name == "知识库索引.md":
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        lines = txt.splitlines()
        got = {}
        for pat, key in ((SCOPE, "scope"), (CHECKED, "checked"), (LOCAL, "local")):
            for ln in lines:
                m = pat.search(ln)
                if m:
                    got[key] = m.group(1)
                    break
        miss = [name for token, name in REQUIRED if token not in txt]
        # 空白模板自带的示例行也算"有"，所以再确认有没有真填进去的证据块（> 开头的引用行）
        if not any(ln.lstrip().startswith(">") for ln in lines):
            miss.append("逐字原文（没有引用块，只有模板示例）")
        out.append({"p": p, "lines": lines, "scope": got.get("scope", "未声明"),
                    "checked": got.get("checked", "未声明"), "local": got.get("local", ""),
                    "miss": miss})
    return out


def ledger_of(ws: Path):
    """读 v1.98 的原文台账，取出"有没有全文"那一列，以及原文目录里实际躺着的文件。"""
    have = {}
    rep = ws / "01-文献PDF" / "原文获取台账.md"
    if rep.is_file():
        for ln in rep.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ln.startswith("|") and ln.count("|") >= 3:
                cells = [c.strip() for c in ln.strip("|").split("|")]
                st = " ".join(cells)
                if "已获取" in st or "可获取" in st:
                    have[cells[0]] = st[:40]
    src = ws / "01-文献PDF" / "原文"
    if src.is_dir():
        for f in sorted(src.iterdir()):
            if f.is_file() and f.suffix.lower() in (".pdf", ".html", ".xml", ".txt"):
                have.setdefault(f.name, "原文目录里有这个文件")
    return have


def main():
    ap = argparse.ArgumentParser(description="文献知识库清点与对账（只读；--write 才落索引）")
    ap.add_argument("--kb", default="我的工作区/10-知识库", help="库目录")
    ap.add_argument("--write", action="store_true", help="把索引写进库（文件名固定为 知识库索引.md）")
    ap.add_argument("--strict", action="store_true", help="有坏链或缺项时返回失败码")
    a = ap.parse_args()
    kb = (ROOT / a.kb) if not Path(a.kb).is_absolute() else Path(a.kb)
    ws = kb.parent          # 库放在 `我的工作区/10-知识库/`，它的上一层就是学生工作区，原文台账与原文目录都在那儿
    print("=" * 66)
    print("文献知识库清点　　库：%s" % kb)
    print("=" * 66)
    if not kb.is_dir():
        print("✗ 还没有这个库。跑菜单第 22 项补齐工作区（会生成 `10-知识库/`），")
        print("  再把 `templates/文献卡片模板.md` 复制成第一张卡开始填。建库指南：workflows/knowledge-base-setup.md")
        return 1
    cs = cards_of(kb)
    if not cs:
        print("⚠ 库里一张卡都没有。卡片是**一篇一个文件**，命名 `L01_作者年份_短名.md`。")
        return 1 if a.strict else 0
    tiers, checks = {}, {}
    for c in cs:
        tiers[c["scope"]] = tiers.get(c["scope"], 0) + 1
        checks[c["checked"]] = checks.get(c["checked"], 0) + 1
    print("\n一、共 %d 张卡。按“我读到哪一层”分档（决定能不能拿来下结论）：" % len(cs))
    for k in sorted(tiers, key=lambda x: -tiers[x]):
        ok = "可作证据" if k == "全文PDF" else "只能当线索，不得输出结论级断言"
        print("   · %-10s %2d 张　← %s" % (k, tiers[k], ok))
    print("   按“学生核对过没有”分：", "　".join("%s %d 张" % (k, v) for k, v in sorted(checks.items())))
    print("   ⚠ 提醒：`AI 起草`/`还没比对` 的卡与 AI 自己的印象同源，**不能当三查里的独立第二源**。")

    bad_local, incomplete = [], []
    for c in cs:
        if c["local"] not in NULLS and not (ROOT / c["local"]).exists():
            bad_local.append((c, "卡里写的本地原文不存在：%s" % c["local"]))
        if c["miss"]:
            incomplete.append((c, "、".join(c["miss"])))
    print("\n二、缺项与坏链（只报位置，不替你补一个字——补上去的数字是编的）：")
    if not incomplete and not bad_local:
        print("   ✅ %d 张卡四要素齐、原文路径都还在。" % len(cs))
    for c, why in (incomplete + bad_local):
        print("   · %s：%s" % (c["p"].name, why))

    have = ledger_of(ws)
    named = " ".join(c["p"].name for c in cs)
    orphan = [k for k in have if k.split(".")[0][:12] not in named.replace("_", " ")]
    print("\n三、与原文台账对账（v1.98 第 26/27 项的产物）：")
    print("   拿得到全文的篇目 %d 个；库里卡 %d 张。" % (len(have), len(cs)))
    if orphan:
        print("   这些原文有文件/有记录、但库里还没有对应的卡（读了没记 = 下次还得重读）：")
        for k in orphan[:12]:
            print("     · %s" % k)
        if len(orphan) > 12:
            print("     …还有 %d 个" % (len(orphan) - 12))
    lines = ["# 知识库索引", "", "> 由 `tools/kb_index.py` 生成，**别手改**；改卡片后重跑菜单第 28 项。",
             "> 用途：换对话/换 AI 时把本文件与进度卡一起交出去，对方立刻知道你核过哪些文献、核到什么程度。", "",
             "| 卡片 | 读到哪一层 | 学生核对 | 本地原文 | 缺项 |", "|---|---|---|---|---|"]
    for c in cs:
        lines.append("| %s | %s | %s | %s | %s |" % (c["p"].name, c["scope"], c["checked"],
                                                     c["local"] or "无", "、".join(c["miss"]) or "无"))
    if a.write:
        out = kb / "知识库索引.md"
        out.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")   # 本包 Windows 侧统一 CRLF
        print("\n✅ 索引已写入 %s（只覆盖这一个由本工具生成的文件，没动任何卡片）" % out.relative_to(ROOT))
    else:
        print("\n提示：加 `--write` 可把上面这张表存成库里的 `知识库索引.md`。")
    n_bad = len(incomplete) + len(bad_local)
    if a.strict and n_bad:
        print("\n--strict：有 %d 处缺项/坏链，返回失败码。" % n_bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
