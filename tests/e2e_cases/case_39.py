# -*- coding: utf-8 -*-
"""case_39 · 第四批对照（21 篇苏州大学**全文版**学位论文）落进表里：三处形状错收窄、一条放行条件补上，
闸要跟着这一批一起长——否则下一批换个体裁照样全绿。

**这一片管五件事**：
  ① **形制回不去**：「所有格后缺中心语」必须带拉丁前缀要求（旧写法只认 `的`＋统计符号）；
     「强调符号」内层必须禁 p／＜／＝／数字（旧写法把表注里的显著性星号当成加粗）；
     「记作」不许回到日常动词冒替术语那行（它在四批 90 篇里只 1 篇用过，且用在质性编码信度公式上）。
  ② **收窄是双向的**：真病句「对 NSSI 的 B = 0.22」照报，比较句「由原来的β=0.44」放行；
     两处 markdown 加粗照报，两条表注星号（*p<.05／**表示p＜0.01 两种形制）放行。
  ③ **缺项档拦人这件事必须可复现**：一段带着本批三种合规写法的稿子，现行表下 `--strict` 必须放行；
     把旧正则植回表里，同一段必须被判缺项——**这条红就说明有人把拦交付的那行改回去了**。
  ④ **闸跟着对照实验长**：语料里得有第四批原句（≥4 句，出处（苏州大学学位论文·档号）），且整份语料在新表下零缺项；整份语料在新表下零缺项，
     并且往表尾植一行「缺项·记作」必须让语料闸判红。
  ⑤ **判不了的写进文案**：因果越界那一行必须同时写着「实验／干预」与「标签」两类放行——
     本批 4/4 开火全是这两类加引述，形状尺判不了研究设计，不许靠再加词条解决。

变量前缀 _h109c*：与 case_37／38 同一版，前缀撞开会静默互相覆盖（见 case_20 的教训）。
"""
_h109c_mod = {"__name__": "style_check_109c", "__file__": str(ROOT / "tools" / "style_check.py")}
exec(compile(tx("tools/style_check.py"), "tools/style_check.py", "exec"), _h109c_mod)
_h109c_rows, _h109c_err = _h109c_mod["load_bans"]()
check("v110 判据表解析成功（半套判据上谈收窄没有意义）",
      _h109c_rows is not None and not _h109c_err, str(_h109c_err)[:200])
_h109c_rows = _h109c_rows or []
_h109c_by = {}
for _h109c_r in _h109c_rows:
    _h109c_by.setdefault(_h109c_r["cat"], []).append(_h109c_r)
_h109c_spec = tx("core/academic-style.md")


def _h109c_hit(text, key=None):
    out = [m for k, m in _h109c_mod["ban_hits"](_h109c_rows, text)]
    return out if key is None else [m for m in out if key in m]


# ---- 合规稿：三种被冤枉过的写法都在里面 ----
_h109c_ok = (
    "本研究以 386 名基层公务员为样本，2023 年 3 月至 5 月分两轮施测，回收量表 361 份，有效回收率 93.5%。\n"
    "第一轮由所在单位人事部门发放问卷，参与者自愿填写并当场收回，平均作答时长 14.2 分钟，"
    "剔除连续同选项的 12 份后进入分析。\n"
    "加入心理授权这个中介变量后，专权领导对情绪衰竭的显著性系数降低"
    "（由原来的β=0.44, p<0.001 变成β=0.33, p<0.001），说明心理授权在两者之间起部分中介作用，假设 2a 得到支持；\n"
    "简单斜率检验显示，领导成员交换水平较低时该间接效应为 0.19，水平较高时降为 0.08。\n"
    "表 4 注：*表示p＜0.05，**表示p＜0.01，***表示p＜0.001，下同。\n"
    "注：表中系数为标准化回归系数𝛽，*p<.05，**p<.01，***p<.001。\n"
    "编码信度按两名研究者归类相同的个数计算，相同个数记作 TI∩T2，两人编码总数之和记作 TI∪T2，Kappa 系数为 0.81，"
    "访谈文本由第三名研究者复核，分歧处回到原始记录逐条讨论后形成一致编码，这段程序在预测试阶段重复过一次。\n")

# ---- ① 形制回不去 ----
_h109c_suo = _h109c_by.get("语病·所有格后缺中心语", [])
_h109c_pat = _h109c_suo[0]["pat"].pattern if _h109c_suo else ""
check("v110 所有格那行带着拉丁前缀要求（旧写法 `的\\s*[BβrR]=` 会撞上比较句「由原来的β=0.44」，"
      "而它是缺项档、--strict 就为这句拦下一篇规范学位论文）",
      len(_h109c_suo) == 1 and _h109c_suo[0]["use"] == "正则" and "A-Za-z" in _h109c_pat,
      str(_h109c_pat)[:120])
_h109c_qd = [r for r in _h109c_rows if r["cat"] == "强调符号"]
_h109c_qdpat = _h109c_qd[0]["pat"].pattern if _h109c_qd else ""
check("v110 强调符号的内层禁掉了 p／＜／＝／数字（旧写法在四批 90 篇里报 14 篇，绝大多数是表注的显著性星号）",
      len(_h109c_qd) == 1 and "0-9" in _h109c_qdpat and "p" in _h109c_qdpat.split("]")[0],
      str(_h109c_qdpat)[:120])
_h109c_ji = [r["cat"] for r in _h109c_rows if r.get("terms") and "记作" in r["terms"]]
check("v110「记作」已不在任何词表行里（90 篇里只 1 篇用过，且用在质性编码信度公式「个数记作 TI∩T2」；撤过不许补回）",
      not _h109c_ji, "又回到了：" + "、".join(_h109c_ji))

# ---- ② 收窄双向 ----
_h109c_yang = "回归系数表明，性别对 NSSI 的 B = 0.22，p<0.01，这一路径在 Bootstrap 5000 次后仍稳定。"
check("v110 真病句「对 NSSI 的 B = 0.22」照报（阳性：收窄不是把这行收没了）",
      bool([m for m in _h109c_hit(_h109c_yang) if "所有格" in m]), str(_h109c_hit(_h109c_yang))[:140])
check("v110 比较句「由原来的β=0.44 变成β=0.33」不再算缺项（阴性：本批唯一一次开火就是它，且它拦了交付）",
      not [m for m in _h109c_hit(_h109c_ok) if "所有格" in m],
      str([m for m in _h109c_hit(_h109c_ok) if "所有格" in m])[:140])
_h109c_bold = ("这一段必须**强调这个结论**，否则读者看不到重点在哪里；"
               "**这里也是加粗**，两处才报的口径在正文里同样成立。\n")
check("v110 两处真正的加粗照报（阳性：禁掉数字与 p 之后这条没变成哑巴）",
      bool([m for m in _h109c_hit(_h109c_bold) if "强调符号" in m]), str(_h109c_hit(_h109c_bold))[:140])
check("v110 两种表注星号形制一起放行（阴性：`*表示p＜0.05，**表示…` 与 `*p<.05，**p<.01` 都是期刊体例）",
      not [m for m in _h109c_hit(_h109c_ok) if "强调符号" in m],
      str([m for m in _h109c_hit(_h109c_ok) if "强调符号" in m])[:140])
check("v110 质性编码公式里的「记作」不报（阴性：摘词之后这一段整条不该再出现该类别）",
      not [m for m in _h109c_hit(_h109c_ok) if "日常动词冒替术语" in m],
      str([m for m in _h109c_hit(_h109c_ok) if "日常动词冒替术语" in m])[:140])

# ---- ③ 这一段在 CLI 上真能交；把旧正则植回去就必须拦 ----
_h109c_tmp = new_tmp("v110c")
_h109c_p = _h109c_tmp / "合规稿.md"
_h109c_p.write_text(_h109c_ok, encoding="utf-8")
_h109c_r = run(["tools/style_check.py", str(_h109c_p), "--strict"])
check("v110 带着三种合规写法的稿子在现行表下 --strict 放行（本批被拦的就是这一类稿子）",
      _h109c_r.returncode == 0 and "【缺项】" not in _h109c_r.stdout,
      "rc=%d；%s" % (_h109c_r.returncode, re.sub(r"\s+", " ", _h109c_r.stdout)[:150]))
_h109c_old = _h109c_tmp / "植回旧正则.md"
_h109c_old.write_text(_h109c_spec + "\n| 缺项 | 夹具自造旧所有格 | 的\\s*[BβrR]\\s*[=<>] | 正则 | 只为验闸：旧形状必须重新拦下这段 |\n",
                      encoding="utf-8")
_h109c_orows, _ = _h109c_mod["load_bans"](_h109c_old)
_h109c_block = [m for k, m in _h109c_mod["ban_hits"](_h109c_orows or [], _h109c_ok) if k == "缺项"]
check("v110 把旧写法植回表里，同一段必须立刻被判缺项（这条红＝有人把那行改回去了）",
      bool(_h109c_block) and any("旧所有格" in m for m in _h109c_block), str(_h109c_block)[:150])

# ---- ④ 语料跟着第四批长大 ----
_h109c_corpus = tx("tests/test-data/已发表原句.md")
_h109c_lines = [l for l in _h109c_corpus.splitlines()
                if len(re.findall(r"[一-鿿]", l)) >= 16 and not l.strip().startswith((">", "#", "|"))]
_h109c_b4 = [l for l in _h109c_lines if re.search(r"（苏州大学学位论文·[A-Z]{1,2}\d{2,3}）$", l.strip())]
check("v110 语料里有第四批学位论文原句（≥4 句，出处带苏州大学档号）——闸的覆盖面必须跟着对照实验长",
      len(_h109c_b4) >= 4, "%d 句 / 共 %d 句" % (len(_h109c_b4), len(_h109c_lines)))
_h109c_cmiss = [m for k, m in _h109c_mod["ban_hits"](_h109c_rows, _h109c_corpus) if k == "缺项"]
check("v110 整份语料（含第四批 4 句）在新表下零缺项", not _h109c_cmiss, str(_h109c_cmiss)[:170])
_h109c_t2 = _h109c_tmp / "植一行记作.md"
_h109c_t2.write_text(_h109c_spec + "\n| 缺项 | 夹具自造记作 | 记作 | 包含 | 只为验闸：摘掉的词若回表必须判红 |\n",
                     encoding="utf-8")
_h109c_r2, _ = _h109c_mod["load_bans"](_h109c_t2)
_h109c_gate = [m for k, m in _h109c_mod["ban_hits"](_h109c_r2 or [], _h109c_corpus) if k == "缺项"]
check("v110 往表尾植一行「缺项·记作」必须让语料闸判红（第四批冤枉的正是这一族写法）",
      bool(_h109c_gate) and any("记作" in m for m in _h109c_gate), str(_h109c_gate)[:150])
_h109c_ctl = [m for k, m in _h109c_mod["ban_hits"](_h109c_r2 or [], "本研究考察了孤独感与自伤的关系，样本 268 人，2023 年 4 月施测。")
              if k == "缺项"]
check("v110 那道闸不许变成『逢加行必红』：正常稿子上它不报缺项（阴性对照）", not _h109c_ctl, str(_h109c_ctl)[:150])

# ---- ⑤ 判不了的写在文案里，别偷偷变回词条 ----
_h109c_yin = [l for l in _h109c_spec.splitlines() if "因果越界" in l]
check("v110 因果越界那行同时写着两类放行（实验／干预的操纵因果、研究问题标签）——本批 4/4 开火都属于这类，"
      "形状尺判不了研究设计",
      _h109c_yin and "实验" in _h109c_yin[0] and "标签" in _h109c_yin[0], str(_h109c_yin)[:150])
check("v110 行为账 T88 在位（表注星号与「记作」这类合规写法被报了，AI 该怎么答）",
      "| T88 |" in tx("tests/behavior-self-test.md"), "T88 没登记")
