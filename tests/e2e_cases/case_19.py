# -*- coding: utf-8 -*-
"""case_19：证据与核验纪律（v1.90）——把"报数字前先核验"从倡议变成门禁。

起因（学生侧真实事故形态）：网上抓论文时只看摘要/检索页就报数据、把二手网页里并列的别的量表的信度
安到学生选的量表上、关键词搜漏就宣布"原文没报"。以前这类要求散在多页且都是软措辞，这一版收成一个权威源
`core/evidence-rigor.md`（轻量版镜像 `doubao-skill/references/evidence-rigor.md`），并钉三件事：

1. **接进每轮门禁**（不是"再强调一次"）——两份 coaching-protocol 的产出前清单各含三条硬动作；
2. **两侧同源**——镜像的口径锚点必须与完整版逐条对得上（`consistency_check.py` 整目录跳过 doubao-skill，跨包靠这里）；
3. **机器真拦**——`proposal_readiness.py` 把没清的 `[需核实]` 报成缺项，`--strict` 下退出码 1。
"""

_RIGOR_KEYS = {"三态标注": "三态标注", "引用四要素": "引用四要素", "切片禁令": "切片禁令",
               "数字三查": "数字三查", "回读定位": "回读定位", "对象对齐": "对象对齐",
               "换源复核": "换源复核", "否定闸门": "≠ 原文没有", "正式稿闸": "不得进正式稿",
               "更正门槛": "更正的门槛高于原结论", "清点落盘": "落盘的错必须清点"}


def _rigor_missing(text):
    """返回这份文本里**缺掉**的口径锚点（纯函数，供阴性测试植入缺失）。"""
    return sorted(k for k, v in _RIGOR_KEYS.items() if v not in text)


_R_FULL = tx("core/evidence-rigor.md")
_R_SKILL = tx("doubao-skill/references/evidence-rigor.md")

# ---- 1. 权威源齐件、口径完整、两侧同源 ----
check("v190完整版证据纪律十一项口径齐备", not _rigor_missing(_R_FULL), str(_rigor_missing(_R_FULL)))
check("v190轻量版镜像同样齐备（缺件即坏）",
      len(_R_SKILL) > 1500 and not _rigor_missing(_R_SKILL), str(_rigor_missing(_R_SKILL)))
check("v190两侧口径同源（跨包不漂移）",
      _rigor_missing(_R_SKILL) == _rigor_missing(_R_FULL) == [],
      "完整缺=%s 轻量缺=%s" % (_rigor_missing(_R_FULL), _rigor_missing(_R_SKILL)))
check("v190尺子抓得到缺失（阴性）",
      _rigor_missing(_R_FULL.replace("换源复核", "")) == ["换源复核"]
      and len(_rigor_missing("与纪律无关的一页文本")) == len(_RIGOR_KEYS))

# ---- 2. 接线：每轮门禁 + 入口文件 + 取数现场 ----
_PROTO = tx("core/coaching-protocol.md")
_GATE = _PROTO.split("## 十、回复前门禁")[1] if "## 十、回复前门禁" in _PROTO else ""
check("v190每轮门禁长出三条硬动作",
      all(k in _GATE for k in ("引用四要素", "读取范围已如实声明", "条数上限截断")), _GATE[:160])
check("v190核心原则与三份入口都指向纪律页",
      "core/evidence-rigor.md" in tdoc("core/coach-rules.md")
      and all("core/evidence-rigor.md" in tx(f) for f in
              ("START.md", "AGENTS.md", "core/coaching-protocol.md", "core/ai-literacy.md")))
check("v190摘要不算原文写进取数现场",
      all(k in tx("workflows/paper-reading-guide.md") for k in
          ("读取范围声明", "取证栏", "数字三查", "搜不到 ≠ 没有"))
      and "数字三查" in tx("workflows/literature-auto-search.md")
      and "节号/表号" in tx("workflows/proposal-guide.md"))
check("v190AI素养页教学生怎么验收AI的数",
      "读到原文还是读到摘要" in tx("core/ai-literacy.md"))
check("v190阶段3细则带取证口径", "evidence-rigor.md" in tx("core/coach-rules/stage-playbook.md"))

# ---- 3. 轻量版接线（手机端同一套动作）----
_SK_PROTO = tx("doubao-skill/references/coaching-protocol.md")
_SKGATE = _SK_PROTO.split("## 十三、产出前门禁清单")[1] if "## 十三、产出前门禁清单" in _SK_PROTO else ""
check("v190轻量版门禁同款三条",
      all(k in _SKGATE for k in ("引用四要素", "读取范围已如实声明", "条数上限截断")), _SKGATE[:160])
check("v190轻量版入口与四份阶段文件已接线",
      all("references/evidence-rigor.md" in tx("doubao-skill/" + f)
          for f in ("SKILL.md", "references/coaching-protocol.md", "references/academic-norms.md",
                    "references/ai-basics.md", "stages/stage-2-literature.md",
                    "stages/stage-3-organize.md", "stages/stage-4-scale.md")))
_SK_RULES = tx("doubao-skill/SKILL.md").split("## 五、运行铁律")[1].split("\n## ")[0]
check("v190运行铁律写明三查与读取范围",
      all(k in _SK_RULES for k in ("逐字原文", "回读定位", "换源复核", "全文还是摘要")), _SK_RULES[:160])
check("v190手机合并单文件收进了纪律页",
      "证据与核验纪律" in tx("doubao-skill/thesis-ai-coach-手机版.md")
      and "回读定位" in tx("doubao-skill/thesis-ai-coach-手机版.md"))
_ORD = tx("doubao-skill/build_mobile_single.py")
check("v190合并顺序表登记了纪律页（防漏拼）",
      '"references/evidence-rigor.md"' in _ORD
      and _ORD.index('"references/stage-checklist.md"') < _ORD.index('"references/evidence-rigor.md"'))
check("v190轻量版必备件清单含纪律页（validate 缺件判红）",
      '"evidence-rigor.md"' in tx("doubao-skill/validate.py"))

# ---- 4. 工具真拦：带 [需核实] 的开题大纲进不了 --strict ----
# 夹具复用 case_17 的坏大纲正文，只把文献综述那行改成品里带未清标记（不新造一份大纲免得两套基准漂）。
_d19 = new_tmp("v190")
_unclean = "\n".join(
    l.replace("- 三条脉络与缺口",
              "- 该量表 α=.96 [需核实]（这个数字其实来自另一份研究的摘要页）")
    for l in BAD17.splitlines())
check("v190夹具确实带上了未清标记", "[需核实]" in _unclean and _unclean != BAD17)
(_d19 / "未清核实.md").write_text(_unclean, encoding="utf-8")
u19 = run(["tools/proposal_readiness.py", str(_d19 / "未清核实.md"), "--no-progress", "--strict"])
uo19 = (u19.stdout or "") + (u19.stderr or "")
check("v190就绪度自检把未清的需核实报成缺项",
      u19.returncode == 1 and "还留着 [需核实]" in uo19, uo19[-400:])
check("v190同一把尺量干净大纲不误报（不空咬）",
      g17.returncode == 0 and "[需核实]" not in go17, go17[-300:])
check("v190工具仍只报问题不写文件",
      [p.name for p in _d19.iterdir()] == ["未清核实.md"]
      and "write_text" not in tx("tools/proposal_readiness.py"))

# ---- 5. 行为自测登记（改了引导行为就要有用例压测）----
_BTTXT = tx("tests/behavior-self-test.md")
_BT = sorted(int(x) for x in re.findall(r"^\| T(\d+) \|", _BTTXT, flags=re.M))
check("v190行为自测含T46-T49且编号连续",
      _BT == list(range(1, len(_BT) + 1)) and all(n in _BT for n in (46, 47, 48, 49)),
      "n=%d tail=%s" % (len(_BT), _BT[-5:]))
_STTXT = tx("doubao-skill/references/self-test.md")
_ST = sorted(int(x) for x in re.findall(r"^\| T(\d+) \|", _STTXT, flags=re.M))
check("v190轻量版自测含T44-T46且编号连续",
      _ST == list(range(1, len(_ST) + 1)) and all(n in _ST for n in (44, 45, 46)),
      "n=%d tail=%s" % (len(_ST), _ST[-5:]))
check("v190新用例各自指得回动作口径",
      all(k in _BTTXT for k in ("仅摘要", "已落盘的错条目", "均未检索到", "不得进正式稿"))
      and all(k in _STTXT for k in ("仅摘要", "搜不到", "逐字原文")))

# ---- 6. P15（v1.94）：被催短与要更正从"写在文档里"变成"有尺量" ----
# 用户 09-20 的原话是"道歉这种就不必写这么多，AI 会自己懂道歉的"——所以两把尺**只量形式在不在**，
# 不量语气、不量有没有认错；写进规则的规矩自己也按"规则算功能"验收。
_C3 = tx("CONSTITUTION.md").split("## 第三条")[1].split("## 第四条")[0]
check("v194宪法第三条多了第五形制被催短不掉形",
      all(k in _C3 for k in ("被催短不掉形", "状态标记", "30–60 秒")), _C3[:180])
check("v194最低形式三样两侧纪律都在位（镜像不缺边）",
      all(all(k in t for k in ("最低形式", "状态标记", "一句为什么", "30–60 秒"))
          for t in (tx("core/evidence-rigor.md"), tx("doubao-skill/references/evidence-rigor.md"))))
check("v194两份产出前门禁都加了这条勾",
      all("最低形式三样" in tx(f) for f in ("core/coaching-protocol.md",
                                            "doubao-skill/references/coaching-protocol.md")))
check("v194手机合并单文件带上这一节", "最低形式" in tx("doubao-skill/thesis-ai-coach-手机版.md"))
_p15 = run(["tests/rigor_pressure.py"], t=60)
po15 = (_p15.stdout or "") + (getattr(_p15, "stderr", "") or "")
check("v194两把尺对五份植入坏回答全部判红（尺不空转）",
      _p15.returncode == 0 and "漏抓" not in po15 and po15.count("[抓到]") == 5, po15[-300:])
check("v194实测结论照实写着第十节测不出增益",
      "测不出增益" in po15 and "已解决" not in po15.split("诚实边界")[-1], po15[-260:])
_PP = tx("tests/rigor_pressure.py")
check("v194压力实验的夹具与词表不抄第二份（单源）",
      "from rigor_experiment import" in _PP and "_MARK = (" not in _PP and "def _放行" not in _PP,
      "抄了第二份就会和原件漂")
check("v194用例登记里两条都指向这把尺",
      "judge_floor" in tx("tests/behavior-self-test.md")
      and "judge_correct" in tx("tests/behavior-self-test.md")
      and "最低形式" in tx("doubao-skill/references/self-test.md"))
# 报告在仓库外的 _归档（不随包分发）：开发树里必须已落盘，干净副本自然跳过
_rep94 = ROOT.parent / "_归档" / "审查报告" / "2026-09-20 被催短与更正的形制下界实验.md"
if _rep94.exists():
    _t94 = _rep94.read_text(encoding="utf-8")
    check("v194实验报告归档且写了测不出增益与三处自纠",
          all(k in _t94 for k in ("n=1", "测不出增益", "摘录删过头", "假阴性", "道歉"))
          and "全部判红" in _t94, _rep94.name)


