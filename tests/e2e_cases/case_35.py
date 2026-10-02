# -*- coding: utf-8 -*-
"""case_35 · 判据对照已发表论文（v1.107）：真刊正文里出现过的写法，不许被判成"一句都不该有"。

这一片管四件事：
  ① **放行**：`tests/test-data/已发表原句.md` 那 16 句逐字原文在新表下必须**零缺项**——
     缺项档的定义就是"一句都不该有"，只要已发表论文正文里出现过一次，这条定义就被证伪了。
  ② **决定不是遗漏**：那四类"统计值省前导零"的类别名不许回到表里，规范第三节必须留着那条口径交代。
  ③ **收窄是双向的**：正文设问句照报（阳性），引号里的访谈题面不报（阴性）——只验一头就是空转。
  ④ **尺子还在咬**：往语料里植一句真缺项病句，必须报出来且 --strict 退出码 1。

变量前缀 _h107*：片段与壳共用 globals，撞名会静默改掉后面片段的运行环境（见 case_20 的教训）。
"""
_h107_corpus_rel = "tests/test-data/已发表原句.md"
_h107_corpus = tx(_h107_corpus_rel)
_h107_cjk = re.findall(r"[一-鿿]", _h107_corpus)
_h107_lines = [l for l in _h107_corpus.splitlines()
               if len(re.findall(r"[一-鿿]", l)) >= 16 and not l.strip().startswith((">", "#", "|"))]

# ---- ① 语料自己得够分量：短夹具撞不满词条，这坑 2026-10-01 那轮踩过（530 字节选的臂读不出差别）----
check("v107 已发表原句语料在位且有 1200 汉字以上（短了撞不满判据，放行就成了假绿）",
      len(_h107_cjk) >= 1200 and len(_h107_lines) >= 12,
      "%d 字 / %d 句" % (len(_h107_cjk), len(_h107_lines)))
_h107_nolabel = [l for l in _h107_lines if not re.search(r"（[^（）]{2,20}）$", l.strip())]
check("v107 语料每句都带出处（无出处的句子不知道是谁写的，冤枉了也没处对账）",
      not _h107_nolabel, "缺出处：" + "；".join(x[:24] for x in _h107_nolabel[:3]))

_h107_mod = {"__name__": "style_check_107", "__file__": str(ROOT / "tools" / "style_check.py")}
exec(compile(tx("tools/style_check.py"), "tools/style_check.py", "exec"), _h107_mod)
_h107_rows, _h107_err = _h107_mod["load_bans"]()
check("v107 判据表解析成功（读不出就整片作废，不许带着半套判据说零缺项）",
      _h107_rows is not None and not _h107_err, str(_h107_err)[:200])
_h107_rows = _h107_rows or []

# ---- ② 核心闸：已发表正文零缺项，工具侧与函数侧各核一遍（两道不是冗余，是同一条事实的两种取法）----
_h107_p = new_tmp("v107") / "已发表原句.md"
_h107_p.write_text(_h107_corpus, encoding="utf-8")
_h107_r = run(["tools/style_check.py", str(_h107_p), "--strict"])
_h107_hits = _h107_mod["ban_hits"](_h107_rows, _h107_corpus)
_h107_miss = [m for k, m in _h107_hits if k == "缺项"]
check("v107 16 句已发表原句必须零缺项（真刊出现过＝这条判据在冤枉规范写作）",
      "【缺项】" not in _h107_r.stdout and _h107_r.returncode == 0 and not _h107_miss,
      "工具rc=%d；函数侧缺项：%s" % (_h107_r.returncode, str(_h107_miss)[:180]))
_h107_tiers = sorted({k for k, _ in _h107_hits})
check("v107 语料上仍允许有风险／提示档命中（顶刊也会写脚手架句，这条闸只管缺项这一档）",
      set(_h107_tiers) <= {"风险", "提示"}, str(_h107_tiers))

# ---- ③ "省前导零"交人判：四类别名不许回表，且第三节那条口径交代必须在位 ----
_h107_cats = {r["cat"] for r in _h107_rows}
_h107_back = [c for c in ("阈值写法", "相关系数前导零", "标准系数前导零", "信度写法") if c in _h107_cats]
check("v107 那四类统计值前导零判据确实不在表里（它们量的是口径选择，不是错误）",
      not _h107_back, "又回来了：" + "、".join(_h107_back))
_h107_spec = tx("core/academic-style.md")
check("v107 规范第三节写着这条口径交人判，并要求定了就全篇统一（写明是决定，不是漏了）",
      "小数点前那个 0" in _h107_spec and "本包不替你定" in _h107_spec and "全篇统一" in _h107_spec)
check("v107 规范把专名（基金项目名称、量表名、被引标题）也归进语境误报，不为一个脚注行改判据",
      "专名同理" in _h107_spec and "基金项目名" in _h107_spec)

# ---- ④ 收窄是双向的：正文设问照报，引号里的题面不报 ----
_h107_pos = "因而,在我国疫情后期,青少年抑郁和焦虑变化轨迹作为疫情后期社会变迁的后果,是否会受到心理韧性这一积极心理品质的影响呢？为回答此问题,本研究提出假设。"
_h107_neg = "Shek等[9]在2000年采用个别访谈的方法，考察了亲子沟通的频率，访谈问题是“你与父亲/母亲交谈的频率如何？”结果发现，青少年报告与母亲的沟通频率更高。"
_h107_ppos = [m for k, m in _h107_mod["ban_hits"](_h107_rows, _h107_pos) if "设问句" in m]
_h107_pneg = [m for k, m in _h107_mod["ban_hits"](_h107_rows, _h107_neg) if "设问句" in m]
check("v107 正文设问句照报（阳性：收窄不能把判据收没了）", bool(_h107_ppos), str(_h107_ppos)[:140])
check("v107 引号内的访谈题面不报（阴性：问号落在引号里是必须照抄的原文）",
      not _h107_pneg, str(_h107_pneg)[:140])

# ---- ⑤ 防尺子空转：植一句真缺项病句，必须报缺项且退出码 1 ----
_h107_planted = _h107_corpus + "\n\n该结果偏小的原因是样本量不足造成的。被试 268 人，量表信度见附录。\n"
_h107_pp = new_tmp("v107p") / "植入病句.md"
_h107_pp.write_text(_h107_planted, encoding="utf-8")
_h107_rp = run(["tools/style_check.py", str(_h107_pp), "--strict"])
check("v107 往语料里植一句真缺项病句必须报出来（零缺项那条不是把尺子磨钝换来的）",
      "【缺项】" in _h107_rp.stdout and _h107_rp.returncode == 1
      and "句式杂糅" in _h107_rp.stdout, _h107_rp.stdout[:200])

# ---- ⑥ 立场没动：不测检测率、不替你改一个字 ----
check("v107 体检输出仍写着不测 AIGC 率与不替你改一个字（收窄判据不等于放开红线）",
      "不测 AIGC 率" in _h107_r.stdout and "不替你改" in _h107_r.stdout, _h107_r.stdout[-200:])
_h107_bt = tx("tests/behavior-self-test.md")
_h107_t = [l for l in _h107_bt.splitlines() if l.startswith(("| T81 |", "| T82 |"))]
check("v107 行为用例 T81–T82 在位（口径交人与语境误报这两件事也得有行为账，不是只改了表）",
      len(_h107_t) == 2 and all(("前导零" in l or "语境误报" in l or "专名" in l) for l in _h107_t),
      "%d 行" % len(_h107_t))
