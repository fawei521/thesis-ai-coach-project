#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量版（doubao-skill）↔ 完整版 口径同源核对（跨包守卫）。

为什么需要它：`tests/consistency_check.py` 把 `doubao-skill/` 整目录列为独立命名空间跳过，
轻量版自己的 `validate.py` 只看目录内部——于是"两边口径必须一致"这条设计原则
（`doubao-skill/README.md` 设计原则第 1 条）过去**只有人的记性能发现**。本脚本把它变成门禁。

用法：
    python tests/skill_sync_check.py             # 核对；退出码 0 = 无漂移
    python tests/skill_sync_check.py --selftest  # 阴性自测：植入变异，确认这把尺抓得到
"""
import re
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（中文 Windows 默认 GBK） ---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "doubao-skill"

# 轻量版允许落后完整版的版本数；超过即判红。改这个数字要在 CHANGELOG 写理由。
MAX_LAG = 15

# 学生侧硬口径：两侧用同一条正则抽取，权威侧必须恰好一个值，轻量侧必须含该值。
# 锚点写成「上下文邻近」而非全文匹配，避免关键词误伤（同一个词在别的语境里数字不同）。
CALIBERS = [
    ("简单中介样本量下限", ("core", "workflows", "psychology"), r"简单中介[^。\n]{0,40}?[≥>]\s*(\d+)"),
    ("链式中介样本量建议", ("core", "workflows", "psychology"), r"链式[^。\n]{0,40}?[≥>]\s*(\d+)"),
    ("Harman 单因素门槛", ("core", "workflows", "psychology"), r"Harman[^。\n]{0,40}?(\d+)\s*%"),
    ("Bootstrap 重抽样次数", ("core", "workflows", "psychology"), r"Bootstrap[^.\n]{0,30}?(\d{4})"),
    ("心理援助热线号码", ("core", "workflows", "psychology"), r"(12356)"),
    ("数据清洗指标个数", ("core", "workflows"), r"([五六四])指标"),
    ("答辩高频问题条数", ("core", "workflows", "psychology"), r"(\d{2})\s*问(?![题答])"),
]

# 轻量版侧只扫学生会被读到的文件：维护者账本与合并单文件产物不算学生口径
SKILL_DIRS = ("references", "stages", "templates")
SKILL_SKIP = {"CHANGELOG.md", "README.md", "thesis-ai-coach-手机版.md"}
# 版本自述只允许出现在 doubao-skill/CHANGELOG.md；这两份学生可见文件里出现即判红。
# 锚点必须能命中真实写法（"口径同步点：…v1.61"、"对应完整版 v1.78"），
# 只盯「完整版 v」这种连写会空转——2026-09-19 自测当场抓到过一次假绿。
VERSION_BAN = [(SKILL / "SKILL.md"), (SKILL / "README.md")]
VERSION_BAN_RX = r"(同步点|对应完整版|完整版已到|已同步)[^。\n]{0,14}?v\d"


def mds(dirs):
    """完整版一侧：给定子目录下的 .md，排除轻量版子包与测试账本。"""
    out = []
    for d in dirs:
        base = ROOT / d
        if base.exists():
            out += [p for p in sorted(base.rglob("*.md"))
                    if SKILL not in p.parents and p.name != "e2e-test.md"]
    return out


def skill_mds():
    out = []
    for d in SKILL_DIRS:
        base = SKILL / d
        if base.exists():
            out += [p for p in sorted(base.rglob("*.md")) if p.name not in SKILL_SKIP]
    return out + [p for p in VERSION_BAN if p.exists()]


def texts(paths):
    """[(相对路径, 正文)]——比对全部走文本，--selftest 因此能植入变异而不碰磁盘。"""
    return [(str(p.relative_to(ROOT)), p.read_text(encoding="utf-8", errors="replace"))
            for p in paths]


def values(pattern, items):
    rx = re.compile(pattern)
    out = {}
    for rel, body in items:
        vals = sorted(set(rx.findall(body)))
        if vals:
            out[rel] = vals
    return out


def compare(name, full_items, skill_items, pattern):
    """一条口径的比对，返回问题列表。"""
    fvals = sorted({v for vs in values(pattern, full_items).values() for v in vs})
    svals = sorted({v for vs in values(pattern, skill_items).values() for v in vs})
    if len(fvals) != 1:
        return ["口径锚点失效 [%s]：完整版侧匹配到 %s（应为恰好一个值）→ "
                "改锚点，或确认这条口径已删除后把该行从 CALIBERS 移除" % (name, fvals or "零个值")]
    want = fvals[0]
    if not svals:
        return ["口径缺失 [%s]：完整版=%s，轻量版学生文件里查不到 → 追平进 doubao-skill/" % (name, want)]
    bad = sorted(set(svals) - {want})
    if bad:
        return ["口径漂移 [%s]：完整版=%s，轻量版另有 %s → 两侧必须同源" % (name, want, bad)]
    return []


def vkey(s):
    """版本号取前两段：v1.78 与 v1.78.1 都算 1.78。"""
    return tuple(int(x) for x in s.lstrip("v").split(".")[:2])


def full_version():
    """完整版当前版本 = 包内 CHANGELOG 索引第一行（唯一版本史）。"""
    for line in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*\*\*(v[\d.]+)\*\*", line.strip())
        if m:
            return m.group(1)
    return ""


def skill_sync_point():
    """轻量版口径同步点 = Skill CHANGELOG 最新一条里的「对应完整版 vX.Y」（唯一权威源）。"""
    m = re.search(r"对应完整版[^0-9v]*?(v[\d.]+)",
                  (SKILL / "CHANGELOG.md").read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def skill_head_version():
    """Skill 自己的版本号也要有唯一来源：CHANGELOG 第一条小节标题。"""
    m = re.search(r"^## (v[\d.]+)", (SKILL / "CHANGELOG.md").read_text(encoding="utf-8"), flags=re.M)
    return m.group(1) if m else ""


def version_problems(cur, sync, items):
    """版本自述的四条规矩，纯函数便于植入变异：超前＝撒谎，落后超限＝欠账，手写完整版号＝分叉，自报版本对不上账＝两套史。"""
    if not cur:
        return ["读不到完整版当前版本（CHANGELOG.md 索引第一行的格式变了？）"]
    if not sync:
        return ['读不到轻量版口径同步点（doubao-skill/CHANGELOG.md 最新条目缺「对应完整版 vX.Y」）']
    out = []
    if vkey(sync) > vkey(cur):
        out.append("轻量版自称已同步到 %s，而完整版只到 %s → 自述超前，属虚假声明" % (sync, cur))
    if vkey(sync)[0] == vkey(cur)[0] and vkey(cur)[1] - vkey(sync)[1] > MAX_LAG:
        out.append("轻量版口径停在 %s，完整版已到 %s，落后超过 %d 个 minor → "
                   "必须追平（ROADMAP 的「Skill 轻量版口径追平」项）" % (sync, cur, MAX_LAG))
    head = skill_head_version()
    for rel, body in items:
        m = re.search(VERSION_BAN_RX, body)
        if m:
            out.append("[%s] 手写了完整版版本自述（…%s…）→ 只允许写在 doubao-skill/CHANGELOG.md 一处"
                       % (rel, m.group(0)[:28]))
        said = re.search(r"Skill\s*版本：\s*(v[\d.]+)", body)   # 自报的 Skill 版本要与 CHANGELOG 一致（没写不算错）
        if head and said and rel.endswith("SKILL.md") and said.group(1) != head:
            out.append("[SKILL.md] 自报 Skill 版本 %s 与 CHANGELOG 最新条目 %s 不一致 → 两处必须同源"
                       % (said.group(1), head))
    return out


def run():
    sf = skill_mds()
    sitems, problems, hit = texts(sf), [], 0
    for name, dirs, pattern in CALIBERS:
        got = compare(name, texts(mds(dirs)), sitems, pattern)
        problems += got
        hit += not got
    problems += version_problems(full_version(), skill_sync_point(),
                                 texts([p for p in VERSION_BAN if p.exists()]))
    print("=" * 60)
    print("轻量版（doubao-skill）↔ 完整版 口径同源核对")
    print("=" * 60)
    print("完整版当前 %s ｜ 轻量版同步点 %s ｜ 学生文件 %d 个"
          % (full_version(), skill_sync_point(), len(sf)))
    if problems:
        print("\n发现 %d 处问题：" % len(problems))
        for p in problems:
            print("  [漂移] " + p)
        return 1
    print("\n结论：%d 条硬口径两侧一致，版本自述在单一权威源。" % hit)
    return 0


def selftest():
    """阴性自测：尺子必须抓得到每一种植入的坏，否则它就是空转。"""
    name, dirs, pattern = CALIBERS[0]
    full, sitems = texts(mds(dirs)), texts(skill_mds())
    want = sorted({v for vs in values(pattern, full).values() for v in vs})[0]
    carrier = [(rel, body) for rel, body in sitems if values(pattern, [(rel, body)])][0]
    flipped = [(carrier[0], carrier[1].replace(want, "9999"))]
    rest = [(r, b) for r, b in sitems if (r, b) != carrier]
    cases = [
        ("轻量版数字被改要判红", compare(name, full, flipped + rest, pattern), True),
        ("轻量版整条缺失要判红", compare(name, full, [], pattern), True),
        ("权威侧锚点失效要判红", compare(name, [], sitems, r"这条锚点根本不存在ZZZ"), True),
        ("自述超前要判红", version_problems("v1.87", "v1.99", []), True),
        ("落后超限要判红", version_problems("v1.87", "v1.61", []), True),
        ("手写版本自述要判红", version_problems("v1.87", "v1.87",
                                                [("doubao-skill/SKILL.md", "口径同步点：v1.61（完整版已到 v1.78）")]), True),
        ("自报Skill版本不一致要判红", version_problems("v1.89", "v1.89",
                                                       [("doubao-skill/SKILL.md", "Skill 版本：v0.0.1")]), True),
        ("正常输入不得误报", compare(name, full, sitems, pattern) +
         version_problems(full_version(), skill_sync_point(), []), False),
    ]
    bad = []
    for label, got, should_hit in cases:
        if should_hit and not got:
            bad.append("阴性自测落空：" + label)
        elif should_hit:
            print("  [OK] %s → %s" % (label, got[0][:56]))
        elif got:
            bad.append("阴性自测误伤：" + label + " → " + got[0][:56])
        else:
            print("  [OK] " + label)
    for b in bad:
        print("  [FAIL] " + b)
    if bad:
        return 1
    print("\n阴性自测通过：植入的漂移全部被抓，正常输入不误报。")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
