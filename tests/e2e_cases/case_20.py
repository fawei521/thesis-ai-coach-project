# -*- coding: utf-8 -*-
"""case_20：宪法级严谨性条款与可复跑的对照实验（v1.91）。

盯四件事：
1. **宪法真有条款**（不是只写在规则页）：第三条加四条可判形制——顺序不许反、空位可以留空、
   交叉验证必须换独立源、流利不等于准确；第十条加「只把话写进文档＝未解决」；
2. **两侧纪律页同源**：v1.91 的四个新锚点（含实验逼出来的「上下文会被压缩，印象不是原文」）
   完整版与轻量版镜像都得有；
3. **每轮门禁第 4 条同款**：先逐字原文＋位置、再判断；
4. **实验判据不空转**：tests/rigor_experiment.py 的 judge() 对三份植入坏回答必须判红、对四份
   「新规则」记录的前两形制必须命中；脚本自身退出码 0；结论行不许出现「已解决」。
"""

_C191 = ["顺序不许反", "空位可以留空", "交叉验证必须换独立来源", "流利不等于准确"]
_R191 = ["先贴逐字引用", "空位可以留空", "流利不等于准确", "印象不是原文", "不算第二源"]
_CTXT = tx("CONSTITUTION.md")
_c3 = _CTXT.split("## 第三条")[1].split("## 第四条")[0]
_c10 = _CTXT.split("## 第十条")[1]
check("v191宪法第三条四条新形制齐备", all(k in _c3 for k in _C191), str([k for k in _C191 if k not in _c3]))
check("v191宪法把动作指向纪律页并定性为粗心违规",
      "core/evidence-rigor.md" in _c3 and "粗心违规" in _c3, _c3[:120])
check("v191宪法第十条：只写进文档不算解决",
      "只把话写进文档＝未解决" in _c10 and "对照实验" in _c10 and "行为用例" in _c10, _c10[-200:])

_F191 = tx("core/evidence-rigor.md")
_S191 = tx("doubao-skill/references/evidence-rigor.md")
check("v191纪律页四项新机制齐备", all(k in _F191 for k in _R191), str([k for k in _R191 if k not in _F191]))
check("v191轻量版镜像逐项同步（缺任一项即跨包漂移）",
      [k for k in _R191 if k in _F191] == [k for k in _R191 if k in _S191],
      "完整版缺=%s 轻量版缺=%s" % ([k for k in _R191 if k not in _F191], [k for k in _R191 if k not in _S191]))
check("v191「印象不是原文」钉在三查之后（是复核规矩不是口号）",
      "数字三查" in _F191 and _F191.index("数字三查") < _F191.index("印象不是原文"))

_G191 = tx("core/coaching-protocol.md").split("## 十、回复前门禁")[1]
_GS191 = tx("doubao-skill/references/coaching-protocol.md").split("## 十三、产出前门禁清单")[1]
check("v191两侧门禁都加了先引用后判断第 4 条",
      all("先逐字原文＋位置、再判断" in g for g in (_G191, _GS191)), "两条门禁里缺这条")
check("v191轻量版幻觉防范节加了空位与独立源",
      all(k in _GS191 for k in ("空位可以留空", "不算第二源"))
      or all(k in tx("doubao-skill/references/coaching-protocol.md") for k in ("空位可以留空", "不算第二源")))

# ---- 实验判据：不空转、可复跑、结论没写歪 ----
_ns = {}
exec(compile(tx("tests/rigor_experiment.py"), "tests/rigor_experiment.py", "exec"), _ns)
_j, _bad, _trs = _ns["judge"], _ns["BAD_ANSWERS"], _ns["TRANSCRIPTS"]


def _strict(ans):
    """只看两条与措辞无关的形制：三态标注、没放行。"""
    return [m for m in _j(ans) if "三态" in m or "放了行" in m]


check("v191判据抓得住三类坏回答", all(_strict(a) for a in _bad.values()),
      str({k: _j(v) for k, v in _bad.items() if not _strict(v)}))
_newr = {k: v for k, v in _trs.items() if k.endswith("·新规则")}
check("v191新规则四份记录前两形制全命中",
      len(_newr) == 4 and all(not _strict(v) for v in _newr.values()),
      str([k for k, v in _newr.items() if _strict(v)]))
check("v191夹具用的是合成量表名（防把合成数据当真实文献）",
      all(n not in tx("psychology/scale-library.md") for n in ("NRS-20", "TFD-21", "GDS-7")))
_x19 = run(["tests/rigor_experiment.py"], t=90)
check("v191对照实验脚本退出码 0", _x19.returncode == 0,
      ((_x19.stdout or "")[-260:] + (getattr(_x19, "stderr", "") or "")[-160:]))
_RT = tx("tests/rigor_experiment.py")
check("v191实验结论如实写着测不出说错数的差异",
      all(k in _RT for k in ("同样没报错数", "形式可稽核", "本方法测不到"))
      and "已解决" not in _RT.split("诚实边界")[-1], _RT.splitlines()[-4:])
# 报告在仓库外的 _归档（不随包分发）：开发树里必须已落盘，包内自然跳过
_rep = ROOT.parent / "_归档" / "审查报告" / "2026-09-20 严谨性闸 A-B 实验.md"
if _rep.exists():
    _rt = _rep.read_text(encoding="utf-8")
    check("v191实验报告已归档并写了两次方法学事故",
          all(k in _rt for k in ("夹具太友好", "夹具泄漏", "n=1", "不放行", "局限")), _rep.name)

# ---- 行为自测登记：把实验里真正会出事的压力点变成用例 ----
_BTT = tx("tests/behavior-self-test.md")
_BTN = sorted(int(x) for x in re.findall(r"^\| T(\d+) \|", _BTT, flags=re.M))
check("v191行为自测含 T50-T51 且编号连续",
      _BTN == list(range(1, len(_BTN) + 1)) and 50 in _BTN and 51 in _BTN,
      "n=%d tail=%s" % (len(_BTN), _BTN[-4:]))
_STT = tx("doubao-skill/references/self-test.md")
_STN = sorted(int(x) for x in re.findall(r"^\| T(\d+) \|", _STT, flags=re.M))
check("v191轻量版自测含 T47-T48 且编号连续",
      _STN == list(range(1, len(_STN) + 1)) and 47 in _STN and 48 in _STN,
      "n=%d tail=%s" % (len(_STN), _STN[-4:]))
check("v191新用例压的是被催着只给一个数这个压力点",
      "只回一个数字" in _BTT and "别耽误" in _STT)
