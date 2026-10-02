# -*- coding: utf-8 -*-
"""case_31 · v1.104 学术语体规范：判据表与体检工具同源，而且这把尺分得开好坏稿子。

这一片只回答三件事：
  ① **同源是真的**——往表里加一个词条工具就抓、删一个就放（不是文档里的一句承诺）；
  ② **尺子不空转也不误伤**——植入的模板腔必须全咬住，一份合规的学术稿必须一条不报；
  ③ **表读坏了不许装检查过**——非法行必须报错退出，不能带着半套判据说"没抓到套话"。
变量前缀 _h104*：片段与壳共用 globals，撞名会静默改掉后续片段的运行环境（见 case_20 的教训）。
"""
_h104_good = """2024 年 11 月，研究者在城区一所初中与农村一所初中各施测一次，当场回收问卷 240 份，
回来先按作答时间过一遍，不足 90 秒的 11 份和整列选同一选项的 8 份剔掉，有效样本 208 人，有效回收率 86.7%。
被试初一到初三，13 到 16 岁，平均 14.6 岁，男生 98 人女生 110 人；两校各占约一半，
班主任协助维持秩序，学生当堂交卷不带走。施测前一周发放纸质知情同意，监护人回签 231 份，
未回签的 9 人不在样本里。自伤那三题放在问卷最后，前面加了一页求助渠道信息——这是导师要求加的，
理由是预测试时有学生在这一组题上空白，还有一名学生在下课后找了班主任。

孤独感取 8 题简版，1 到 4 级计分，本研究算得 α = .76。反刍思维 12 题，两个维度，α = .89。
自伤频次按自我报告清单计次，3 名被试该题缺失，按均值填补并写进附录。

孤独感与自伤频次呈显著正相关，r = .32，p < .01；与反刍思维的相关更高，r = .41，p < .001。
反刍思维与自伤频次的相关为 r = .35，p < .01。三个变量之间的相关方向都与假设一致。

以孤独感为自变量、反刍思维为中介变量预测自伤频次，间接效应 .07 到 .19，Bootstrap 5000 次，
95% CI [.07, .19]，区间不含 0。加入中介变量后直接效应缩小，t(205) = 1.12，p = .263，
据此判断反刍思维起部分中介作用。

这些结果只说明变量之间的关联。"""

_h104_bad = """随着心理健康问题日益受到学界重视，青少年自伤行为的深入研究具有重要的理论与实践意义。
本研究基于生态系统理论的视角，对孤独感与自伤的关系进行了深入的探讨，全面剖析了国内外相关文献，
为后续研究提供了参考。我们认为，孤独感不仅是一种主观体验，而且是一种社会性信号；它既是情绪层面的
困扰，又是认知层面的偏差。由此可见，二者的联合作用值得高度重视。

相关分析显示 r=0.32，p<0.05，α=0.76，t=3.41(207)，中介效应显著，充分说明了模型的合理性。
✅ 这一发现彻底解决了该领域长期存在的争议，为教育实践提供了有益借鉴，具有深远影响。

综上所述，本研究全方位、多角度地考察了青少年自伤问题，深度契合了当前心理健康工作的需要，
有力支撑了后续干预方案的落地。孤独感重要，反刍思维重要，干预时机同样重要。"""

_d104 = new_tmp("v104")
_h104_spec = tx("core/academic-style.md")
_h104_goodp = _d104 / "合规稿.md"
_h104_goodp.write_text(_h104_good, encoding="utf-8")
_h104_badp = _d104 / "模板腔稿.md"
_h104_badp.write_text(_h104_bad, encoding="utf-8")

# ---- ① 判据表解析：三档与五种用法都要有人在表里，缺一类就说明整段被删了（不写死条数） ----
_h104_mod = {"__name__": "style_check_104", "__file__": str(ROOT / "tools" / "style_check.py")}
exec(compile(tx("tools/style_check.py"), "tools/style_check.py", "exec"), _h104_mod)
_h104_rows, _h104_err = _h104_mod["load_bans"]()
check("v104 判据表解析成功（读不出就整片作废，不许带着半套判据跑）",
      _h104_rows is not None and not _h104_err, str(_h104_err)[:200])
_h104_rows = _h104_rows or []
check("v104 表里三档都有判据（缺项／风险／提示 少一类＝整段被删）",
      {r["tier"] for r in _h104_rows} == {"缺项", "风险", "提示"}, str(sorted({r["tier"] for r in _h104_rows})))
check("v104 表里五种用法都有判据（包含／句首／正则／配对／须有）",
      {r["use"] for r in _h104_rows} == set(_h104_mod["USES"]),
      str(sorted({r["use"] for r in _h104_rows})))

# ---- ② 同源：加词即抓、删词即放（这才叫"改表＝改判据"，不是文档里的一句话） ----
_h104_plus = _d104 / "表加一行.md"
_h104_plus.write_text(_h104_spec + "\n| 缺项 | 夹具自造词 | 咕咕测试词 | 包含 | 只为证明加一行就立刻生效 |\n",
                      encoding="utf-8")
_h104_rows_plus, _ = _h104_mod["load_bans"](_h104_plus)
_h104_hit = _h104_mod["ban_hits"](_h104_rows_plus or [], "这一段写了咕咕测试词，还有别的正文内容在里面。")
check("v104 往表里加一个词条，工具立刻开始抓它（同源·加）",
      any("咕咕测试词" in m for _, m in _h104_hit), str(_h104_hit)[:160])
_h104_minus = _d104 / "表删一行.md"
_h104_minus.write_text("\n".join(l for l in _h104_spec.splitlines() if "宣传话术" not in l), encoding="utf-8")
_h104_rows_minus, _ = _h104_mod["load_bans"](_h104_minus)
_h104_miss = _h104_mod["ban_hits"](_h104_rows_minus or [], "本研究为后续工作提供了闭环式的有效支撑。")
check("v104 从表里删掉那一行，工具立刻不抓（同源·删；判据只有表这一处）",
      not any("闭环" in m for _, m in _h104_miss), str(_h104_miss)[:160])

# ---- ③ 坏表不许静默：非法用法／空命中／正则编译不了，都要报错而不是少一条判据照样跑 ----
_h104_broken = _d104 / "表坏了.md"
_h104_broken.write_text("\n".join(
    (l.replace("| 包含 |", "| 随便写 |") if "宣传话术" in l else l) for l in _h104_spec.splitlines()), encoding="utf-8")
_h104_brows, _h104_berr = _h104_mod["load_bans"](_h104_broken)
check("v104 用法列写成非法值时报错而不是跳过那一行",
      _h104_brows is None and bool(_h104_berr), str(_h104_berr)[:160])
_h104_missing = _d104 / "表不在.md"
check("v104 判据文件读不到时同样报错（不是回退到内置词表）",
      _h104_mod["load_bans"](_h104_missing)[0] is None)
_h104_mod["SPEC"] = _h104_broken
_h104_r104 = _h104_mod["main"]([str(_h104_badp)])
check("v104 表坏时 main 退出码 2 并明说不假装检查过",
      _h104_r104 == 2, "退出码=%s" % _h104_r104)
_h104_mod["SPEC"] = ROOT / "core" / "academic-style.md"

# ---- ④ 分得开：模板腔全咬住、合规稿一条不报（价值判据，不是形状判据） ----
_h104_rb = run(["tools/style_check.py", str(_h104_badp), "--strict"])
_h104_rg = run(["tools/style_check.py", str(_h104_goodp), "--strict"])
check("v104 模板腔稿报缺项且 --strict 退出码 1",
      "【缺项】" in _h104_rb.stdout and _h104_rb.returncode == 1, _h104_rb.stdout[:160])
_h104_new = ["自由度位置", "图标进正文",
             "第一人称复数", "翻译腔", "AI 高频动词", "空转评价", "绝对化"]
_h104_gap = [w for w in _h104_new if w not in _h104_rb.stdout]
check("v104 本版新加的判据逐条咬住（写法与措辞两边都在）",
      not _h104_gap, "漏了：" + "、".join(_h104_gap))
check("v104 合规学术稿既不报缺项也不报风险（好稿子必须放行，否则这条判据是在误伤）",
      "【缺项】" not in _h104_rg.stdout and "【风险】" not in _h104_rg.stdout
      and _h104_rg.returncode == 0, _h104_rg.stdout[:220])
_h104_r104b = _h104_mod["ban_hits"](_h104_rows, _h104_bad)
check("v104 植入一段模板腔必须让它多报几条（阴性：尺子不空转）",
      len(_h104_r104b) >= 6, "%d 条" % len(_h104_r104b))

# ---- ⑤ 红线与立场一个字没动：不做降率、改字归学生、体检只报位置 ----
check("v104 体检输出仍带「不测 AIGC 率」与「不替你改」两句",
      "不测 AIGC 率" in _h104_rb.stdout and "不替你改" in _h104_rb.stdout)
check("v104 规范自己写明不做降率、不测检测、学生正文改字归学生",
      "不做降率" in _h104_spec and "不测 AIGC 率" in _h104_spec and "由学生自己改" in _h104_spec)
check("v104 学生侧四步工序标题没被搬走（writing-guide 第三节仍是权威源）",
      "把文字改回你自己的口吻（四步，重要）" in tx("workflows/writing-guide.md"))

# ---- ⑥ 接线：落笔前该读它的六个入口都在指，规范只有一份（旧的那份已收成指针） ----
_h104_entry = "core/academic-style.md"
_h104_wo = [(f, tx(f)) for f in ("START.md", "AGENTS.md", "core/coach-rules.md",
                                 "core/outcome-delivery.md", "workflows/writing-guide.md",
                                 "core/skill-sourcing.md")]
_h104_no = [f for f, t in _h104_wo if _h104_entry not in t]
check("v104 六个入口文档都指向语体规范", not _h104_no, "缺：" + "、".join(_h104_no))
check("v104 阶段细则里落了笔前必读（开题与写作两个阶段都指到）",
      tx("core/coach-rules/stage-playbook.md").count(_h104_entry) >= 2)
_h104_dup = [f for f in ("workflows/writing-guide.md", "workflows/proposal-guide.md")
             if "常见语言问题" in tx(f) or "空转词一个不留：" in tx(f)]
check("v104 旧的两份语言规范已收成指针（同一知识点不留第二处）",
      not _h104_dup, "还留着：" + "、".join(_h104_dup))
check("v104 交付纪律把体检条数写进了自检（不做才算没做到）",
      "core/academic-style.md" in tx("core/outcome-delivery.md")
      and "剩余条数" in tx("core/outcome-delivery.md"))

# ---- ⑦ 行为用例与机判不再两张皮 ----
_h104_bt = tx("tests/behavior-self-test.md")
_h104_t = [l for l in _h104_bt.splitlines() if l.startswith(("| T71 |", "| T72 |", "| T73 |"))]
check("v104 行为用例 T71–T73 在位且都点名可机判的入口",
      len(_h104_t) == 3 and all("style_check.py" in l or "academic-style.md" in l for l in _h104_t),
      "%d 行" % len(_h104_t))
check("v104 菜单第 24 项的说明指向判据表（学生改表不用改代码这句话要看得见）",
      "core/academic-style.md" in tx("tools/menu_thesis.py"))

# ---- ⑨ 这份规范必须跟着包走：工具的词表全靠它，挡在包外＝第 24 项第 0 步就报错 ----
#     判两条与名字无关的形状：① 它在 git 跟踪里（archive 只装跟踪文件）② 没人给它加 export-ignore。
#     `git ls-files` 在**没有 .git 的副本**里只会返回空——那是"查不到"不是"没有"，所以整个分支只在开发树跑（同 case_23 的先例）。
_h104_attr = tx(".gitattributes")
_h104_ign = [l.split()[0] for l in _h104_attr.splitlines()
             if "export-ignore" in l and not l.strip().startswith("#")]
_h104_shield = [g for g in _h104_ign
                if g.rstrip("/*") == "core/academic-style.md" or g.rstrip("/*") == "core"]
if (ROOT / ".git").is_dir():
    _h104_ls = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files", "core/academic-style.md"],
                              cwd=str(ROOT), capture_output=True)
    check("v104 判据文件已进 git 跟踪（archive 只装跟踪文件，没跟踪＝包里根本没有）",
          _h104_ls.stdout.decode("utf-8", "replace").strip() == "core/academic-style.md",
          "ls-files 返回：" + _h104_ls.stdout.decode("utf-8", "replace")[:80])
check("v104 判据文件没被 export-ignore 挡在包外（也不许把整层 core/ 挡掉）",
      not _h104_shield, "被挡：" + "、".join(_h104_shield))
_h104_ls = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files", "-z", "core/academic-style.md"],
                          capture_output=True, cwd=str(ROOT)).stdout.decode("utf-8").split("\0")
# 这条原本也拿 `git ls-files` 判"进没进包"，而学生副本里没有 `.git`，命令回空 → 副本必判红
# （2026-10-01 阶段 G 实测抓到，与 v1.103 那次同一族）。开发树的"已进跟踪"由上面那条带 `.git` 闸的检查管，
# 这里只问一件在两种形态下都成立的事：**解出来的包里到底有没有这份文件**。
check("v104 判据文件真的在包里（不在＝第 24 项第 0 步就报错）",
      (ROOT / "core" / "academic-style.md").is_file(), str(_h104_ls)[:120])

# ---- ⑧ 对照实验的尺子自测跑绿（GOOD 三条全过、BAD 的语体条必须判红） ----
_h104_x = run(["tests/style_experiment.py", "--demo"])
check("v104 语体对照实验的判据自测分得开（尺空不空转，不参与 A/B 结论）",
      _h104_x.returncode == 0 and "分得开" in _h104_x.stdout, _h104_x.stdout[-180:])
