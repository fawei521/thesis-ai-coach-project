# -*- coding: utf-8 -*-
"""v1.96 的机检：AI 腔体检、写作留痕，以及"不做降率"这条红线的形制。
full_e2e.py 顺序片段 23/23（由壳按序 exec，不单独运行）。
临时命名空间一律用 _h196* 前缀：片段与壳共用 globals，撞名会静默改掉后续片段的运行环境（见 case_20 的教训）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:
    _d196 = new_tmp("v196")
    _para = ("综上所述，这一领域的研究具有重要意义。首先，它体现了理论层面的深度融合；其次，它展现了实践层面的多维视角；"
             "再次，它为后续工作提供了闭环式的支撑；最后，其影响将是深远的、系统的、全方位的。")
    _ai196 = _d196 / "AI味稿.md"
    _ai196.write_text("\n\n".join([_para] * 4), encoding="utf-8")
    _hu196 = _d196 / "真人稿.md"
    # 夹具用**不指名的量表**配假 α：真量表名＋假数字放一起，就是 v1.93 那次被自家闸判红的那类东西
    _hu196.write_text("我在城区一所初中发了 240 份问卷，回来 227 份，19 份因为作答不到 90 秒被剔掉，最后用 208 份。\n\n"
                      "孤独感量表长版 20 题学生嫌长，删到 8 题后 α 从 .89 掉到 .76，我在讨论里就不敢说满。"
                      "预测试有 3 个人在自伤那题空白，还有一个下课后找班主任哭了，所以正式施测把这部分挪到最后，"
                      "前面加了一页求助信息。\n\n"
                      "中介效应是 .07 到 .19，Bootstrap 5000 次，区间不含 0。就这么点。"
                      "导师原话是「别写成决定性因素」，我抄在草稿边上。\n\n"
                      "反刍那部分我原本想用 Nolen-Hoeksema 的 22 题全版，预测试做完发现学生在\"想事情太多\""
                      "这一类题上重复作答，最后只留了 12 题，计分按维度均分，缺失的那两题我在附录里写了处理"
                      "办法。2024 年 11 月在两所学校各施测一次，一节 45 分钟做不完，后来压缩到 32 分钟。",
                      encoding="utf-8")
    _r_ai = run(["tools/style_check.py", str(_ai196), "--strict"])
    _r_hu = run(["tools/style_check.py", str(_hu196)])
    check("v196 体检：AI 味稿报缺项且 --strict 退出码 1",
          "【缺项】" in _r_ai.stdout and _r_ai.returncode == 1, _r_ai.stdout[:140])
    check("v196 体检：含具体信息的真人稿不报缺项（不误伤）",
          "【缺项】" not in _r_hu.stdout and _r_hu.returncode == 0, _r_hu.stdout[:200])
    check("v196 体检输出自带「不测 AIGC 率」与「不替你改」两句",
          "不测 AIGC 率" in _r_ai.stdout and "不替你改" in _r_ai.stdout)
    _hu196.write_text(_hu196.read_text(encoding="utf-8") + "\n\n" + _para, encoding="utf-8")
    _r_in = run(["tools/style_check.py", str(_hu196), "--strict"])
    check("v196 植入一段套话必须让它报缺项（阴性：尺子不空转）",
          "【缺项】" in _r_in.stdout and _r_in.returncode == 1, _r_in.stdout[:200])
    _short196 = _d196 / "短稿.md"
    _short196.write_text("只有这么几个字，统计判据不该装懂。", encoding="utf-8")
    _r_s = run(["tools/style_check.py", str(_short196)])
    check("v196 稿子太短就直说不成立，不硬给结论", _r_s.returncode == 2 and "太短" in _r_s.stdout, _r_s.stdout[:120])

    _log196 = _d196 / "留痕.md"
    _draft = _d196 / "讨论_第一版.md"
    _draft.write_text("第一段内容，约二十来个字，用于留痕测试。\n", encoding="utf-8")
    _c1 = run(["tools/authorship_log.py", str(_draft), "--log", str(_log196), "--note", "初稿"])
    _snap196 = _draft.read_bytes()
    _draft.write_text("第一段内容，约二十来个字，用于留痕测试。\n第二段补了样本量 208 与 α=.76。\n", encoding="utf-8")
    _fp196 = _draft.read_bytes()
    _c2 = run(["tools/authorship_log.py", str(_draft), "--log", str(_log196), "--note", "补数据"])
    _lt = _log196.read_text(encoding="utf-8")
    check("v196 留痕跑两次各记一行、备注落表",
          _c1.returncode == 0 and _lt.count("\n| 20") == 2 and "初稿" in _lt and "补数据" in _lt, _lt[:220])
    check("v196 写留痕不改草稿一个字节（真不变量）", _draft.read_bytes() == _fp196)
    check("v196 第一次记「首次」、第二次算出与上次的字数差",
          "首次" in _lt and re.search(r"\|\s*[+-]\d+\s*\|", _lt) is not None, _lt[-260:])
    check("v196 留痕表头与模板逐字相同（两处写法同源）",
          _lt.split("| 时间")[0].strip() == tx("templates/写作留痕模板.md").split("| 时间")[0].strip())
    _v0 = _d196 / "上一版.md"
    _v0.write_text("旧内容一行。\n另一行旧内容。\n", encoding="utf-8")
    _c3 = run(["tools/authorship_log.py", str(_draft), "--log", str(_log196), "--compare", str(_v0)])
    check("v196 --compare 报出两份稿子之间的真实改动行数",
          "改动" in _c3.stdout and "行（" in _c3.stdout, _c3.stdout[-200:])

    _menu196 = "\n".join(tx("tools/" + p.name) for p in sorted((ROOT / "tools").glob("menu*.py")))
    check("v196 菜单第24/25项已接线",
          "【24/25】" in _menu196 and "【25/25】" in _menu196
          and "style_check.py" in _menu196 and "authorship_log.py" in _menu196)
    _gen196 = re.findall(r'^\s+\("([^"]+)",\s*"templates/', tx("tools/setup_workspace.py"), re.M)
    check("v196 生成件四份且先读我逐份点名",
          len(_gen196) == 4 and "06-论文正文/我的写作留痕.md" in _gen196
          and all(k in tx("我的工作区/先读我.md") for k in ("我的论文进度.md", "检索记录.md",
                                                           "我的毕业材料清单.md", "我的写作留痕.md")))
    _red196 = tdoc("core/ai-literacy.md") + tx("workflows/writing-guide.md") + tx("core/skill-sourcing.md")
    check("v196 红线口径写实在三处（不做降率一节＋四步工序＋不装自称能过检测的技能）",
          "## 八、学生要" in _red196 and "把文字改回你自己的口吻（四步，重要）" in _red196
          and "直接不装" in _red196)
    _lite196 = tx("doubao-skill/references/academic-norms.md") + tx("doubao-skill/stages/stage-9-writing.md")
    check("v196 轻量版两侧同改（不做降率这句话镜像位也在）",
          "降 AI 率" in _lite196 and "骗过检测" in _lite196 and "四步" in _lite196)
    _hp196 = {}
    exec(compile(tx("tests/humanize_pressure.py"), "tests/humanize_pressure.py", "exec"), _hp196)
    _promised = _hp196["promised"]
    _bad196 = []
    for _p196 in sorted(ROOT.rglob("*.md")):
        # 只扫**学生侧指引**：CHANGELOG 是账本，必须原样记"用户要过什么、我们拒了什么"，
        # 把它扫进来只会逼人改写史实；tests/ 与档案、构建产物同理不扫。
        if _p196.relative_to(ROOT).parts[0] in ("tests", "维护档案") or _p196.name in (
                "手机版", "CHANGELOG.md") or "手机版" in _p196.name:
            continue
        _txt196 = _p196.read_text(encoding="utf-8", errors="replace")
        if any(_promised(_txt196, _pat) for _pat in _hp196["PROMISE"]):
            _bad196.append(str(_p196.relative_to(ROOT)))
    check("v196 学生侧指引里没有肯定式的降率/过检测承诺（尺子反扫）",
          not _bad196, str(_bad196)[:240])
    check("v196 行为用例 T57-T60 在位且点名可机判的尺",
          all(("| T%d |" % _n) in tx("tests/behavior-self-test.md") for _n in (57, 58, 59, 60))
          and "humanize_pressure.py" in tx("tests/behavior-self-test.md"))
    _rep196 = ROOT.parent / "_归档" / "审查报告" / "2026-09-21 去AI味与降率请求的A-B实验.md"
    if (ROOT / ".git").exists():      # 仓库外的档案：只有开发树查得到，发布包干净副本自然跳过
        _rt196 = _rep196.read_text(encoding="utf-8") if _rep196.is_file() else ""
        check("v196 A-B 实验报告已落盘并写了尺子的同义词假阴性",
              "四件必备" in _rt196 and "同义词假阴性" in _rt196 and "n=1" in _rt196,
              _rep196.name)
    _rp196 = run(["tests/humanize_pressure.py"])
    check("v196 压力尺自测通过（植入判红、合格放过）",
          _rp196.returncode == 0 and "抓得住坏回答" in _rp196.stdout, _rp196.stdout[-180:])
