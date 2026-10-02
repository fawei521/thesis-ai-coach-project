# -*- coding: utf-8 -*-
"""case_36 · v1.108 第二批真刊对照落进表里：拆行两侧、已证伪词条不许回表、降档双向、闸自己得能咬人。

**这一片管五件事**：
  ① **拆行是有两侧的**：零命中的五个词留在缺项档（一句都不该有），真刊在用的六个词降到风险档（只报位置）。
     只验「六个词不在缺项」而不验「五个词还在缺项」，就等于把一行判据删了充数。
  ② **撤过的词条不许被顺手补回来**：『系统梳理』『凸显了』『被广泛认为』『在某种程度上』都有真刊原句对着，
     下个会话若拿「AI 爱用」当理由加回去，这条当场红。
  ③ **两处降档各自双向**：设问句与『对…进行…』降到提示档后，一处不报（阴性，规范稿就写一处）、多处照报（阳性）。
  ④ **主谓那行是形状错，不是口味**：收窄后『系统日趋成熟』『人机关系成熟度』都不报，而『关系更成熟』照报。
  ⑤ **闸不再是快照**：语料里必须有第二批原句；并且往表尾植一行『缺项·赋能』必须让语料闸判红——
     2026-10-02 实测旧语料拦不住这一行（四个植入臂全绿），这一条就是把那一格补上的。

变量前缀 _h108*：片段与壳共用 globals，撞名会静默改掉后面片段的运行环境（见 case_20 的教训）。
"""
_h108_mod = {"__name__": "style_check_108", "__file__": str(ROOT / "tools" / "style_check.py")}
exec(compile(tx("tools/style_check.py"), "tools/style_check.py", "exec"), _h108_mod)
_h108_rows, _h108_err = _h108_mod["load_bans"]()
check("v108 判据表解析成功（读不出就整片作废，不许带着半套判据说收窄过了）",
      _h108_rows is not None and not _h108_err, str(_h108_err)[:200])
_h108_rows = _h108_rows or []
_h108_by = {}
for _h108_r in _h108_rows:
    _h108_by.setdefault(_h108_r["cat"], []).append(_h108_r)

_hard = _h108_by.get("宣传话术", [])
_soft = _h108_by.get("宣传话术·真刊在用", [])
_h108_kept = ["抓手", "顶层设计", "有力支撑", "必然趋势", "协同联动"]
_h108_demoted = ["赋能", "闭环", "有效提升", "高度契合", "深度融合", "底层逻辑"]
check("v108 缺项档只剩两批 45 篇零命中的那五个词（真刊在用的一律不许留在这一档）",
      len(_hard) == 1 and _hard[0]["tier"] == "缺项" and set(_hard[0]["terms"]) == set(_h108_kept),
      str([(r["tier"], r["terms"]) for r in _hard])[:170])
check("v108 那六个真刊在用的词降到风险档，一个都没丢（拆行不是删行）",
      len(_soft) == 1 and _soft[0]["tier"] == "风险" and set(_soft[0]["terms"]) == set(_h108_demoted),
      str([(r["tier"], r["terms"]) for r in _soft])[:170])

_h108_back = []
for _h108_cat, _h108_words in (("AI 高频动词", ["系统梳理", "凸显了"]),
                               ("翻译腔", ["被广泛认为", "在某种程度上"])):
    for _h108_r in _h108_by.get(_h108_cat, []):
        _h108_back += ["%s>%s" % (_h108_cat, w) for w in _h108_words if w in _h108_r.get("terms", [])]
check("v108 两批连续证伪过的四个词条不在表里（拿『AI 爱用』当理由补回来＝冤枉已发表论文）",
      not _h108_back, "又回来了：" + "、".join(_h108_back))

_h108_softrows = [(c, _h108_by[c][0]["tier"]) for c in ("设问句进正文", '空转的"对…进行…"') if c in _h108_by]
check("v108 设问句与名词化『对…进行…』都在提示档（两批 45 篇里 27 篇与 12 篇在用，不该算风险）",
      len(_h108_softrows) == 2 and all(t == "提示" for _, t in _h108_softrows), str(_h108_softrows))

_h108_one = "本研究对被试的风险倾向得分进行分析。转向之后会怎样？合理的推测不是 AI 替学生做决定。"
_h108_many = ("本研究对被试的风险倾向得分进行分析。\n对成人的评价问题回答进行分析，对聪明的迫选回答进行分析。\n"
              "转向之后会怎样？\n把人直接推向自伤的又是什么？合理的推测不是 AI 替学生做决定。\n被试 268 人，量表信度见附录。")
_h108_o1 = [m for _, m in _h108_mod["ban_hits"](_h108_rows, _h108_one) if "设问句" in m or "进行" in m]
_h108_o2 = [m for _, m in _h108_mod["ban_hits"](_h108_rows, _h108_many) if "设问句" in m or "进行" in m]
check("v108 一处设问、一处『对 X 进行分析』必须放行（阴性：规范稿就这么写，降档要降出效果）",
      not _h108_o1, str(_h108_o1)[:170])
check("v108 满篇设问与名词化堆叠照报（阳性：降档不等于撤掉）", len(_h108_o2) == 2, str(_h108_o2)[:170])

_h108_zhu = [r for r in _h108_by.get("语病·主谓搭配不当", []) if "成熟" in r["pat"].pattern]
_h108_fp = ["随着学龄段增长,个体的认知控制与情绪调节系统日趋成熟,社会观点采择能力显著提升。",
            "并强调模式的适应性转换能力是衡量人机关系成熟度的关键指标。"]
_h108_tp = "反刍思维与自伤的关系更成熟。两个变量之间的关系已经相当成熟。"
_h108_fired = [s[:24] for s in _h108_fp if _h108_zhu and _h108_zhu[0]["pat"].search(s)]
check("v108 主谓那行只认『关系』当主语：两处真刊原句都不报（旧写法把系统、成熟度一起吞了）",
      len(_h108_zhu) == 1 and not _h108_fired, str(_h108_fired)[:150])
check("v108 收窄后仍咬得住真病句（阳性：这条不是被磨钝了）",
      bool(_h108_zhu) and _h108_zhu[0]["pat"].search(_h108_tp), _h108_tp[:40])

_h108_corpus = tx("tests/test-data/已发表原句.md")
_h108_lines = [l for l in _h108_corpus.splitlines()
               if len(re.findall(r"[一-鿿]", l)) >= 16 and not l.strip().startswith((">", "#", "|"))]
_h108_b2 = [l for l in _h108_lines if re.search(r"（[^（）]*·[BCDE]\d{3,4}）$", l.strip())]
check("v108 语料里有第二批原句（≥12 句，出处带档号）——闸的覆盖面必须跟着对照实验长",
      len(_h108_b2) >= 12, "%d 句 / 共 %d 句" % (len(_h108_b2), len(_h108_lines)))
_h108_miss = [m for k, m in _h108_mod["ban_hits"](_h108_rows, _h108_corpus) if k == "缺项"]
check("v108 整份语料（含第二批 32 句）在新表下零缺项", not _h108_miss, str(_h108_miss)[:170])

_h108_tmp = new_tmp("v108")
_h108_table = _h108_tmp / "表植一行.md"
_h108_table.write_text(tx("core/academic-style.md") + "\n| 缺项 | 夹具自造宣传词 | 赋能 | 包含 | 只为验闸拦不拦得住 |\n",
                       encoding="utf-8")
_h108_prows, _ = _h108_mod["load_bans"](_h108_table)
_h108_gate = [m for k, m in _h108_mod["ban_hits"](_h108_prows or [], _h108_corpus) if k == "缺项"]
check("v108 植入一行『缺项·赋能』必须让语料闸判红（2026-10-02 旧语料拦不住它，四个臂全绿）",
      bool(_h108_gate) and any("赋能" in m for m in _h108_gate), str(_h108_gate)[:170])
_h108_ctl = [m for k, m in _h108_mod["ban_hits"](_h108_prows or [], "本研究考察了孤独感与自伤的关系，样本 268 人。")
             if k == "缺项"]
check("v108 那道闸不许变成『逢加行必红』：正常稿子上它不报缺项（阴性对照）", not _h108_ctl, str(_h108_ctl)[:150])

check("v108 立场没动：不做降率、改字归学生、改表即改判据三句都还在",
      all(k in tx("core/academic-style.md") for k in ("不做降率", "由学生自己改", "改表＝改判据")))
