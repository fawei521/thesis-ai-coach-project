# -*- coding: utf-8 -*-
"""case_33 · 交付后"换上下文复审"这条提醒：规则在位、要素分得开、且没把立场改成检测对抗。

这一片回答四件事：
  ① **规则真的落地了**：五条要素能在 `core/outcome-delivery.md` 第七节逐条数出来，
     语境口径与换上下文的指针能在 `core/academic-style.md` 找到。
  ② **可复跑的对照**：`tests/cross_review_experiment.py` 八个臂各判五条，判定必须与夹具声明逐条一致；
     尺子自己还要过一遍植入式阴性（删一块交代要少一条、翻一句否定要翻一次判定）。
  ③ **不给预设模板**这条不能只写在纸上：包里不许藏一份成品提示词供抄——templates/ 下有这类文件就判红。
  ④ **立场一格没动**：新增的复审只看表达，文档里不许出现承诺降率、过检测的措辞。

变量前缀 _h106*：片段与壳共用 globals，撞名会静默改掉后面片段的运行环境（case_20 的教训）。
"""
_h106_od = tx("core/outcome-delivery.md")
_h106_as = tx("core/academic-style.md")
_h106_bt = tx("tests/behavior-self-test.md")

# ---- ① 五条要素逐条数得出 ----
_h106_sec = _h106_od.split("## 七、")[1].split("## 八、")[0] if "## 七、" in _h106_od else ""
_h106_items = [l for l in _h106_sec.splitlines() if l[:3] in ("1. ", "2. ", "3. ", "4. ", "5. ")]
check("v106 交付后提醒那段确实列了五条要素（少于五条就是有一条没落地）",
      len(_h106_items) == 5, "%d 条" % len(_h106_items))
_h106_keys = ["新会话或另一个 AI", "只读不改", "本包不给固定模板", "不测 AIGC 率",
              "只有做过这个研究的人才写得得出", "第 24 项"]
check("v106 六处关键交代都在位（对象、只读、不给模板、要的读数、边界、上一轮读数）",
      all(k in _h106_sec for k in _h106_keys),
      "缺：" + "、".join(k for k in _h106_keys if k not in _h106_sec))
check("v106 自检清单加了这一格（学生看得到它属于交付的一步）",
      "复审表达度" in _h106_od and "当场写出那段话" in _h106_od)

# ---- ② 语体规范两侧都接上了 ----
check("v106 语体规范末尾指向换上下文复审，并写明理由是你读不出自己的套话",
      "换上下文再读一遍" in _h106_as and "读不出自己的套话" in _h106_as)
check("v106 误伤那条补了语境口径：先判语境、否定句与定义句两种豁免、不许为清零改词",
      all(k in _h106_as for k in ("先判语境", "否定句", "定义句", "不许为了让条数清零")))

# ---- ③ 用例账：T77–T79 在位且各自指到落地的文件 ----
_h106_t = [l for l in _h106_bt.splitlines() if l.startswith(("| T77 |", "| T78 |", "| T79 |"))]
check("v106 行为用例 T77–T79 三条齐（要求 AI 怎么想的规矩，得有行为账）",
      len(_h106_t) == 3, "%d 行" % len(_h106_t))
check("v106 T77 指到交付纪律、T78 指到 AI 素养第八节、T79 指到语体规范第五节",
      len(_h106_t) == 3 and "outcome-delivery.md" in _h106_t[0]
      and "ai-literacy.md" in _h106_t[1] and "academic-style.md" in _h106_t[2], "逐条看引用")
check("v106 自检项点名了可复跑实验，且写明条数由脚本自己数",
      "cross_review_experiment.py" in _h106_bt and "自己数" in _h106_bt)

# ---- ④ 实验真能跑，八臂分得开，尺子不空转 ----
_h106_demo = run(["tests/cross_review_experiment.py", "--demo"])
_h106_dlines = _h106_demo.stdout.splitlines() or [""]
check("v106 八个臂的判定与夹具声明逐条一致（分得开，条数由脚本现数）",
      _h106_demo.returncode == 0 and "分得开" in _h106_demo.stdout,
      (_h106_demo.stdout or _h106_demo.stderr)[-300:])
check("v106 合格臂必须五要素全真（合格夹具自己过不了，后面全不用看）",
      _h106_dlines[0].startswith("合格臂") and "要素 5/5" in _h106_dlines[0], _h106_dlines[0])
_h106_self = run(["tests/cross_review_experiment.py", "--selftest"])
check("v106 植入式阴性通过：删一块交代少一条，翻一句否定翻一次判定",
      _h106_self.returncode == 0 and "植入式阴性通过" in _h106_self.stdout,
      (_h106_self.stdout or _h106_self.stderr)[-260:])

# ---- ⑤ 不给模板要落成形状：包里不许藏一份成品提示词 ----
_h106_tpl = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "templates").rglob("*")
                   if p.is_file() and re.search(r"提示词|prompt", p.name, re.I))
check("v106 templates/ 下没有成品提示词文件（“包里不留模板”不许只是句好话）",
      not _h106_tpl, "查到：" + "、".join(_h106_tpl))

# ---- ⑥ 立场没动：这条提醒不是检测对抗的入口 ----
# 判否定只看**匹配词前面那一小段**，不能整句里有个"不"就免检——
# 第一版按整句豁免，被"能把 AIGC 率降到 20%，让检测查不出来"这种句子钻了口子（一个"不"字救全句）。
# 立场话（"不测 AIGC 率""不承诺任何检测结果"）照放行；承诺话必须咬住。两条都由这同一个函数判。
_h106_promise = re.compile(r"降\s*AIGC|降低\s*AIGC|AIGC\s*[率比]|把\s*AIGC|骗过检测|绕过检测|通过检测|避开检测")
_h106_neg = re.compile(r"[不别]|拒|禁止|无需|未|没有|而非")


def _h106_promised(text):
    """返回"在承诺降率/过检测"的分句；否定紧邻在匹配词之前的不算。"""
    out = []
    for clause in re.split(r"[，、；：。！\n]", text):
        for m in _h106_promise.finditer(clause):
            if not _h106_neg.search(clause[max(0, m.start() - 12):m.start()]):
                out.append(clause.strip()[:36])
                break
    return out


check("v106 交付纪律里没有承诺降率或过检测的措辞（立场话照放行）",
      not _h106_promised(_h106_od), "、".join(sorted(set(_h106_promised(_h106_od)))))
check("v106 阳性探针：写“能把 AIGC 率降到 20%”必须被判红（不是恒绿，也不是整句豁免）",
      bool(_h106_promised("这个工具能把 AIGC 率降到 20%，让检测查不出来。")))
check("v106 立场句反例：“不测 AIGC 率、不承诺任何检测结果”不得被判红",
      not _h106_promised("本包不测 AIGC 率、不做降率、不承诺任何检测结果。"))
check("v106 语体规范里“不做降率”与“改字这个动作在学生身上”两句原样还在",
      "不做降率" in _h106_as and "改字这个动作在学生身上" in _h106_as)

# ---- 阴性：同一批判据打在无关文件上必须全不成立（不是写死的真）----
_h106_ctl = tx("workflows/literature-auto-search.md")
check("v106 上述文档判据在无关文件上全不成立（阴性）",
      not any(k in _h106_ctl for k in ("换上下文", "先判语境", "本包不给固定模板", "复审表达度")))
