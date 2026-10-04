# -*- coding: utf-8 -*-
"""case_37 · 第三批对照（24 篇心理学学位论文）落进表里：补词与收窄都要双向，闸得跟着这一批长大。

**这一片管四件事**：
  ① **形制回不去**：因果越界必须是「配对」（本研究…导致 这类同句形状），不许退回按词命中——
     旧写法在三批 69 篇真语料（45 篇期刊＋24 篇学位论文）里报下 53 篇，天天报等于没有提醒。
     研究对象与测量那行必须带着第三批补进来的学前／质性词（幼儿、教师、观察、访谈…）。
  ② **撤过的理由钉住**：「影响机制／内在机制」不许回到因果那一行——它是研究问题标签（学位论文 4/24 在用），
     不是因果宣称；下个会话拿"AI 爱写因果"当理由补回来，这条当场红。
  ③ **收窄是双向的**：自称因果的四句照报（阳性），引述前人结论／定义句／否定句放行（阴性）；
     学前方向的一段话不许报"通篇找不出研究对象"（第三批就是被这样冤枉的），纯套话段照报。
  ④ **闸跟着对照实验长**：语料里得有第三批原句（≥8 句，出处带学位论文档号），
     并且往表尾植一行「缺项·幼儿」必须让语料闸判红——只认旧样本的门槛等于没有门槛。

变量前缀 _h109*：片段与壳共用 globals，撞名会静默改掉后面片段的运行环境（见 case_20 的教训）。
"""
_h109_mod = {"__name__": "style_check_109", "__file__": str(ROOT / "tools" / "style_check.py")}
exec(compile(tx("tools/style_check.py"), "tools/style_check.py", "exec"), _h109_mod)
_h109_rows, _h109_err = _h109_mod["load_bans"]()
check("v109 判据表解析成功（读不出就整片作废，不许带着半套判据说收窄过了）",
      _h109_rows is not None and not _h109_err, str(_h109_err)[:200])
_h109_rows = _h109_rows or []
_h109_by = {}
for _h109_r in _h109_rows:
    _h109_by.setdefault(_h109_r["cat"], []).append(_h109_r)

# ---- ① 因果那行的形制 ----
_h109_yin = _h109_by.get("因果越界", [])
_h109_pairs = _h109_yin[0]["pairs"] if _h109_yin else []
check("v109 因果越界改成『配对』：要的是「自称结论＋因果动词落在同一行」这个形状，不再是裸词命中",
      len(_h109_yin) == 1 and _h109_yin[0]["use"] == "配对" and ("本研究", "导致") in _h109_pairs
      and ("结果", "导致") in _h109_pairs, str([(r["use"], r.get("pairs")) for r in _h109_yin])[:170])
_h109_left = [w for r in _h109_yin for w in (r.get("terms") or []) if "机制" in w]
_h109_back = [w for w in ("影响机制", "内在机制") if any(w in "%s" % (p,) for p in _h109_pairs)]
check("v109「影响机制／内在机制」不在因果那一行（它是研究问题标签，学位论文 4/24 在用，撤过不许补回）",
      not _h109_left and not _h109_back, "又回来了：" + "、".join(_h109_left + _h109_back))

# ---- ② 因果收窄的双向 ----
_h109_yang = ("本研究结果表明，孤独感导致青少年自伤风险上升。\n"
              "本研究进一步发现，反刍思维引起情绪持续恶化。\n"
              "数据显示，问题性网络使用造成睡眠剥夺。\n"
              "分析结果说明，学业压力导致情绪低落。")
_h109_yin_txt = ("张光骅（2014）提出负性情绪导致冲动决策，这一取向也引起广泛讨论。\n"
                 "故意造成身体组织损伤是非自杀性自伤的核心定义成分，不包括自杀意图。\n"
                 "孤独感与抑郁的关系是情绪影响机制研究的重点。")
# 配对档的文案不带类别名（它写的是「本研究…导致…这类句式连用 N 处」），
# 所以按"句式连用＋因果动词"认，别按类别名认——按类别名认会两头都空，阴性假绿。
def _h109_yin_hit(text):
    return [m for k, m in _h109_mod["ban_hits"](_h109_rows, text)
            if "这类句式连用" in m and ("导致" in m or "引起" in m)]
_h109_f_yang = _h109_yin_hit(_h109_yang)
_h109_f_yin = _h109_yin_hit(_h109_yin_txt)
check("v109 四句自称因果照报（阳性：收窄不能把判据收没了，也是这条过滤器自己的阳性自证）",
      len(_h109_f_yang) == 1 and "连用" in _h109_f_yang[0], str(_h109_f_yang)[:150])
check("v109 引述、定义句与术语放行（阴性：第三批 53/69 篇开火就是这三类语境撑起来的）",
      not _h109_f_yin, str(_h109_f_yin)[:150])

# ---- ③ 须有档补词的双向 ----
_h109_dxiang = _h109_by.get("研究对象与测量", [])
_h109_new = [w for w in ("幼儿", "儿童", "青少年", "教师", "家长", "观察", "访谈", "编码")
             if not _h109_dxiang or w not in _h109_dxiang[0]["terms"]]
check("v109 研究对象与测量带着第三批补进来的学前／质性词（旧词表只认「被试／学生／问卷」那一路）",
      len(_h109_dxiang) == 1 and _h109_dxiang[0]["use"] == "须有" and not _h109_new,
      "缺这些词：" + "、".join(_h109_new) if _h109_new else str(_h109_dxiang[0]["tier"]))
_h109_pre = "本研究以 96 名中班幼儿为对象，每周两次在自由游戏时段做事件取样观察，访谈记录由两名教师独立编码。"
_h109_vague = "本研究具有重要的理论意义与实践价值，为后续研究提供了参考，也奠定了理论基础，结果呈现出积极趋势。"
_h109_f_pre = [m for k, m in _h109_mod["ban_hits"](_h109_rows, _h109_pre) if "研究对象与测量" in m]
_h109_f_vague = [m for k, m in _h109_mod["ban_hits"](_h109_rows, _h109_vague) if "研究对象与测量" in m]
check("v109 学前方向的写法放行（阴性：两篇学前学位论文被报「一个都没有」，正文里「幼儿」几十次）",
      not _h109_f_pre, str(_h109_f_pre)[:150])
check("v109 通篇只有自我评价的稿子照报（阳性：补词是把网张开，不是撤掉这一行）",
      bool(_h109_f_vague), str(_h109_f_vague)[:150])

# ---- ④ 语料里有第三批，且闸认得这一族 ----
_h109_corpus = tx("tests/test-data/已发表原句.md")
_h109_lines = [l for l in _h109_corpus.splitlines()
               if len(re.findall(r"[一-鿿]", l)) >= 16 and not l.strip().startswith((">", "#", "|"))]
_h109_b3 = [l for l in _h109_lines if re.search(r"（石河子大学学位论文·[A-Z]{1,2}\d{2,3}）$", l.strip())]
check("v109 语料里有第三批学位论文原句（≥8 句，出处带档号）——闸的覆盖面必须跟着对照实验长",
      len(_h109_b3) >= 8, "%d 句 / 共 %d 句" % (len(_h109_b3), len(_h109_lines)))
_h109_miss = [m for k, m in _h109_mod["ban_hits"](_h109_rows, _h109_corpus) if k == "缺项"]
check("v109 整份语料（含第三批 13 句）在新表下零缺项", not _h109_miss, str(_h109_miss)[:170])
_h109_tmp = new_tmp("v109")
_h109_table = _h109_tmp / "表植一行.md"
_h109_table.write_text(tx("core/academic-style.md") + "\n| 缺项 | 夹具自造学前词 | 幼儿 | 包含 | 只为验闸拦不拦得住 |\n",
                       encoding="utf-8")
_h109_prows, _ = _h109_mod["load_bans"](_h109_table)
_h109_gate = [m for k, m in _h109_mod["ban_hits"](_h109_prows or [], _h109_corpus) if k == "缺项"]
check("v109 植入一行『缺项·幼儿』必须让语料闸判红（第三批冤枉的正是这一族：学前与质性方向的研究对象表述）",
      bool(_h109_gate) and any("幼儿" in m for m in _h109_gate), str(_h109_gate)[:170])
_h109_ctl = [m for k, m in _h109_mod["ban_hits"](_h109_prows or [], "本研究考察了孤独感与自伤的关系，样本 268 人。")
             if k == "缺项"]
check("v109 那道闸不许变成『逢加行必红』：正常稿子上它不报缺项（阴性对照）", not _h109_ctl, str(_h109_ctl)[:150])
