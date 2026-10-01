# -*- coding: utf-8 -*-
"""case_32 · 语病判据进表：合规稿放行在前、植入病句必须逐条咬住在后，顺序不许倒。

这一片只管三件事，都在回答"这把尺是不是真在量语言"：
  ① **放行**：一份没有语病的稿子必须一条不报——先验这条，是因为"只咬人的尺不算尺"，
     本仓已经为同义词假阴性栽过四次（把合规写法判成病句，比漏判更坏：它会把好稿子改坏）。
  ② **咬住**：16 类病句逐条植入，每类都要由**它自己那一行**报出来，
     不接受"反正有别的行在响"——短夹具必然撞上 `须有` 那行，混在一起就验不出真判据。
  ③ **改表即改判据**：把某一行的词条删掉，那条判据当场失效；加一行，当场生效。

变量前缀 _h105*：片段与壳共用 globals，撞名会静默改掉后面片段的运行环境（case_20 的教训）。
"""
_h105_spec = tx("core/academic-style.md")

_h105_clean = """本研究以班级为单位施测，回收有效问卷 268 份，各题项均无缺失值。
非自杀性自伤是指个体在不具自杀意图的前提下故意伤害自身躯体组织的行为。
差异不大。四个量表的内部一致性良好，孤独感量表与反刍思维量表各 4 题，α 如表 1 所示。
施测由主试宣读统一指导语后开始，题目按固定顺序呈现，作答过程中不解释题意，收回后当场核对份数，
这份清单在附录里可以逐条对上。
以 NSSI 总分为因变量、AI 情感依赖为自变量建立一元回归，模型显著，F(1, 266) = 12.39，p < .001。
回归系数 B = 0.22，SE = 0.06，标准化系数 β = .21，达到显著水平，这说明测量与统计口径均可接受。
中介检验的结果分三路。链式路径的置信区间为 [.02, .07]，不含 0，其标准误为 .01，
小于两条单一路径的 .02，因此判定只有串行通道成立，假设 H4 得到支持。
直接效应在纳入两个中介之后仍然显著，其区间下限接近 0，据此判断为部分中介，先后次序仍需追踪设计检验。"""

_h105_plant = [
    ("语病·句式杂糅", "该结果偏小的原因是样本量不足造成的。被试 268 人，量表信度见附录。"),
    ("语病·介宾颠倒", "把 NSSI 总分对 AI 情感依赖做一元回归，模型显著。被试 268 人施测。"),
    ("语病·各字无所指", "孤独感量表 4 题，反刍思维量表各 4 题，均为 5 点计分。被试填答问卷。"),
    ("语病·术语与谓语不搭", "两条单一路径含 0，据此判定为不显著。样本为大学生。"),
    ("语病·所有格后缺中心语", "AI 情感依赖对 NSSI 的 B = 0.221，达到显著。被试 268 人。"),
    ("语病·标记替句子当成分", "问卷在【待补：施测场地】完成，当场回收记录份数。被试为学生。"),
    ("语病·标记替句子当成分", "本研究采取【待补：方便抽样】的方式，回收有效问卷 268 份。量表信度良好。"),
    ("语病·负零舍入残留", "该路径的 95% CI 为 [−.00, .06]，区间包含 0。样本 268 人，问卷施测。"),
    ("设问句进正文", "转向之后会怎样？合理的推测不是 AI 直接把人推向自伤。被试 268 人。"),
    ("口语量词与泛指", "这么一来，那些个负面体验就好处理了，模型也就说得通了。样本为学生。"),
    ("日常动词冒替术语", "已有工作多把人机交互的强度记作使用时长。被试 268 人施测问卷。"),
    ("日常动词冒替术语", "这为理解该问题提供了一个更细的解释入口。量表测量孤独感。"),
    ("语病·主谓搭配不当", "反刍思维与自伤的关系更成熟。被试填写问卷。"),
    ("语病·主谓搭配不当", "模型能带走的方差不足二十分之一。样本 268 人施测问卷。"),
    ("语病·主谓搭配不当", "性别与年级上的差异一个都没跑出来。被试施测问卷。"),
    ("语病·主谓搭配不当", "这条判据偏松，不足以支撑结论。量表信度可接受。"),
]

# ---- ① 先验放行：好稿子过不了这条，后面全不用跑 ----
_h105_cleand = new_tmp("v105")
_h105_cleanp = _h105_cleand / "无语病稿.md"
_h105_cleanp.write_text(_h105_clean, encoding="utf-8")
_h105_rc = run(["tools/style_check.py", str(_h105_cleanp), "--strict"])
check("v105 无语病稿必须放行（缺项与风险都零条，否则新判据是在误伤）",
      "【缺项】" not in _h105_rc.stdout and "【风险】" not in _h105_rc.stdout and _h105_rc.returncode == 0,
      _h105_rc.stdout[:260])

# ---- ② 再验咬住：逐类按**类别名**对账，不接受"别的行也在响" ----
_h105_mod = {"__name__": "style_check_105", "__file__": str(ROOT / "tools" / "style_check.py")}
exec(compile(tx("tools/style_check.py"), "tools/style_check.py", "exec"), _h105_mod)
_h105_rows, _h105_err = _h105_mod["load_bans"]()
check("v105 判据表解析成功（读不出就整片作废，不许带着半套判据说没抓到）",
      _h105_rows is not None and not _h105_err, str(_h105_err)[:200])
_h105_rows = _h105_rows or []
_h105_cats = {r["cat"] for r in _h105_rows}
_h105_absent = [c for c, _ in _h105_plant if c not in _h105_cats]
check("v105 语病类判据确实进了表（表里没有这行＝夹具在验一条不存在的判据）",
      not _h105_absent, "缺：" + "、".join(sorted(set(_h105_absent))))
_h105_miss = []
for _h105_want, _h105_s in _h105_plant:
    _h105_hit = _h105_mod["ban_hits"](_h105_rows, _h105_s)
    if not any(_h105_want in m for _, m in _h105_hit):
        _h105_miss.append(_h105_want)
check("v105 16 类病句逐条由自己那一行咬住（不看总数，看是不是该行在响）",
      not _h105_miss, "漏：" + "、".join(sorted(set(_h105_miss))))

# ---- ③ 改表即改判据：删一行当场失效，加一行当场生效 ----
_h105_deld = new_tmp("v105del")
_h105_del = _h105_deld / "删掉一行.md"
_h105_del.write_text("\n".join(l for l in _h105_spec.splitlines()
                              if "语病·句式杂糅" not in l), encoding="utf-8")
_h105_drows, _ = _h105_mod["load_bans"](_h105_del)
_h105_dhit = _h105_mod["ban_hits"](_h105_drows or [], _h105_plant[0][1])
check("v105 删掉那一行，工具立刻不再抓它（判据只有表这一处，不在代码里）",
      not any("句式杂糅" in m for _, m in _h105_dhit), str(_h105_dhit)[:160])
_h105_add = _h105_deld / "加一行.md"
_h105_add.write_text(_h105_spec + "\n| 缺项 | 夹具自造语病词 | 咕咕倒装测试 | 包含 | 只为证明加一行就立刻生效 |\n",
                     encoding="utf-8")
_h105_arows, _ = _h105_mod["load_bans"](_h105_add)
_h105_ahit = _h105_mod["ban_hits"](_h105_arows or [], "这一段写了咕咕倒装测试，另有别的正文在里面。")
check("v105 往表里加一行语病判据，工具立刻开始抓（同源·加）",
      any("咕咕倒装测试" in m for _, m in _h105_ahit), str(_h105_ahit)[:160])

# ---- ④ 立场没动：加了语病判据也不许变成"检测对抗"工具 ----
check("v105 体检输出仍写着不测 AIGC 率与不替你改一个字",
      "不测 AIGC 率" in _h105_rc.stdout and "不替你改" in _h105_rc.stdout, _h105_rc.stdout[-260:])
check("v105 规范自己仍写明不做降率、学生正文改字归学生",
      "不做降率" in _h105_spec and "由学生自己改" in _h105_spec)
check("v105 规范把「定义句缺判断动词」留在第三节而不是写进表（写明是正则分不清，不是忘了）",
      "定义句缺判断动词" in _h105_spec and "没进表" in _h105_spec)
# ---- ⑩ 工序接线：语言闸必须挂在"阶段完成标志／每轮默查／开题清单"三处，否则跑不跑体检都能算完成 ----
_h105_pf = tx("core/coaching-protocol.md")
_h105_sp = tx("core/coach-rules/stage-playbook.md")
_h105_pg = tx("workflows/proposal-guide.md")
_h105_done = [l for l in _h105_sp.splitlines() if l.strip().startswith("- 完成标志") and "第 24 项" in l]
check("v105 阶段6 与阶段9 的完成标志都写了第 24 项缺项清零（不跑体检不能算这一阶段完成）",
      len(_h105_done) >= 2, "%d 处" % len(_h105_done))
check("v105 每轮回复前默查里有语言这一条，且写明它不替代证据那条",
      "菜单第 24 项" in _h105_pf and "互不替代" in _h105_pf)
check("v105 开题前检查清单加了体检那一格（学生自查看得见）",
      "style_check.py" in _h105_pg and "第 24 项" in _h105_pg)
check("v105 三道闸的口径没被改坏：动机／质量／留痕都还在",
      all(k in tx("core/coach-rules.md") for k in ("闸1：动机闸", "闸2：质量闸", "闸3：留痕闸")))
# 阴性：换一个没接线的文件跑同一批判据，必须全 False——全 True 就说明判据是空转的常量
_h105_ctl = tx("workflows/literature-auto-search.md")
check("v105 上面四条接线判据在无关文件上全不成立（阴性：不是写死的真）",
      not ("菜单第 24 项" in _h105_ctl or "style_check.py" in _h105_ctl and "第 24 项" in _h105_ctl
           or any(l.strip().startswith("- 完成标志") and "第 24 项" in l for l in _h105_ctl.splitlines())))
_h105_bt = tx("tests/behavior-self-test.md")

_h105_t = [l for l in _h105_bt.splitlines() if l.startswith(("| T74 |", "| T75 |", "| T76 |"))]
check("v105 行为用例 T74–T76 在位（规则也算功能，得有可判定的行为账）",
      len(_h105_t) == 3 and all("style_check.py" in l or "academic-style.md" in l for l in _h105_t),
      "%d 行" % len(_h105_t))
