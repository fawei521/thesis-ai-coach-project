#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开局集之外的「当轮叠量」探针：命中才读的那几份，真被抽进来时有多大（只读，不写盘）。

**为什么有这个文件**：2026-10-03 把开局必读改成三层之后，`case_16` 那道总量闸只管**层一**（现抽 START 第二步声明的那四份＋START 自己）。
于是有个问题没人量过：「命中才读」听起来比「每轮在场」省，但它省的是**第一轮**，不是**最重的那一轮**——
一轮里同时命中几份层二时，抽进来的字节可能比旧的全读开局集还大（复核报告里那个 97,891 B 的推算）。要把它变成能判定的事，先得有数，所以这里量六件事：
  ① 层一现量（规则同 `case_16.py:47-55`，两边不许各写一套）；② 层二每份的触发条件与现量（从 START 层二段落的「→ 路径」现抽，不抄清单）；
  ③ `core/coaching-protocol.md` 第十节那份**每轮默查清单**里，多少条把判据外包给了非层一文件；
  ④ 分节字节：设计写的是「读那一节」，机器只能整份抽——所以量出「一节多大／整份多大」这个比值；⑤ 轮型叠量：按一张**摆在明面上的输入表**算四种轮型各抽进来多少字节；
  ⑥ 按节取的**声明层要求读入量**：指向里点名了「第几节」就只算那一节——它只回答"声明要求读多少"，不回答"省下多少"（后者要真做层实测）。
**能判什么**：一份文件被抽进来的字节、被多少条默查项指向、拆成按节读能少要求读入多少。
**不能判什么**：真实命中率。轮型表是人工列的问法，不是观察到的对话分布——换了这张表结论就跟着换，读数必须配「这是推演、不是实测」一起看；⑥更不能判"AI 真读了多少"——**所以 ⑥ 打出的那个差额不是省下来的字节**，2026-10-04 四格真做层实测：被要求"只读第三、四节"的落笔者为了答第 4 步要求的三问，仍把整份读了。
跑法：
    python tests/opening_overlay_probe.py            # 打 ①②③④⑤⑥
    python tests/opening_overlay_probe.py --selftest  # 尺子的阴性自测（退出码 0 才算尺子能用）
字节口径同 `tests/full_e2e.py` 的 `tx()`：读进来（通用换行，CRLF→LF）再 encode，所以这里是**归一后的字节**，与磁盘原始大小对 CRLF 文件会差一截（差值＝行数）。
"""
import argparse
import re
import sys
from pathlib import Path

# --- 输出编码守卫：无条件生效（不做 isatty 判断，理由见 case_14 的 v186 那条）---
# 中文 Windows 管道/重定向时 stdout 会退回 GBK，本文件打印的「｜」「→」「B」等字符会让它崩。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PATH_RE = re.compile(r"[A-Za-z0-9_\-./\u4e00-\u9fff]+\.(?:md|py)")
TICK_RE = re.compile(r"`([^`]+)`")
BASELINE_94528 = 94528  # 三层改造前的开局全读实测数，只在 AGENTS.md:16 有叙述、无可复跑算法


def tx(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def nbytes(rel):
    return len(tx(rel).encode("utf-8"))


def extract_layer1(start_text):
    """规则与 case_16.py:47-55 一致：从含「层一」的行起、到含「层二」的行止，收形如 1. `path` 的行。"""
    out, seen = [], False
    for ln in start_text.split("\n"):
        s = ln.strip()
        if "层一" in s:
            seen = True
        elif "层二" in s:
            break
        if seen and s[:1].isdigit() and s[1:3] == ". " and s[3:4] == "`":
            out.append(s.split("`")[1])
    return out


def extract_layer2(start_text):
    """扫「层二」到「层三」之间每个 - 项里的「→ 路径」，返回 [(触发语, 原始路径串)]。"""
    rows, seen = [], False
    for ln in start_text.split("\n"):
        s = ln.strip()
        if "层二" in s:
            seen = True
            continue
        if "层三" in s:
            break
        if not seen or not s.startswith("-"):
            continue
        trigger = s.split("→")[0].lstrip("- ").strip()
        for seg in s.split("→")[1:]:
            for span in TICK_RE.findall(seg):
                m = PATH_RE.search(span)
                if m:
                    rows.append((trigger, m.group(0)))
    return rows


def resolve(rel, source_dir="."):
    """路径怎么落地的：原样 → 就近 → 补 core/ → 全仓唯一同名。落不了返回 (None, 原因)。"""
    for cand, how in ((rel, "原样"),
                      (str(Path(source_dir) / rel), "就近"),
                      ("core/" + rel, "补 core/")):
        p = (ROOT / cand)
        if p.is_file():
            return p.relative_to(ROOT).as_posix(), how
    hits = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob(Path(rel).name)
            if p.is_file() and not p.relative_to(ROOT).as_posix().startswith(("维护档案/", "tests/.tmp"))]
    if len(hits) == 1:
        return hits[0], "按名唯一"
    return None, ("重名 %d 处" % len(hits)) if hits else "查无"


def gate_items():
    """coaching-protocol 第十节那份默查清单，逐条返回原文。"""
    tail = tx("core/coaching-protocol.md").split("## 十、", 1)
    if len(tail) < 2:
        return []
    return [ln.strip() for ln in tail[1].split("\n") if ln.strip().startswith("- [ ]")]


def outsourced(items, layer1_all):
    """每条默查项指向的非层一文件（tools/ 下的脚本不算规则文本）。"""
    out = []
    for i, item in enumerate(items, 1):
        hits = set()
        for span in TICK_RE.findall(item):
            for raw in PATH_RE.findall(span):
                real, _ = resolve(raw, "core")
                if real and real not in layer1_all and not real.startswith(("tools/", "tests/")):
                    hits.add(real)
        out.append((i, sorted(hits)))
    return out


def overlay_of(files):
    return sum(nbytes(f) for f in files if (ROOT / f).is_file())


def section_sizes(rel, pat):
    """按节切，返回 [(节标题, 归一字节)]。"""
    cur, acc, out = "(文头)", 0, []
    for ln in tx(rel).split("\n"):
        if re.match(pat, ln):
            out.append((cur, acc))
            cur, acc = ln.strip(), len((ln + "\n").encode("utf-8"))
        else:
            acc += len((ln + "\n").encode("utf-8"))
    out.append((cur, acc))
    return [(t, b) for t, b in out if b > 0]


# —— ⑤ 轮型表：这是**输入**不是结论。每型列出这一轮真会抽进来的非层一文件。
TURNS = [
    ("引导轮（讲下一步、学生交回一小块）",
     ["core/coach-rules/stage-playbook.md"]),
    ("落笔轮（往论文文件里写：开题/草稿/讲稿/卡片）",
     ["core/coach-rules/stage-playbook.md", "core/academic-style.md"]),
    ("报数轮（报论文/网页/数据库里的数，或下否定判断）",
     ["core/coach-rules/stage-playbook.md", "core/evidence-rigor.md",
      "core/literature-kb.md", "core/coach-rules/tool-rules.md"]),
    ("出成品轮（学生要 AI 直接交付一整套）",
     ["core/coach-rules/stage-playbook.md", "core/outcome-delivery.md",
      "core/academic-style.md", "core/evidence-rigor.md",
      "core/coach-rules/emergency.md", "core/skill-sourcing.md"]),
]

SECTIONS = [
    ("core/coach-rules/stage-playbook.md", r"^### "),
    ("core/coach-rules/common-errors.md", r"^### "),
    ("core/coach-rules/emergency.md", r"^### "),
    ("core/coach-rules/tool-rules.md", r"^### "),
    ("core/academic-style.md", r"^## "),
    ("core/evidence-rigor.md", r"^## "),
    ("core/literature-kb.md", r"^## "),
    ("core/outcome-delivery.md", r"^## "),
]
SEC_PAT = dict(SECTIONS)
SEC_NUMS = re.compile(r"第([一二三四五六七八九十]+)节")


def bullet_text(rel):
    """START 层二段落里指向这份文件的那一行原文（指向写在哪，节号就着落在哪）。"""
    return next((l.strip() for l in tx("START.md").split("\n")
                 if l.strip().startswith("-") and ("`%s`" % rel) in l), "")


def sec_head(title):
    m = re.match(r"^#+\s*([一二三四五六七八九十]+)、", title)
    return m.group(1) if m else ""


def section_bytes(rel, nums):
    """文头＋被点名的那些节。没点名＝整份（不许算成只读文头）。返回 (字节, 查无的节号)。"""
    if not nums:
        return nbytes(rel), []
    secs = section_sizes(rel, SEC_PAT.get(rel, r"^## "))
    have = {sec_head(t) for t, _b in secs} - {""}
    keep = set(nums)
    tot = sum(b for t, b in secs if sec_head(t) in keep or not sec_head(t))
    return tot, [n for n in nums if n not in have]


def report():
    st = tx("START.md")
    l1 = extract_layer1(st)
    l1_all = ["START.md"] + l1
    print("① 层一（现抽 START 第二步声明，口径同 case_16）")
    for f in l1_all:
        print("   %-32s %7d B" % (f, nbytes(f)))
    tot1 = overlay_of(l1_all)
    _lim = int(re.search(r"_open16 < (\d+)", tx("tests/e2e_cases/case_16.py")).group(1))  # 上限只在闸那一处定义，这里现读；抽不到就抛错，不许静默按旧数算
    _ag = nbytes("AGENTS.md")
    print("   合计 %d B＋AGENTS.md %d B = %d B（闸 %d，余 %d；AGENTS 2026-10-04 起进闸）"
          % (tot1, _ag, tot1 + _ag, _lim, _lim - tot1 - _ag))

    print("\n② 层二触发表（从 START 的「→ 路径」现抽）")
    for trig, p in extract_layer2(st):
        real, how = resolve(p, "core")
        print("   %-46s → %-34s %s %6d B" % (trig[:44], p, ("查无" if not real else how),
                                             nbytes(real) if real else 0))

    items = gate_items()
    print("\n③ 每轮默查清单把判据外包给谁（coaching-protocol 第十节，共 %d 条）" % len(items))
    outs = outsourced(items, l1_all)
    n_out = sum(1 for _, h in outs if h)
    for i, h in outs:
        if h:
            print("   [%2d] → %s" % (i, "、".join(h)))
    print("   外包判据 %d 条，层一内可判 %d 条" % (n_out, len(items) - n_out))

    print("\n④ 设计说「读那一节」，机器只能整份抽——一节到底多大")
    for f, pat in SECTIONS:
        secs = section_sizes(f, pat)
        full = nbytes(f)
        med = sorted(b for _, b in secs)[len(secs) // 2]
        print("   %-34s 整份 %6d B｜节数 %2d｜最大节 %6d B｜中位节 %6d B｜中位节占整份 %3.0f%%"
              % (f, full, len(secs), max(b for _, b in secs), med, 100.0 * med / full))
    sp = section_sizes("core/coach-rules/stage-playbook.md", r"^### ")
    print("   阶段单举：%s" % "、".join("%s %d B" % (t.replace("### 阶段", "阶段").split("：")[0], b)
                                        for t, b in sp if t.startswith("### 阶段"))[:200])

    print("\n⑤ 轮型叠量（轮型表是人列的输入，不是实测分布；这里只算 START 声明那几份，走 AGENTS 进门还要再加它那一份，见①）")
    for name, files in TURNS:
        miss = [f for f in files if not (ROOT / f).is_file()]
        ov = overlay_of(files)
        print("   %-34s %d 份 %7d B｜层一＋层二 %7d B（层一的 %.1f 倍）%s"
              % (name, len(files), ov, tot1 + ov, (tot1 + ov) / tot1,
                 ("缺文件:" + ",".join(miss)) if miss else ""))
    over = [n for n, _f in TURNS if overlay_of(_f) + tot1 > BASELINE_94528]
    print("   对照：三层改造前开局全读 %d B（AGENTS.md:16 的叙述，本仓无可复跑算法）；"
          "叠量超过它的轮型：%s" % (BASELINE_94528, "、".join(over) or "无"))

    print("\n⑥ 若指向改成按节取：节号从 START 那一处指向现抽，点了第几节就只算那一节（没点名＝仍按整份）——这一档算「声明要求读入多少」，不是省下来的字节")
    for name, files in TURNS:
        got = [(f,) + section_bytes(f, SEC_NUMS.findall(bullet_text(f))) for f in files]
        whole, cut = overlay_of(files), sum(b for _f, b, _m in got)
        miss = [(f, x) for f, _b, m in got for x in m]
        print("   %-34s 整份 %7d B → 按节 %7d B｜层一＋层二 %7d B（声明层少要求 %6d B）%s"
              % (name, whole, cut, tot1 + cut, whole - cut,
                 ("⚠ 指向点了查无的节号：" + "、".join("%s§%s" % x for x in miss)) if miss else ""))
    print("   注：⑥是**声明层**被要求读的量，磁盘与包字节一点没动；2026-10-04 四格真做层实测——落笔者为答第四节第 4 步要求的三问仍整份读，所以这一档的差额**不许当省量报**，只许说「声明口径已收窄」。")


def selftest():
    """阴性自测：把答案藏起来它还报得出，才证明它真在盯声明而不是把名字写死。"""
    res = []
    res.append(("夹具里没有层一标记时必须抽出空（不硬编码清单）",
                extract_layer1("1. `CONSTITUTION.md` — x\n") == []))
    real_l1 = extract_layer1(tx("START.md"))
    res.append(("真 START 抽出四份", len(real_l1) == 4))
    res.append(("改掉层一声明的标记后抽取要跟着变（尺子不替旧口径站岗）",
                extract_layer1(tx("START.md").replace("层一·开局必读", "第X部分", 1)) != real_l1))
    fake = "**层二·命中才读**：\n- 要报数 → `core/nope-not-here.md`：x\n**层三**\n"
    rows = extract_layer2(fake)
    res.append(("夹具里的假路径要判查无", bool(rows) and resolve(rows[0][1], "core")[0] is None))
    res.append(("真路径要原样落地", resolve("core/evidence-rigor.md", ".")[0] == "core/evidence-rigor.md"))
    res.append(("裸名要按名唯一落地", resolve("ethics.md", "core/coaching-protocol.md")[1] == "按名唯一"))
    res.append(("轮型表里不许躺着查无的文件",
                all((ROOT / f).is_file() for _n, fs in TURNS for f in fs)))
    res.append(("分节字节要加得回整份（容 200 B）",
                abs(sum(b for _, b in section_sizes("core/academic-style.md", r"^## "))
                    - nbytes("core/academic-style.md")) < 200))
    items = gate_items()
    res.append(("默查清单条数从文件里现数（不少于 10）", len(items) >= 10))
    res.append(("默查清单确实有外包项可抓",
                any(h for _i, h in outsourced(items, ["START.md"] + real_l1))))
    sty = "core/academic-style.md"
    named = SEC_NUMS.findall(bullet_text(sty))
    res.append(("⑥真在盯 START 的指向：落笔那份点名了节号，没指节号的份不受影响",
                bool(named) and section_bytes(sty, [])[0] == nbytes(sty)
                and not SEC_NUMS.findall(bullet_text("core/evidence-rigor.md"))))
    res.append(("按节求和必须真小于整份（不然「按节读」是句空话）",
                0 < section_bytes(sty, named)[0] < nbytes(sty)))
    res.append(("点了不存在的节号要报查无（不许静默少算成「省了」）",
                section_bytes(sty, ["十九"])[1] == ["十九"]))
    res.append(("文头不许丢：只点一节时算出的量要大于那一节自己",
                section_bytes(sty, ["四"])[0]
                > [b for t, b in section_sizes(sty, r"^## ") if sec_head(t) == "四"][0]))
    bad = [n for n, v in res if not v]
    for n, v in res:
        print(("PASS " if v else "FAIL ") + n)
    print("==== 共 %d 项，通过 %d，失败 %d ====" % (len(res), len(res) - len(bad), len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="尺子的阴性自测")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
