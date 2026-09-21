# -*- coding: utf-8 -*-
"""v1.98 的机检：原文可得性探测、题录双源核验，以及"占位/标注分开数"。
full_e2e.py 顺序片段 24/24（由壳按序 exec，不单独运行）。
临时命名空间一律用 _h198* 前缀：片段与壳共用 globals，撞名会静默改掉后续片段的运行环境（见 case_20 的教训）。
本片段全程**不联网**：两把尺的判定逻辑靠替换模块内的取数函数来验，
  真实网络只在学生机器上跑一次就留台账——回归测试压在离线才是可复现的。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:
    import importlib.util as _il198

    def _load198(rel):
        spec = _il198.spec_from_file_location(rel.replace("/", "_")[:-3], ROOT / rel)
        mod = _il198.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    _d198 = new_tmp("v198")      # 别往 tests/test-data 里落夹具残渣：那是常驻目录，new_tmp 的会随收尾清掉
    _lf198 = _load198("tools/lit_fetch.py")
    _lv198 = _load198("tools/lit_verify.py")

    # ---------- 一、两个工具都是纯标准库 + 编码守卫形状 ----------
    _s198 = "\n".join(tx("tools/" + n) for n in ("lit_fetch.py", "lit_verify.py", "menu_ref.py"))
    check("v198 原文与题录工具纯标准库",
          all(k not in _s198 for k in ("import requests", "import pandas", "import numpy",
                                       "subprocess"))
          and "urllib.request" in _s198, "引入了第三方库或 subprocess")
    check("v198 编码守卫无条件生效",
          'if hasattr(sys.stdout, "reconfigure"):' in tx("tools/lit_fetch.py")
          and "and not sys.stdout.isatty()" not in _s198)
    check("v198 不绕付费墙：只登记需数据库，不含任何登录/凭据处理",
          all(k in tx("tools/lit_fetch.py") for k in ("需数据库", "不绕付费墙"))
          and all(k not in _s198.lower() for k in ("password", "token", "cookie", "login")))

    # ---------- 二、菜单接线与分册 ----------
    _menu198 = "\n".join(tx("tools/" + p.name)
                         for p in sorted((ROOT / "tools").glob("menu*.py")))
    check("v198 菜单第26/27项已接线",
          "【26/27】" in _menu198 and "【27/27】" in _menu198
          and "lit_fetch.py" in _menu198 and "lit_verify.py" in _menu198)
    check("v198 新处理器落在独立分册且被 menu.py 点名",
          "menu_ref.py" in tx("tools/menu.py") and (ROOT / "tools" / "menu_ref.py").is_file(),
          "menu_lit.py 顶在尺寸闸门上，另起一册是硬约束")
    # 注意：不能用壳里的 st —— case_18 第 70 行把 st 顶成了轻量版 self-test，
    # 这正是片段头警告的"撞名静默改掉后续片段环境"，只不过这次的受害者是别人的变量。
    _start198 = tx("START.md")
    check("v198 START登记两个新工具",
          "lit_fetch.py" in _start198 and "lit_verify.py" in _start198,
          "新工具没进学生可见的工具清单")
    check("v198 模板带列头且自带阴性样本",
          all(k in tx("templates/文献原文清单模板.csv")
              for k in ("id", "doi", "pmcid", "arxiv", "expect_title"))
          and "06.023" in tx("templates/文献原文清单模板.csv")
          and "ULS-6" in tx("templates/题录核验模板.csv"),
          "模板少了阴性样本＝这两把尺可能空转")

    # ---------- 三、lit_fetch：六态判定（把 fetch 换成假响应） ----------
    _PDF, _XML, _HTML = b"%PDF-1.7\n..."[:64] * 600, b'<?xml version="1.0"?><article xmlns=x><body>hi', b"<html>" * 9000

    def _fake198(table):
        def f(url, timeout=60, tries=3):
            for key, val in table.items():
                if key in url:
                    if isinstance(val, Exception):
                        raise val
                    return 200, val[1], val[0]
            raise AssertionError("清单没覆盖的 URL：" + url[:70])
        return f

    _真标题198 = "The Interaction of Person-Affect-Cognition-Execution (I-PACE) model for addictive behaviors"
    _old_fetch, _old_cr = _lf198.fetch, _lf198.crossref_title
    try:
        _lf198.crossref_title = lambda doi: _真标题198        # 登记处说 DOI 指向 I-PACE
        _lf198.fetch = _fake198({"arxiv.org": (_PDF, "application/pdf"),
                                 "ebi.ac.uk": (_XML, "application/xml"),
                                 "tandfonline.com": (_HTML, "text/html")})
        _r_ok = _lf198.probe(dict(id="A", doi="10.1016/j.neubiorev.2019.06.032",
                                  expect_title=_真标题198, arxiv="2506.12605v1"),
                             False, _d198)
        check("v198 探测：公开 PDF 判可获取", _r_ok["status"] == "可获取", str(_r_ok)[:130])
        _r_xml = _lf198.probe(dict(id="B", pmcid="PMC11987286", expect_title="两波纵向研究"),
                              False, _d198)
        check("v198 探测：开放全文 XML 也算可获取（能逐字引就不止是摘要）",
              _r_xml["status"] == "可获取(全文XML)" and _r_xml["path"] == "", str(_r_xml)[:130])
        _r_need = _lf198.probe(dict(id="C", doi="10.64628/ab.x", expect_title="随便"),
                                False, _d198)
        check("v198 探测：只有题录没公开入口判需数据库",
              _r_need["status"] == "需数据库", str(_r_need)[:130])
        # 阴性①：DOI 猜错一位，登记处返回的是另一篇 → 必须拦住，不许下载
        _r_wrong = _lf198.probe(dict(id="D", doi="10.1016/j.neubiorev.2019.06.023",
                                     expect_title="A Short Scale for Measuring Loneliness",
                                     url="https://arxiv.org/pdf/1234"),
                                False, _d198)
        check("v198 探测：DOI 指向别的文章时报标题对不上且不去下载",
              _r_wrong["status"] == "标题对不上", str(_r_wrong)[:150])
        _lf198.fetch = _fake198({})
        _r_err = _lf198.probe(dict(id="E", expect_title="某篇",
                                    url="https://arxiv.org/pdf/9999.9999"), False, _d198)
        _lf198.fetch = _fake198({"9999.9999": (_HTML, "text/html")})
        _r_html = _lf198.probe(dict(id="F", expect_title="某篇",
                                     url="https://arxiv.org/pdf/9999.9999"), False, _d198)
        check("v198 探测：网络异常判失败不误报已获取", _r_err["status"] == "失败", str(_r_err)[:120])
        check("v198 探测：返回 HTML 壳判非PDF（页面能看≠原文到手）",
              _r_html["status"] == "非PDF", str(_r_html)[:120])
    finally:
        _lf198.fetch, _lf198.crossref_title = _old_fetch, _old_cr

    _c198 = _lf198.candidates(dict(doi="10.3389/fpsyg.2025.1621540", pmcid="PMC12350385",
                                   arxiv="2506.12605v1"))
    check("v198 候选地址按来源类型生成且不猜付费墙",
          len(_c198) >= 4 and all(u.startswith("https://") for _, u in _c198)
          and not any("sci-hub" in u.lower() or "download=1" in u for _, u in _c198), str(_c198)[:150])
    check("v198 标题回核认得大小写与标点差异",
          _lf198.same_title("I-PACE Model for Addictive Behaviors:",
                            "the i-pace model for addictive behaviors")
          and not _lf198.same_title("Emotional Cascade Model", "Understanding emotional dysregulation"))

    # ---------- 四、lit_verify：五态判定（把两个登记处换成假返回值） ----------
    _好 = dict(title="Relationship formation on the Internet: What's the big attraction?",
               journal="Journal of Social Issues", volume="58", issue="1", pages="9-31",
               year="2002", doi="10.1111/1540-4560.00246", authors="McKenna K; Green A")
    _真 = dict(_好, title="Understanding the relationship between emotional and behavioral dysregulation")

    def _stub198(a, b):
        _oc, _oa = _lv198.from_crossref, _lv198.from_openalex
        _lv198.from_crossref, _lv198.from_openalex = (lambda **k: dict(a)), (lambda **k: dict(b))
        return _oc, _oa

    _旧c, _旧o = _stub198(_好, _好)
    try:
        _v198 = _lv198.verdict({"title": "Relationship formation on the Internet: What's the big attraction?",
                                "journal": "Journal of Social Issues", "year": "2002",
                                "volume": "58", "pages": "9-31", "doi": "10.1111/1540-4560.00246"})
        check("v198 核验：两源一致且与条目相符判双源一致",
              _v198["状态"] == "双源一致", str(_v198)[:130])
        # 阴性②：笔记里那种"编出来的标题"——两源一致但和你的条目不同，必须报有出入
        _v198b = _lv198.verdict({"title": "The Emotional Cascade Model and Self-Injury",
                                 "journal": "Behaviour Research and Therapy", "year": "2008",
                                 "volume": "46", "pages": "593-611", "doi": "10.1016/j.brat.2008.02.002"})
        check("v198 核验：编造的标题判有出入并点名标题对不上",
              _v198b["状态"] == "有出入" and "标题对不上" in _v198b["差异"], str(_v198b)[:160])
        _v198c = _lv198.verdict({"title": _好["title"], "journal": "Journal of Family Psychology",
                                 "year": "2002", "volume": "58", "pages": "9-31",
                                 "doi": "10.1111/1540-4560.00246"})
        check("v198 核验：刊名记错（把 A 刊写成 B 刊）也报有出入",
              _v198c["状态"] == "有出入" and "刊名对不上" in _v198c["差异"], str(_v198c)[:160])
    finally:
        _lv198.from_crossref, _lv198.from_openalex = _旧c, _旧o
    _旧c, _旧o = _stub198(_好, _真)
    try:
        check("v198 核验：两源互相矛盾判双源互斥（不给你挑一个顺眼的）",
              _lv198.verdict({"title": _好["title"], "doi": _好["doi"]})["状态"] == "双源互斥")
        _lv198.from_openalex = lambda **k: (_ for _ in ()).throw(RuntimeError("no record"))
        check("v198 核验：只有一家有记录判单源，不升级为已核实",
              _lv198.verdict({"title": _好["title"], "doi": _好["doi"]})["状态"] == "单源")
    finally:
        _lv198.from_crossref, _lv198.from_openalex = _旧c, _旧o
    _旧c, _旧o = _lv198.from_crossref, _lv198.from_openalex
    try:
        _lv198.from_crossref = _lv198.from_openalex = \
            lambda **k: (_ for _ in ()).throw(RuntimeError("登记处查无"))
        check("v198 核验：两家都查无判登记处查无（不等于“这条不存在”，更不是“写个差不多的”）",
              _lv198.verdict({"title": "某篇谁也没见过的文章"})["状态"] == "登记处查无")
    finally:
        _lv198.from_crossref, _lv198.from_openalex = _旧c, _旧o
    check("v198 缺字段只留空位不猜值",
          "104: 1-10" not in _lv198.gbt(dict(_好, volume="", pages=""))
          and "9-31" in _lv198.gbt(_好))
    _行198 = _d198 / "题录小.csv"
    _行198.write_text("题名,作者,年份,期刊,卷,期,页,DOI\r\n"
                      "# 这是说明行不该被当数据\r\n"
                      "真实标题,McKenna K,2002,Journal of Social Issues,58,1,9-31,10.1111/1540-4560.00246\r\n",
                      encoding="utf-8")
    check("v198 题录表：# 说明行不算数据、GBK/UTF-8 都读得进",
          len(_lv198.read_rows(str(_行198))) == 1)

    # ---------- 五、第 23 项：占位与核验标注分开数 ----------
    _混198 = _d198 / "占位混标注.md"
    _混198.write_text(
        "# 一、选题背景\n【你来写：4 段】\n【你填】\n"
        "## 八、参考文献\n1. 某作者. 某题[J]. 某刊, 2024(11). （**待补**：卷号、页码）\n"
        "【缺：卷号】\n2. 另一作者《另一题》[EB/OL]【预印本未经同行评审】\n"
        "3. 第三作者. 第三题[J]. 第三刊. [未查到] 原文是否设反向计分题\n", encoding="utf-8")
    _r198 = run(["tools/proposal_readiness.py", str(_混198), "--no-progress"])
    _o198 = _r198.stdout
    check("v198 自检把模板占位与核验标注分开数",
          "还有 2 处【】没换成你自己的内容" in _o198 and "核验类标注" in _o198, _o198[:260])
    check("v198 自检对三态标记给提示不判缺项（空着是事实，填上才是编）",
          "三态标记" in _o198 and "[提示]" in _o198, _o198[-260:])
