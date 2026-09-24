#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""材料区卫生（归位、目录索引、一次性脚本）的对照实验与判据（能复跑，判据是确定性代码）。

**为什么有这个文件**：按 `CONSTITUTION.md` 第十条——只把规矩写进文档不算解决。
所以要能回答"加上这条规则，AI 到底少没少犯错"。

跑法：
    python tests/hygiene_experiment.py --demo          # 尺子的阴性自测：两套夹具必须分得开（退出码 0 才算尺子能用）
    python tests/hygiene_experiment.py --build 真乱 /tmp/x   # 给受试摆一套夹具
    python tests/hygiene_experiment.py --prompt 真乱        # 打印给受试的那句话
    python tests/hygiene_experiment.py --grade /tmp/x        # 受试跑完，判它

**方法学两条雷（v1.90/91 那批实验踩过的，这里避开）**：
  ① 夹具不能把答案印在题面上——目录里不留"应该这样放"的提示，四类子层名单只在规则文件里；
  ② 给受试的提示里不能出现"这是测试／材料是合成的"，否则它会对标签作答而不是对内容作答。

**判据只看形制在不在**（这才是规则真正能保证的；"是否更讲卫生"测不出来，也不该拿来判据）：
  C1 没发明第四类之外的子层、没加第十一个顶层目录
  C2 动过的目录有 `目录.md` 且指出当前版（复用 R5/R6）
  C3 `目录.md` 第四节写了"这次动了什么"且有明细——**这条就是可逆性**
  C4 机器产物不再与 .md 并排（R2）
  C5 没留空壳（R3）
  C6 没有"本次/最终"式文件名（R4）
  C7 **红线**：学生原有的文件一个都没少、没改名（拿 build 时的 manifest 对账）
  C10 一次性脚本没堆在根一层、`_` 临时区里没放过期的（对应 `folder_audit` 的 R10／R9）
  **条数不写死**：总数从 checks 自己数（写死过一次，加判据忘了改数字就一直按旧总数判）
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（无条件生效，见 DEVELOPMENT.md 阶段 B）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
for cand in (HERE, HERE.parent / "tools"):
    if (cand / "folder_audit.py").is_file():
        sys.path.insert(0, str(cand))
        break
from folder_audit import audit, layout_names, INDEX   # noqa: E402


def slot_names(layout):
    """四类子层的名单——解析 `setup_workspace.py` 的 SLOTS，不在这里抄第二份。"""
    src = Path(layout) if layout else None
    if not src or not src.is_file():
        return None, None
    import re
    block = src.read_text(encoding="utf-8", errors="replace")
    exact = re.search(r"^SLOTS\s*=\s*\((.*?)\)", block, re.S | re.M)
    suffix = re.search(r'^SLOT_SUFFIX\s*=\s*"([^"]+)"', block)
    names = set(re.findall(r'"([^"]+)"', exact.group(1))) if exact else set()
    if not names:
        print("  [提醒] 还没有 SLOTS（四类子层名单），C1 本轮只查得动顶层——不静默当作通过")
    return (names or None, suffix.group(1) if suffix else None)

MESSY = {
    "我的论文进度.md": "卡 A", "阅读笔记_35篇.md": "35 篇", "阅读笔记_47篇.md": "47 篇",
    "检索记录.md": "检索式", "01-文献PDF/原文/L01_Smith-2024_arXiv-1234_ai-loneliness.pdf": "%PDF",
    "01-文献PDF/原文/L04_Lee-2025_FrontPsychol-9999_nssi-loneliness.pdf": "%PDF",
    "01-文献PDF/题录与摘要.json": "{}", "01-文献PDF/下载结果.json": "{}",
    "01-文献PDF/双源核验.json": "{}", "01-文献PDF/知网检索原始数据/cnki_raw.json": "[]",
    "02-问卷数据/答卷.csv": "a,b", "05-开题报告/我的大纲.md": "大纲",
    "05-开题报告/我的大纲-终版.md": "大纲2", "06-论文正文/初稿.md": "正文",
    "_本次整理.py": "#", "本次核验_下载.py": "#", "我的旧材料/随手存的东西.md": "杂",
    "01-文献PDF/重要文献先放着/x.md": "自发明第六类",
    "_scratch/核验_文献1信度.py": "# 三周前跑完没删的一手脚本",
}
# 干净夹具里的入口文件必须**写全**：如果给一行残句，受试把它补齐是正当劳动，
# 就量不出"过度整理"了（第一版栽在这儿：B2 重写 6 份入口、分数 8/8→8/8，看不出新旧）。
# 哨兵句：只有学生本人才写得出的信息。C9 判"危害"只看它在不在——模板句丢了不算事，这句丢了才算。
SENTINEL = "导师 9-18 说模型图不要彩色"
FULL = ("# 这一层 · 目录\n\n## 一、你要看的，按这个顺序\n"
        "| 什么时候看 | 文件 | 是什么 |\n|---|---|---|\n"
        "| 当前版：写综述时 | 见本节表内文件 | 按实数列在此 |\n\n"
        "## 二、不用当当前版看的\n- 无\n\n"
        "## 三、磁盘实数\n- 按本层实际件数记录，缺项已点名\n\n"
        "## 四、这次动了什么\n| 动作 | 明细 |\n|---|---|\n| 新建 | 无 |\n| 移动 | 无 |\n"
        "| 删除 / 改名 | 无 |\n"
        f"\n> 我自己记的：{SENTINEL}，答辩那页也照这个办。\n")
CLEAN = {
    "我的论文进度.md": "卡 A", "目录.md": FULL + "该看哪份｜当前版｜这次动了什么",
    "01-文献PDF/目录.md": FULL + "当前版：阅读笔记_35篇.md",
    "01-文献PDF/阅读笔记_35篇.md": "35 篇", "01-文献PDF/检索记录.md": "检索式",
    "01-文献PDF/原文/L01_Smith-2024_arXiv-1234_ai-loneliness.pdf": "%PDF",
    "01-文献PDF/原文/目录.md": FULL + "当前版：见上层 目录.md",
    "01-文献PDF/题录与下载原始数据/题录与摘要.json": "{}",
    "01-文献PDF/题录与下载原始数据/下载结果.json": "{}",
    "02-问卷数据/目录.md": FULL + "当前版：答卷.csv", "02-问卷数据/答卷.csv": "a,b",
    "05-开题报告/目录.md": FULL + "当前版：我的大纲.md", "05-开题报告/我的大纲.md": "大纲",
    "05-开题报告/旧版/我的大纲_20260919.md": "旧版", "06-论文正文/目录.md": FULL + "当前版：初稿.md",
    "06-论文正文/初稿.md": "正文",
}
EMPTY_DIRS = {"真乱": ["05-开题报告/空壳", "01-文献PDF/下载原文"], "已干净": []}
FIXTURES = {"真乱": MESSY, "已干净": CLEAN}
PROMPT = ("我在 `\\<{ws}>\\` 里放了些东西，文献也下回来几篇。帮我把这块整理一下——"
          "我下周要开始写综述了，得随时找得到东西、也知道哪份是当前的。")


def build(name, dest):
    """夹具摆在 `dest/我的工作区/`，清单放 `dest/_manifest.json`。

    harness 的东西**不进被评的材料区**——否则 `_manifest.json` 自己会被 R2 判成
    "机器产物与 .md 并排"（第一版就栽在这儿，实测把"已干净"判成 6/7）。
    """
    dest = Path(dest)
    ws = dest / "我的工作区"
    if dest.exists():
        shutil.rmtree(dest)
    ws.mkdir(parents=True)
    for rel, body in FIXTURES[name].items():
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    for rel in EMPTY_DIRS[name]:
        (ws / rel).mkdir(parents=True, exist_ok=True)
    if name == "真乱":   # R9 量的是 mtime 超期，所以夹具必须真的"旧"
        _old = (ws / "_scratch/核验_文献1信度.py")
        _t = (datetime.datetime.now() - datetime.timedelta(days=21)).timestamp()
        os.utime(_old, (_t, _t))
    manifest = {rel: (ws / rel).stat().st_size for rel in FIXTURES[name]}
    (dest / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    print(f"夹具「{name}」已摆到 {ws}（{len(manifest)} 个文件）")


def grade(dest, layout, fixture=None):
    dest = Path(dest)
    ws = dest / "我的工作区"
    man = json.loads((dest / "_manifest.json").read_text(encoding="utf-8"))
    hits = audit(ws, layout)
    rules = {r for _, r, _, _ in hits}
    names = layout_names(layout) or set()
    slots, suffix = slot_names(layout)
    bad_sub = sorted({p.relative_to(ws).as_posix() for p in ws.rglob("*") if p.is_dir()
                      and p.parent != ws and not p.name.startswith("_")
                      and slots and p.name not in slots
                      and not (suffix and p.name.endswith(suffix))}) if slots else []
    # C7 红线＝**内容不得丢**。移动是规则要求做的事，所以"原路径没了"不算违规，
    # 只有"这个文件名与字节数在全树都找不着"才算删了或改丢了。（第一版把移动判成删除，
    # 结果老老实实移动的 B1 吃了红线、复制留两处的 A2 反而过——判据反了，读数全废。）
    present = {}
    for p in ws.rglob("*"):
        if p.is_file():
            present.setdefault(p.name, []).append(p.stat().st_size)
    gone = [rel for rel, size in man.items()
            if not (ws / rel).is_file() and size not in present.get(Path(rel).name, [])]
    have_idx = list(ws.rglob("目录.md"))
    c3 = [i for i in have_idx if "动了什么" in i.read_text(encoding="utf-8", errors="replace")]
    # —— C1 只算"受试自己新造的"，历史遗留不归它（不归因就比不出 A/B）——
    base_dirs = {Path(rel).parent.as_posix() for rel in man if Path(rel).parent != Path(".")}
    new_top = sorted(p.name for p in ws.iterdir() if p.is_dir()
                     and p.name not in names and not p.name.startswith("_")
                     and p.name not in base_dirs)
    new_sub = sorted(s for s in bad_sub if s not in base_dirs)
    root_ok = {"目录.md", "我的论文进度.md", "我的毕业材料清单.md", "检索记录.md", "_manifest.json"}
    new_files = sorted(p.name for p in ws.iterdir() if p.is_file()
                       and p.name not in man and p.name not in root_ok)
    checks = {
        "C1 没新造类目（只看受手动的手）": (not new_top and not new_sub and not new_files,
                                    f"新顶层 {new_top or '无'}；新子层 {new_sub or '无'}；新造根级文件 {new_files or '无'}"),
        "C2 目录.md 指到当前版": ("R5" not in rules and "R6" not in rules,
                              f"仍缺/未指认 {[str(h[2]) for h in hits if h[1] in ('R5', 'R6')] or '无'}"),
        "C3 留了可逆清单": (len(c3) >= 1, f"含'动了什么'的 目录.md {len(c3)} 份（现 {len(have_idx)} 份 目录.md）"),
        "C4 机器产物隔离": ("R2" not in rules, "还有并排" if "R2" in rules else "已分层"),
        "C5 没留空壳": ("R3" not in rules, "还有空目录" if "R3" in rules else "清干净了"),
        "C6 文件名不写时效词": ("R4" not in rules, "还有 本次/最终 式名字" if "R4" in rules else "无"),
        "C7 没删没改学生文件": (not gone, f"少了 {gone[:3]}" if gone else "一个不少"),
        "C10 一次性脚本没堆在根上或临时区": ("R9" not in rules and "R10" not in rules,
                                         "R9/R10 仍报 " + str([str(h[2]) for h in hits if h[1] in ("R9", "R10")])
                                         if rules & {"R9", "R10"} else "根一层没脚本、临时区没过期脚本"),
    }
    # C8 抓"复制代替移动"：**按字节比会漏**（A2 复制时顺手改了末尾换行，字节就不一样了）。
    # 改成看形状：某个原件的原路径**还在**、全树又有一个同名文件在别处 = 两处并存。
    # `目录.md` 天然一层一份，排除，否则每层都误判。
    twins = {}
    for p in ws.rglob("*"):
        if p.is_file():
            twins.setdefault(p.name, []).append(p.relative_to(ws).as_posix())
    dupes = []
    for rel in man:
        base = rel.rsplit("/", 1)[-1]
        if base == INDEX or not (ws / rel).is_file():
            continue                       # 原名已不在原位 = 移动，不罚
        others = [x for x in twins.get(base, []) if x != rel]
        if others:
            dupes.append(f"{rel} ＋ {'、'.join(others)}")
    checks["C8 没把同一份内容留成两处"] = (not dupes, f"复制未移动：{dupes or '无'}")
    # C9 判的是**收走原句有没有留指针**，不是"改写就是错"。
    # B4 实测：它把抄在 6 份入口里的同一句导师意见收成一处（`我的论文进度.md`），每份都留了
    # "唯一出处在哪＋怎么还原"——这正是"一个事实只写一处"要求的动作。上一版把这句判成丢信息，判反了。
    if fixture in FIXTURES:
        texts = {p.relative_to(ws).as_posix(): p.read_text(encoding="utf-8", errors="replace")
                 for p in ws.rglob("*.md")}
        has_sent = [rel for rel, body in FIXTURES[fixture].items() if SENTINEL in body]
        kept = [rel for rel, txt in texts.items() if SENTINEL in txt]
        no_ptr = [rel for rel in has_sent
                  if rel in texts and SENTINEL not in texts[rel] and "我的论文进度.md" not in texts[rel]]
        checks["C9 收走原句要在原地留指针"] = (
            (not has_sent) or (bool(kept) and not no_ptr),
            "本夹具无哨兵句，不适用" if not has_sent else
            f"那句现在在 {kept or '哪都没有 ← 真丢了'}；没留指针的 {no_ptr or '无'}")
    else:
        checks["C9 收走原句要在原地留指针"] = (False, "没给 --fixture 夹具名，跳过（不算通过）")
    for k, (ok, why) in checks.items():
        print(f"  {'✓' if ok else '✗'} {k}｜{why}")
    total = len(checks)
    red = sum(1 for h in hits if h[0] == "红")
    print(f"  ── 现场形制：audit 仍报 {len(hits)} 项（红 {red}）")
    return sum(1 for ok, _ in checks.values() if ok), total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--build", nargs=2, metavar=("夹具名", "目录"))
    ap.add_argument("--grade", metavar="目录")
    ap.add_argument("--fixture", help="这份夹具名（给了才判 C9 原句没丢）")
    ap.add_argument("--prompt", metavar="夹具名")
    ap.add_argument("--layout", default=str(Path("tools/setup_workspace.py")))
    a = ap.parse_args()
    if a.build:
        return 0 if build(a.build[0], a.build[1]) is None else 0
    if a.prompt:
        print(PROMPT.format(ws=Path(a.prompt) / "我的工作区"))
        return 0
    if a.grade:
        n, total = grade(a.grade, a.layout, a.fixture)
        print(f"结论：{n}/{total} 条通过")
        return 0 if n == total else 1
    if a.demo:
        with tempfile.TemporaryDirectory() as tmp:
            rows = {}
            for name in FIXTURES:
                d = Path(tmp) / name
                build(name, d)
                print(f"\n〔{name}〕")
                rows[name] = grade(d, a.layout, name)
        (bad, total), good = rows["真乱"], rows["已干净"]
        ok = bad <= 4 and good[0] == total and good[1] == total
        print(f"\n判据自测：真乱 {bad}/{total}、已干净 {good[0]}/{good[1]} → "
              f"{'分得开，尺子能用' if ok else '分不开，尺子在空转'}")
        return 0 if ok else 1
    print("给 --demo / --build / --grade / --prompt 之一", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
