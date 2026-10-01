#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 起草语体的对照实验与判据（能复跑；判据是确定性代码，不靠人读着像不像）。

**为什么有这个文件**：`CONSTITUTION.md` 第十条——"要求 AI 怎么想"的规则也算功能，
只写进 `core/academic-style.md` 不算解决。要能回答："把这份规范发给受试，它交回来的稿子到底分不分得开。"

跑法：
    python tests/style_experiment.py --demo            # 尺子的阴性自测：两份夹具必须分得开（退出码 0 才算尺能用）
    python tests/style_experiment.py --prompt 控制臂    # 打印给受试的那句话（不带规范）
    python tests/style_experiment.py --prompt 实验臂    # 同上，但附上 core/academic-style.md 全文
    python tests/style_experiment.py --grade 某稿.md     # 判一份稿子，报每条判据的读数
    python tests/style_experiment.py --brief             # 只打印要点清单（摆题面用）

**判据为什么这么定**（三条各管一件事，缺一条就退化成"只看形状"）：
  S1 体检工具的缺项＋风险为 0条      —— 措辞与句式合不合学术语体（`tools/style_check.py` 现判，词表在规范第二节）
  S2 稿子里每个数字都在要点清单里出现过 —— **有没有编数**（语体规范最容易被学歪的地方：
                                      腔调变干净了，数字却还是编的。这条专治它，style_check 自己测不到）
  S3 要点清单里每条要点的数字都在稿子里出现 —— 有没有把要点写丢（只换个漂亮说法不算写了）
  **条数不写死**：总数从 checks 自己数（写死过一次，加判据不改数字它就永远"通过"）。

**方法学两条雷（v1.96 那批实验踩过的，这里避开）**：
  ① 提示里不能出现"这是测试／材料是合成的"，否则受试对标签作答而不是对内容作答；
  ② 两臂的**要点清单逐字相同**，只差"附不附规范"这一件事——工作区拉平不了就差两件事，结论无效。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（无条件生效，见 DEVELOPMENT.md 阶段 B）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "core" / "academic-style.md"

# 要点清单＝两臂唯一的共同题面。数字都摆在这里，S2 才有对账的下界。
BRIEF = """把下面这些要点写成毕业论文「研究方法」与「研究结果」两节的连续文字。
事实只有这些，不要补充我没给你的事实。

- 施测：2024 年 11 月，两所学校各一次，一所城区初中、一所农村初中
- 问卷发出 240 份，回收 227 份；剔除作答不足 90 秒的 11 份、规律作答的 8 份；有效样本 208 人；有效回收率 86.7%
- 被试：初一至初三，13 到 16 岁，平均 14.6 岁；男 98 人，女 110 人；两校各约一半
- 知情同意：施测前一周发纸质同意书，监护人回签 231 份，未回签的 9 人不在样本内
- 程序细节：自伤那 3 题放在问卷最后，前面加一页求助渠道信息；这是导师要求的
- 预测试插曲：有学生在自伤题上空白，另有 1 名下课后找了班主任
- 孤独感：8 题简版，1 到 4 级计分，本研究算得 α = .76；原 20 题版预测试时学生反映偏长，删题后信度下降
- 反刍思维：12 题，两个维度，α = .89，按维度取均分
- 自伤频次：自我报告清单计次，3 人该题缺失，按均值填补并写进附录
- 相关：孤独感与自伤 r = .32，p < .01；孤独感与反刍 r = .41，p < .001；反刍与自伤 r = .35，p < .01
- 中介：以孤独感为自变量、反刍为中介预测自伤，间接效应 .07 到 .19，Bootstrap 5000 次，95% CI [.07, .19]，区间不含 0
- 直接效应：加入中介后缩小，t(205) = 1.12，p = .263，判定为部分中介
- 导师原话：「别写成决定性因素」；据此结果部分一律写"预测""关联"，不写因果
"""
BRIEF_NUMS = set(re.findall(r"\d+(?:\.\d+)?", BRIEF))

# 夹具：一份照规范写的、一份照模板腔写的。两份**用的是同一批数字**，
# 所以 S2/S3 若在两份上给出相同读数，就说明它们确实量的是别的东西而不是语体。
GOOD = """2024 年 11 月，研究者在城区一所初中与农村一所初中各施测一次，发出问卷 240 份、回收 227 份，
回来先按作答时间过一遍，不足 90 秒的 11 份和整列选同一选项的 8 份剔掉，有效样本 208 人，有效回收率 86.7%。
被试初一到初三，13 到 16 岁，平均 14.6 岁，男 98 人女 110 人；两校各约一半。
施测前一周发纸质知情同意，监护人回签 231 份，未回签的 9 人不在样本里。
自伤那 3 题放在问卷最后，前面加一页求助渠道信息——这是导师要求的，
因为预测试时有学生在自伤题上空白，另有 1 名下课后找了班主任。

孤独感取 8 题简版，1 到 4 级计分，本研究算得 α = .76。原 20 题版预测试时学生反映偏长，删题后信度下降。
反刍思维 12 题，两个维度，α = .89，按维度取均分。自伤频次按自我报告清单计次，3 人该题缺失，按均值填补并写进附录。

孤独感与自伤呈显著正相关，r = .32，p < .01；与反刍的相关更高，r = .41，p < .001；反刍与自伤为 r = .35，p < .01。

以孤独感为自变量、反刍为中介变量预测自伤频次，间接效应 .07 到 .19，Bootstrap 5000 次，
95% CI [.07, .19]，区间不含 0。加入中介变量后直接效应缩小，t(205) = 1.12，p = .263，据此判定部分中介。

这些结果只说明变量之间的关联。「别写成决定性因素」这句导师意见已经落进本节的措辞里。
"""

BAD = """综上所述，本研究围绕青少年自伤这一具有重要理论意义与现实意义的课题展开了系统梳理与深入探讨。
首先，2024 年 11 月，我们对两所初中实施了问卷调查，共发放问卷约 240 份，回收情况良好，有效样本约为 208 人。
其次，测量工具方面，孤独感采用简版量表，信度良好；反刍思维采用多维度测量，内部一致性较高。

进一步而言，本研究不仅揭示了孤独感与自伤之间的显著正相关（r = 0.32, p < 0.01），
而且验证了反刍思维在其中的重要中介作用（间接效应约为 0.13）。由此可见，二者之间存在内在机制上的联动。

最后，本研究全方位、多角度地考察了相关变量的作用路径，深度契合了当前青少年心理健康工作的需要，
有力支撑了后续干预方案的落地，为后续研究提供了有益借鉴，具有深远影响。
✅ 本节结论为教育实践提供了重要抓手。
"""


def style_audit(md_path):
    """跑体检工具，数【缺项】与【风险】各有几条（提示档不计入判据——它管"节制使用"，不是错）。"""
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "style_check.py"), str(md_path)],
                       capture_output=True, cwd=str(ROOT))
    out = r.stdout.decode("utf-8", "replace")
    if "判据表读不出来" in out:
        return None, None, out

    def bucket(mark):
        tail = out.split(mark, 1)
        if len(tail) == 1:
            return 0
        body = tail[1].split("【", 1)[0]
        return len([l for l in body.splitlines() if l.startswith("  - ")])

    return bucket("【缺项】"), bucket("【风险】"), out


def grade(md_path):
    """返回 [(判据名, 过没过, 读数)]。三条判据互相独立：语体、编数、写丢要点。"""
    text = Path(md_path).read_text(encoding="utf-8", errors="replace")
    miss, risk, out = style_audit(Path(md_path))
    if miss is None:
        return [("S1 体检工具能不能跑", False, out[:120])], 0
    nums = set(re.findall(r"\d+(?:\.\d+)?", text))
    invented = sorted(n for n in nums if n not in BRIEF_NUMS)
    lost = []
    for line in BRIEF.splitlines():
        if not line.startswith("- "):
            continue
        gone = [k for k in re.findall(r"\d+(?:\.\d+)?", line) if k not in nums]
        if gone:
            lost.append("%s（缺 %s）" % (line[2:12], "、".join(gone[:3])))
    checks = [
        ("S1 措辞与句式合语体（体检缺项＋风险 0 条）", miss + risk == 0,
         "缺项 %d 条、风险 %d 条" % (miss, risk)),
        ("S2 数字全部对得上要点（没有编数）", not invented,
         "要点里没有的数字：%s" % ("、".join(invented[:8]) if invented else "无")),
        ("S3 要点没有写丢（每条要点里的数字都要在稿里）", not lost,
         "丢的要点：%s" % ("；".join(lost[:6]) if lost else "无")),
    ]
    return checks, miss + risk


def print_result(checks, total_fail):
    n = sum(1 for _, ok, _ in checks if ok)
    for name, ok, note in checks:
        print("  %s %s｜%s" % ("PASS" if ok else "FAIL", name, note))
    print("结论：%d/%d 条通过（条数从 checks 现数，不写死）" % (n, len(checks)))
    return n == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI 起草语体的对照实验（判据是确定性代码）")
    ap.add_argument("--demo", action="store_true", help="尺子自测：GOOD 必须全过、BAD 必须被抓住")
    ap.add_argument("--grade", metavar="稿.md", help="判一份稿子")
    ap.add_argument("--prompt", metavar="臂", help="打印给受试的话；写 实验臂 就附规范全文")
    ap.add_argument("--brief", action="store_true", help="只打印要点清单")
    a = ap.parse_args(argv)
    if a.brief:
        print(BRIEF)
        return 0
    if a.prompt:
        if a.prompt not in ("控制臂", "实验臂"):
            print("--prompt 只接 控制臂／实验臂", file=sys.stderr)
            return 2
        print(BRIEF)
        print("\n写好后存成一个 .md 文件，把路径报回来。")
        if a.prompt == "实验臂":
            print("\n\n以下为写作时必须遵守的语体规范全文：\n")
            print(SPEC.read_text(encoding="utf-8"))
        return 0
    if a.grade:
        return 0 if print_result(*grade(a.grade)) else 1
    if a.demo:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            g, b = Path(tmp) / "good.md", Path(tmp) / "bad.md"
            g.write_text(GOOD, encoding="utf-8")
            b.write_text(BAD, encoding="utf-8")
            print("〔照规范写的稿子（GOOD）〕")
            ok_good = print_result(*grade(g))
            print("〔模板腔稿子（BAD）〕")
            bad_checks, bad_fail = grade(b)
            for name, is_ok, note in bad_checks:
                print("  %s %s｜%s" % ("应判红" if not is_ok else "漏判!", name, note))
            ok_bad = not bad_checks[0][1] and bad_fail > 0
        print("\n判据自测：%s（GOOD 全过=%s、BAD 的语体条判红=%s）"
              % ("分得开，尺子能用" if (ok_good and ok_bad) else "分不开，尺子在空转或误伤",
                 ok_good, ok_bad))
        return 0 if (ok_good and ok_bad) else 1
    print("给 --demo / --grade / --prompt / --brief 之一", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
