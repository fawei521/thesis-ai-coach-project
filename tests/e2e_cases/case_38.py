# -*- coding: utf-8 -*-
"""case_38 · 「零命中≠合格」得有物证：词表全绿的空洞稿 + 规范里的「词表外三问」双向钉住。

**这一片管五件事**：
  ① **物证在位且真的全绿**：`tests/test-data/全绿但空洞.md`（通篇没有一句只有做过研究才写得出的信息，
     数字与场景都是占位数）在现行表下**零缺项**——连 `--strict` 都放行。这条断言不许靠「改夹具让它绿」维持，
     它绿本身就是问题所在。
  ② **地基不偷工**：那份夹具的零缺项必须由**正文**撑住，不能靠说明页眉里的数字混过数字密度那条——
     所以这里剥掉引用块再跑一次，正文自己得够密度。
  ③ **三问在位，且写明不许靠加词条**：第三批补 12 个词之后 69 篇真语料零误报，
     但零误报不等于它读对了；词表只认列过的写法，换个方向（生理指标、眼动、田野、企业样本）照样「找不到」。
  ④ **三问是判断，不是第二张词表**：它们不许被搬进 §二 那张表当词条——表仍是唯一词表判据源，
     搬进去就等于把「要你想」偷偷换成「数你在不在」。
  ⑤ **反面也钉住**：三问要求指到具体位置（说不出位置＝没答），行为账 T87 管的是「报 0 条能不能交」那一格。

变量前缀 _h109b*：与 case_37 同一版，前缀撞开会静默互相覆盖（见 case_20 的教训）。
"""
_h109b_mod = {"__name__": "style_check_109b", "__file__": str(ROOT / "tools" / "style_check.py")}
exec(compile(tx("tools/style_check.py"), "tools/style_check.py", "exec"), _h109b_mod)
_h109b_rows, _h109b_err = _h109b_mod["load_bans"]()
check("v109 判据表解析成功（空洞夹具全绿这件事若在半套判据上成立就没意义）",
      _h109b_rows is not None and not _h109b_err, str(_h109b_err)[:200])
_h109b_rows = _h109b_rows or []
_h109b_spec = tx("core/academic-style.md")

# ---- ① 物证：通篇空洞却零缺项 ----
_h109b_fix = tx("tests/test-data/全绿但空洞.md")
_h109b_n = len(re.findall(r"[一-鿿]", _h109b_fix))
check("v109 空洞夹具在位且有 800 汉字以上（短了撞不到结构统计，全绿就成了假的）",
      _h109b_n >= 800, "%d 字" % _h109b_n)
_h109b_miss = [m for k, m in _h109b_mod["ban_hits"](_h109b_rows, _h109b_fix) if k == "缺项"]
_h109b_p = new_tmp("v109b") / "空洞.md"
_h109b_p.write_text(_h109b_fix, encoding="utf-8")
_h109b_r = run(["tools/style_check.py", str(_h109b_p), "--strict"])
check("v109 通篇没有一句只有作者写得出的信息的稿子在现行表下零缺项且 --strict 放行"
      "（这条不是夸尺子，是钉住词表看不见这类毛病——判断那一侧不许省）",
      not _h109b_miss and _h109b_r.returncode == 0 and "【缺项】" not in _h109b_r.stdout,
      "缺项：%s；rc=%d" % (str(_h109b_miss)[:120], _h109b_r.returncode))

# ---- ② 全绿得由正文自己撑住，不是页眉里的数字 ----
_h109b_body = "\n".join(l for l in _h109b_fix.splitlines() if not l.strip().startswith(">"))
_h109b_bn = len(re.findall(r"[一-鿿]", _h109b_body))
_h109b_bd = len(re.findall(r"\d+(?:\.\d+)?", _h109b_body))
check("v109 剥掉说明块后夹具正文自己的数字密度仍达标（不达标就是拿页眉混过那条结构判据）",
      _h109b_bn >= 600 and 1000.0 * _h109b_bd / max(_h109b_bn, 1) >= 1.0,
      "正文 %d 字 %d 个数字" % (_h109b_bn, _h109b_bd))

# ---- ③ 三问在位，且写明不许靠加词条 ----
_h109b_三问 = ["对象与工具说清了没有", "这个因果是谁说的", "这一段换到任何一篇论文里还成立吗"]
_h109b_缺 = [q for q in _h109b_三问 if q not in _h109b_spec]
check("v109 规范第二节末尾有那三问（词表咬不到的地方由落笔者逐段判断，一条都不许少）",
      not _h109b_缺, "缺：" + "、".join(_h109b_缺))
check("v109 三问写明了不许靠加词条解决，并给出理由（补完 12 个词后 69 篇零误报，但零误报不等于读对了）",
      "不许靠加词条解决" in _h109b_spec and "零误报不等于它读对了" in _h109b_spec)
check("v109 第四节第 4 步把「报 0 条也要答三问」接进了交付工序，并点到这份夹具"
      "（否则下个会话会把它当成可删的样例）",
      "报 0 条也要把第二节那三问答完" in _h109b_spec and "全绿但空洞" in _h109b_spec)

# ---- ④ 三问不许被搬进表当词条 ----
_h109b_moved = [r["cat"] for r in _h109b_rows
                if "三问" in r["cat"] or "换到任何一篇" in r["cat"] or "对象与工具说清" in r["cat"]]
check("v109 那三问没有变成表里的词条（表仍是唯一词表判据源；把「要你想」换成「数你在不在」就是自欺）",
      not _h109b_moved, "被搬进表的：" + "、".join(_h109b_moved))

# ---- ⑤ 反面：判断也得可核对 ----
check("v109 三问要求指到具体位置（说不出位置＝没答），防的是「我认真看过了」这种自由发挥混过关",
      "说不出位置就等于没答" in _h109b_spec)
_h109b_t = [l for l in tx("tests/behavior-self-test.md").splitlines() if l.startswith("| T87 |")]
check("v109 行为用例 T87 在位（「第 24 项报了 0 条是不是就能交」这一格得有行为账，不是只改了文档）",
      len(_h109b_t) == 1 and "三问" in _h109b_t[0], "%d 行" % len(_h109b_t))
