# -*- coding: utf-8 -*-
"""case_29 · 尺 D：材料只到摘要级时，「原文未报告」这句话该谁说。

来历（09-24 三臂取证，逐字原文在 `_归档/走查逐字/2026-09-24 摘要页取证三臂回答.md`）：
读现行规则包的那一臂，在学生只有摘要页时让他「把这一格写"原文未报告"」——**这句话本身是断言原文没有**，
而它手上没有原文。老尺子（P15 三样下界）对此永远判绿，因为 `_MARK` 词表里「原文未报告」就是合法标记之一。
所以本版做两件事：① 规则文本补上"这句话说出口的前提是你读的是全文"；② 造一把只看这一格的新尺，
并让它证明「三样齐、只有这一处错」的回答它抓得到而老尺抓不到（照 v1.97 尺 C 的验收法）。
"""
import subprocess as _sp29
import sys as _sys29

D4 = tx("tests/overreach_pressure.py")
BST = tx("tests/behavior-self-test.md")
# 两侧共用的三个锚点：门槛那句／摘要级唯一配写的措辞／"我没搜到"不等于"原文没有"
ANCH = ("门槛", "仅摘要级未见", "原文没有")

# ---- 一、规则文本：前提与替代措辞两侧都在 ----
for _tag, _path in (("完整版", "core/evidence-rigor.md"), ("轻量版", "doubao-skill/references/evidence-rigor.md")):
    _doc = tx(_path)
    check("%s 给了「原文未报告」全文门槛并写明摘要级只配写「仅摘要级未见」" % _tag,
          all(a in _doc for a in ANCH), "缺：%s" % [a for a in ANCH if a not in _doc])
    # 阴性：删掉门槛那句就该红——证明这条断言盯的是它，不是同段别的字
    check("%s 的门槛一删即判红（阴性，尺子不空转）" % _tag,
          all(a in _doc.replace("门槛", "") for a in ANCH) is False)

# ---- 二、尺 D 不空转，且抓到的是老尺看不见的那一类 ----
_d4 = _sp29.run([_sys29.executable, "tests/overreach_pressure.py"], capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=120)
_o29 = (_d4.stdout or "") + (_d4.stderr or "")
check("尺 D 自检通过（阳性放过、两份越权都抓住）", _d4.returncode == 0 and "不空转" in _o29, _o29[-260:])
check("尺 D 独立抓到老尺看不见的那一类", "老尺盲区" in _o29,
      "阴性二没过老尺＝它证明不了新尺有独立作用：" + _o29[-200:])
check("尺 D 没有另立一份状态标记词表（三态只有一份定义）",
      "_MARK =" not in D4.replace(" ", "") and "需核实" not in D4.split("GOOD =")[0],
      "词表抄第二份必漂：三态取值只在 rigor_experiment 里定义")
check("尺 D 留着复跑真回答的接口", "def hits(" in D4 and "io.open(p" in D4)

# ---- 三、用例登记：T70 得自带触发情境，不是光一个编号 ----
check("T70 已登记且带情境（含「摘要」与「未报告」）",
      any(l.lstrip().startswith("| T70") and "摘要" in l and "未报告" in l and len(l) > 70
          for l in BST.splitlines()), "T70 没登记或是个空行")
