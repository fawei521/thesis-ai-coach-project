# -*- coding: utf-8 -*-
"""case_40 · 第五批对照（两校 31 篇**全文版**学位论文）落进表里：五行改动各自配闸。
和 case_39 同一个道理——**闸必须跟着这一批一起长**，否则下一批换所学校、换个体裁照样全绿。

**这一片管五件事**：
  ① **形制回不去**：「语病·介宾颠倒」必须带着 `(?<!叫)`（旧写法把教材定义句「把…叫做…」判成缺项，
     学生把含附录的整份稿子交给第 24 项时，一句课本原文就拦住交付）；「强调符号」内层必须禁中文标点、
     前后必须不吃连串星号（团体辅导方案里的脱敏占位「我叫**、是**族」不是加粗）；「立足于」不许回到
     AI 高频动词那行（121 篇里 5 篇在用、其中 1 篇是已发表论文）；「面向读者说话」缺项行只准留
     「让我们一起／你有没有想过」两词，被摘出的三词必须在**提示**档那一行里。
  ② **收窄是双向的**：真「把 Y 对 X 做回归」照报，「叫做」放行；真加粗照报，脱敏星号与表注星号放行；
     「置信区间**为** 0.01, 0.06」现在要报（这是补口子，不是收窄）。
  ③ **拦交付这件事必须可复现**：一段带着本批五种合规写法的稿子，现行表下 `--strict` 必须放行；
     把被摘掉的词与旧正则植回表尾，同一段必须立刻被判缺项——这条红＝有人把那几行改回去了。
  ④ **闸跟着对照实验长**：语料里要有第五批原句（≥6 句，出处带 SH／ZH 两字母档号），整份语料在新表下零缺项，
     并且往表尾植一行「缺项·立足于」必须让语料闸判红——同时**正常稿子上它不许报**（防"逢加行必红"的空转闸）。
  ⑤ **判不了的写进文案**：摘到提示档那三词必须写明"两处才报、单处交给三问第 3 问"，
     不许有人把它搬回缺项档图省事。

变量前缀 _h110e*：与 case_37／38／39 各自独立，前缀撞开会静默互相覆盖（见 case_20 的教训）。
"""
_h110e_mod = {"__name__": "style_check_110e", "__file__": str(ROOT / "tools" / "style_check.py")}
exec(compile(tx("tools/style_check.py"), "tools/style_check.py", "exec"), _h110e_mod)
_h110e_rows, _h110e_err = _h110e_mod["load_bans"]()
check("v111 判据表解析成功（半套判据上谈收窄没有意义）",
      _h110e_rows is not None and not _h110e_err, str(_h110e_err)[:200])
_h110e_rows = _h110e_rows or []
_h110e_by = {}
for _h110e_r in _h110e_rows:
    _h110e_by.setdefault(_h110e_r["cat"], []).append(_h110e_r)
_h110e_spec = tx("core/academic-style.md")


def _h110e_hit(text, rows=None):
    out = [m for k, m in _h110e_mod["ban_hits"](rows or _h110e_rows, text)]
    return out


def _h110e_pat(cat):
    rs = _h110e_by.get(cat, [])
    return rs[0]["pat"].pattern if rs and rs[0]["use"] == "正则" else ""


# ---- ① 形制回不去 ----
check("v111「介宾颠倒」带着 (?<!叫)（旧写法撞教材定义句「我们把∠A的对边a与斜边c的比叫做∠A的正弦」，"
      "那是缺项档、--strict 为一篇干净稿拦交付）",
      "(?<!叫)" in _h110e_pat("语病·介宾颠倒"), _h110e_pat("语病·介宾颠倒")[:120])
_h110e_qd = _h110e_pat("强调符号")
check("v111「强调符号」内层禁了中文标点、且前后不吃连串星号（第五批冤枉的是脱敏占位「我叫**、是**族」与「***后面的***」）",
      "、" in _h110e_qd and "(?<" in _h110e_qd and "(?!" in _h110e_qd, _h110e_qd[:150])
_h110e_ljz = [r["cat"] for r in _h110e_rows if r.get("terms") and "立足于" in r["terms"]]
check("v111「立足于」已不在任何词表行里（121 篇 5 篇在用、含 1 篇已发表论文；撤过的词不许补回）",
      not _h110e_ljz, "又回到了：" + "、".join(_h110e_ljz))
_h110e_rq = _h110e_by.get("面向读者说话", [])
_h110e_tip = _h110e_by.get("面向读者说话·真人在用", [])
check("v111「面向读者说话」缺项行只剩两个零人使用的词（让我们一起／你有没有想过）",
      len(_h110e_rq) == 1 and _h110e_rq[0]["tier"] == "缺项"
      and set(_h110e_rq[0]["terms"]) == {"让我们一起", "你有没有想过"},
      str([r["terms"] for r in _h110e_rq])[:120])
check("v111 摘出的三词确实落在提示档那一行（拆行不是删判据）",
      len(_h110e_tip) == 1 and _h110e_tip[0]["tier"] == "提示"
      and set(_h110e_tip[0]["terms"]) == {"我们可以看到", "相信大家都", "不难想象"},
      str([r["terms"] for r in _h110e_tip])[:120])

# ---- ② 收窄双向 ----
_h110e_ok = (
    "本研究以某市两所初中 412 名学生为样本，2021 年 3 月至 5 月分两轮施测，回收量表 397 份，有效回收率 96.4%。\n"
    "第二轮由班主任在班会课组织填写，学生自愿参加并可中途退出，平均作答时长 12.6 分钟，剔除规律作答的 9 份后进入分析。\n"
    "如图 2，在直角三角形中，∠C=90o。我们把∠A 的对边 a 与斜边 c 的比叫做∠A 的正弦，记作 sinA——这段教材原文作为实验材料照抄进附录。\n"
    "热身活动环节由第一个成员开始说说我叫**、是**族、我家在**、我是**班的学生，成员用星号匿名后再复述一遍。\n"
    "表 3 注：*表示p＜0.05，**表示p＜0.01，***表示p＜0.001，下同。\n"
    "M1：觉性的平等以真实为前提条件，基于我们可以看到真相，我们才能把这种平等给呈现出来。\n"
    "带领者在第五单元说：好的，谢谢这位同学的分享。我相信大家都一定会或多或少的感受到正念训练带来的益处。\n"
    "本研究也是立足于初中生心理发展特点设计与实施课程，回顾以往的研究成果，我们可以看到研究对象与研究领域的差异，"
    "据此调整了取样框架，并在预测试阶段把两处题意含混的题目改写给三年级两个班复测。\n")
check("v111 教材定义句『叫做』放行（阴性：本批 S22 一句咬 8 处、且它是缺项档）",
      not [m for m in _h110e_hit(_h110e_ok) if "介宾颠倒" in m],
      str([m for m in _h110e_hit(_h110e_ok) if "介宾颠倒" in m])[:140])
for _h110e_pos, _h110e_key in (("把心理健康对自尊做回归分析，看哪一个更能预测结果。", "介宾颠倒"),
                               ("把这些变量对班级均值做中心化处理后进入多层线性模型。", "介宾颠倒"),
                               ("这一点**必须在方法章交代**，别留给答辩现场问。\n本研究的**主要发现**有三条，逐条见表 4。", "强调符号"),
                               ("该间接效应为 0.03，置信区间为 0.01, 0.06，另一条路径置信区间为 0.003, 0.05。", "区间写法")):
    check("v111 真错照报：%s（阳性：收窄不是把这行收没了）" % _h110e_key,
          bool([m for m in _h110e_hit(_h110e_pos) if _h110e_key in m]),
          str(_h110e_hit(_h110e_pos))[:140])
check("v111 脱敏星号与表注星号一起放行（阴性：两种形制都不是 markdown 加粗）",
      not [m for m in _h110e_hit(_h110e_ok) if "强调符号" in m],
      str([m for m in _h110e_hit(_h110e_ok) if "强调符号" in m])[:140])
check("v111 研究定位句『立足于』不报（阴性：摘词之后这一段不该再出现该类别）",
      not [m for m in _h110e_hit(_h110e_ok) if "AI 高频动词" in m],
      str([m for m in _h110e_hit(_h110e_ok) if "AI 高频动词" in m])[:140])
_h110e_tipk = [(k, m) for k, m in _h110e_mod["ban_hits"](_h110e_rows, _h110e_ok) if "面向读者说话" in m]
check("v111 合规稿里那三词绝不进缺项档（阴性：缺项＝一句都不该有，而五批 121 篇里只有人在写、各一处）",
      not [m for k, m in _h110e_tipk if k == "缺项"], str(_h110e_tipk)[:170])
check("v111 同一段确实触发提示档（阳性：降档不是删档——夹具里故意写了三处，两处以上就该提醒）",
      any(k == "提示" for k, m in _h110e_tipk), str(_h110e_tipk)[:170])

# ---- ③ 这一段在 CLI 上真能交；把旧写法植回去就必须拦 ----
_h110e_tmp = new_tmp("v111e")
_h110e_p = _h110e_tmp / "合规稿.md"
_h110e_p.write_text(_h110e_ok, encoding="utf-8")
_h110e_r = run(["tools/style_check.py", str(_h110e_p), "--strict"])
check("v111 带着本批五种合规写法的稿子在现行表下 --strict 放行（改前这类稿子 31 篇里拦 5 篇，带附录再拦 1 篇）",
      _h110e_r.returncode == 0 and "【缺项】" not in _h110e_r.stdout,
      "rc=%d；%s" % (_h110e_r.returncode, re.sub(r"\s+", " ", _h110e_r.stdout)[:160]))
_h110e_old = _h110e_tmp / "植回旧写法.md"
_h110e_old.write_text(
    _h110e_spec + "\n| 缺项 | 夹具自造旧介宾 | 把[^，。；]{1,16}对[^，。；]{1,16}做 | 正则 | 只为验闸：丢掉 (?<!叫) 必须重新拦下这段 |\n"
    "| 缺项 | 夹具自造旧面向读者 | 我们可以看到,相信大家都,不难想象 | 包含 | 只为验闸：三词搬回缺项必须拦 |\n"
    "| 缺项 | 夹具自造旧立足于 | 立足于 | 包含 | 只为验闸：摘掉的词回表必须判红 |\n", encoding="utf-8")
_h110e_orows, _ = _h110e_mod["load_bans"](_h110e_old)
_h110e_block = [m for k, m in _h110e_mod["ban_hits"](_h110e_orows or [], _h110e_ok) if k == "缺项"]
check("v111 把三条旧写法植回表尾，同一段必须立刻被判缺项（这条红＝有人把那几行改回去了）",
      len(_h110e_block) >= 3 and any("旧介宾" in m for m in _h110e_block)
      and any("旧面向读者" in m for m in _h110e_block) and any("旧立足于" in m for m in _h110e_block),
      str(_h110e_block)[:170])

# ---- ④ 语料跟着第五批长大 ----
_h110e_corpus = tx("tests/test-data/已发表原句.md")
_h110e_lines = [l for l in _h110e_corpus.splitlines()
                if len(re.findall(r"[一-鿿]", l)) >= 16 and not l.strip().startswith((">", "#", "|"))]
_h110e_b5 = [l for l in _h110e_lines if re.search(r"（(苏州大学|石河子大学)学位论文·[SZ]H\d{2}）$", l.strip())]
check("v111 语料里有第五批学位论文原句（≥6 句，出处带 SH／ZH 两字母档号）——闸的覆盖面必须跟着对照实验长",
      len(_h110e_b5) >= 6, "%d 句 / 共 %d 句" % (len(_h110e_b5), len(_h110e_lines)))
_h110e_cmiss = [m for k, m in _h110e_mod["ban_hits"](_h110e_rows, _h110e_corpus) if k == "缺项"]
check("v111 整份语料（含第五批 6 句）在新表下零缺项", not _h110e_cmiss, str(_h110e_cmiss)[:170])
_h110e_ctl = [m for k, m in _h110e_mod["ban_hits"](_h110e_orows or [],
               "本研究考察了孤独感与自伤的关系，样本 268 人，2021 年 4 月施测，α 系数 0.86。") if k == "缺项"]
check("v111 那道闸不许变成『逢加行必红』：正常稿子上三行植入臂都不报缺项（阴性对照）",
      not _h110e_ctl, str(_h110e_ctl)[:150])

# ---- ⑤ 判不了的写进文案，别偷偷搬回词条 ----
_h110e_tipln = [l for l in _h110e_spec.splitlines() if "面向读者说话·真人在用" in l]
check("v111 提示档那一行写明了『两处以上才提醒、单处交给三问第 3 问』——降档的理由要在场，"
      "否则下个会话会把它当漏网补回缺项",
      _h110e_tipln and "两处" in _h110e_tipln[0] and "三问" in _h110e_tipln[0], str(_h110e_tipln)[:150])
check("v111 行为账 T89 在位（被冤枉过的学生问『是不是我写错了』时该怎么答）",
      "| T89 |" in tx("tests/behavior-self-test.md"), "T89 没登记")
