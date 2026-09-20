# -*- coding: utf-8 -*-
"""v1.56.2 本体口径硬化：人格与挫折协议一致 + 反攀比回归 + 规则单源 ----
full_e2e.py 顺序片段 6/14（原第 995–1121 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ---- v1.56.2 本体口径硬化：人格与挫折协议一致 + 反攀比回归 + 规则单源 ----
    check("v1562霸道总裁情绪口径", "会怼回去" not in cr and "正常化情绪" in cr and "我卡在哪" in cr)
    check("v1562反攀比无凭据比较", "大半同级学生" not in eg and "攀比式表达" in eg)
    check("v1562专业导师焦虑先接情绪", "先一句话正常化" in eg)
    check("v1562规则单源不重复", "第三节为唯一来源" in eg and "coach-rules.md` 第四节" in cp
          and "主动临时降一档把这一步讲透" not in cp)

    # ---- v1.56.4 规则接线：core规则真正接入10个workflow（统一指针，不复制正文）+ 鼓励理论规范出处 + 防假空白 ----
    wf_all = sorted(p for p in (ROOT / "workflows").glob("*.md"))
    check("v1564工作流十份", len(wf_all) == 10, "n=%d" % len(wf_all))
    check("v1564工作流全部接带教约定",
          all(all(s in p.read_text(encoding="utf-8") for s in
                  ("**带教约定**", "core/coaching-protocol.md", "core/encouragement-guide.md",
                   "反馈三段式", "P0/P1/P2", "core/coach-rules.md")) for p in wf_all))
    _conv = [[l for l in p.read_text(encoding="utf-8").splitlines() if "**带教约定**" in l]
             for p in wf_all]
    check("v1564带教约定指针逐字一致",
          all(len(x) == 1 for x in _conv) and len({x[0].strip() for x in _conv}) == 1)
    check("v1564鼓励理论规范出处", all(s in eg for s in (
        "10.1037/0033-2909.119.2.254", "10.1037/0022-3514.75.1.33",
        "Mueller, C. M., & Dweck, C. S. (1998)", "Kluger, A. N., & DeNisi, A. (1996)",
        "Ryan, R. M., & Deci, E. L. (2000)", "Skinner, B. F. (1953)")))
    check("v1564理论出处带核对日期", "核对" in eg and "勿与上面 Ryan & Deci (2000) 混写" in eg)
    check("v1564文献防假空白反查", all(s in tx("workflows/literature-auto-search.md")
                                  for s in ("假空白", "0 命中", "上位词")))

    # ---- v1.56.6 专业文档接线 + 行为自测补盲与可追溯走查 ----
    psy = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "psychology").glob("*.md")}
    check("v1566专业文档四份", set(psy) == {"ethics.md", "scale-library.md", "stats-guide.md", "missing-imputation-guide.md"}, str(set(psy)))
    check("v1566专业文档使用约定指针",
          all("**使用约定**" in t and "core/coaching-protocol.md" in t for t in psy.values()))
    check("v1566伦理危机口径", "12356" in psy["ethics.md"] and "不做临床诊断" in psy["ethics.md"])
    check("v1566统计数据真实性P0",
          "P0 红线" in psy["stats-guide.md"] and "不显著也是结果" in psy["stats-guide.md"])
    check("v1566量表库需核实", "需核实" in psy["scale-library.md"])
    check("v1566自测用例扩至38且连续", len(bt_nums) >= 38 and bt_nums[:38] == list(range(1, 39)),
          "n=%d" % len(bt_nums))
    check("v1566自测新增六场景", all(s in bt for s in ("T33", "T34", "T35", "T36", "T37", "T38")))
    check("v158自测用例扩至45且连续", len(bt_nums) >= 45 and bt_nums == list(range(1, len(bt_nums) + 1)),
          "n=%d" % len(bt_nums))
    check("v158自测新增七场景", all(("T%d" % i) in bt for i in range(39, 46)))
    check("v1566走查记录诚实标注",
          "桌面静态走查" in bt and "非真人" in bt and "最高优先级遗留" in bt)

    # ---- v1.2 手机独立版：能力边界三处一致 + 合并单文件可生成且自包含 ----
    mgp = ROOT / "doubao-skill" / "references" / "mobile-guide.md"
    check("v12手机说明文件", mgp.exists())
    mg = mgp.read_text(encoding="utf-8") if mgp.exists() else ""
    check("v12手机能力边界齐全", all(s in mg for s in ("手机上能完成", "手机上做不了", "必须回电脑", "手机装不了")))
    check("v12统计回电脑的理由", "JASP" in mg and "SPSS" in mg and "PROCESS" in mg and "电脑软件" in mg)
    check("v12只有手机时的出路", all(s in mg for s in ("必须找一台电脑", "带回手机", "跟导师说明")))
    check("v12安装方式含保底单文件", "合并单文件" in mg and "thesis-ai-coach-手机版.md" in mg)
    check("v12安装入口标注需核实", "[需核实]" in mg)
    check("v12三处边界一致",
          "手机可做一半" in skm and "必须回电脑" in skm
          and "本阶段需要电脑" in tx("doubao-skill/stages/stage-8-analysis.md")
          and "必须回电脑" in tx("doubao-skill/stages/stage-7-data.md")
          and "预处理" in tx("doubao-skill/stages/stage-7-data.md"))
    check("v12工具表含手机对照", "手机上能用什么" in tx("doubao-skill/references/tools.md"))
    check("v12学校示例不绑定某校", "九江" not in tx("doubao-skill/references/tools.md"))
    # 合并单文件：生成到临时目录（不依赖项目外的 _发布包/，保证干净副本也能跑）
    bsp = ROOT / "doubao-skill" / "build_mobile_single.py"
    check("v12合并单文件生成器存在", bsp.exists())
    if bsp.exists():
        md_dir = new_tmp("v12mobile")
        try:
            tg = md_dir / "single.md"
            rg = run(["doubao-skill/build_mobile_single.py", "--out", str(tg)], 120)
            check("v12合并单文件可生成", rg.returncode == 0 and tg.exists(), (rg.stderr or "")[-200:])
            stext = tg.read_text(encoding="utf-8") if tg.exists() else ""
            check("v12合并单文件自包含",
                  all(s in stext for s in ("手机上做不了", "引导循环", "阶段 11：答辩准备", "concise-direct", "规则优先级")),
                  "len=%d" % len(stext))
            check("v12合并单文件规模合理", len(stext) > 50000, "chars=%d" % len(stext))
            check("v12合并版排除维护者文件", "Skill 行为自测用例" not in stext)
            rc2 = run(["doubao-skill/build_mobile_single.py", "--check", "--out", str(tg)], 60)
            check("v12合并版同步校验通过", rc2.returncode == 0, (rc2.stdout or "")[-150:])
        finally:
            if not rmtree_retry(md_dir):
                print("WARN 手机版构建临时目录未能删除（请手动清理）：" + str(md_dir))

        # ---- v1.78 生成器默认输出路径必须就是 validate.py 检查的那一份 ----
        # 历史缺陷：默认路径按 CWD 解析，在仓库根跑就写到根目录，技能目录里那份永远过期，
        # 于是 validate 报"不同步"、旧语气名断言跟着红，两条报警都指不到真因。
        _art = SK / "thesis-ai-coach-手机版.md"
        _bak = _art.read_bytes() if _art.exists() else None
        _mtmp = new_tmp("v178mobile")
        try:
            rb = subprocess.run([sys.executable, str(bsp)], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=120, cwd=str(_mtmp))
            check("v178默认输出落技能目录而非当前目录",
                  rb.returncode == 0 and _art.exists() and not list(_mtmp.glob("*.md")),
                  (rb.stderr or rb.stdout or "")[-200:])
            rc3 = subprocess.run([sys.executable, str(bsp), "--check"], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=60,
                                 cwd=str(_mtmp))
            check("v178换目录跑--check仍判同步", rc3.returncode == 0, (rc3.stdout or "")[-160:])
        finally:
            if _bak is not None:
                _art.write_bytes(_bak)
            elif _art.exists():
                _art.unlink()

    # ---- v1.58 身份/稳定陪伴/鼓励自然化/多词检索/90篇候选池/重点卡片/手机原生适配 ----
    companionship = ROOT / "core" / "companionship.md"
    skill_comp = SK / "references" / "companionship.md"
    check("v158陪伴文件存在", companionship.exists() and skill_comp.exists())
    ct = companionship.read_text(encoding="utf-8") if companionship.exists() else ""
    check("v158陪伴身份与边界", all(s in ct for s in ("不是老师", "虚拟伴侣", "脚手架", "情感依赖", "12356")))
    sct = skill_comp.read_text(encoding="utf-8") if skill_comp.exists() else ""
    check("v158skill陪伴口径", all(s in sct for s in ("不是老师", "虚拟伴侣", "脚手架", "情感依赖")))
    check("v158陪伴登记入规则与入口",
          "core/companionship.md" in cr and "core/companionship.md" in st and "companionship.md" in skm)
    for _nm, _txt in (("coach-rules", cr), ("coaching-protocol", cp), ("START", st), ("SKILL", skm)):
        check("v158去旧人格:" + _nm, not any(x in _txt for x in ("霸道总裁", "知心姐姐", "小奶狗")))
    check("v158START不自称导师", "毕业论文AI导师" not in st and "毕业论文 AI 导师" not in st and "AI 助手" in st)
    check("v158鼓励原则化自然化", "密度自然" in eg and "每轮至多一次肯定" not in eg)
    # 多词检索 + ≥90 候选池（文档口径 + 脚本开关）
    check("v158工作流多词与90池",
          all(s in las for s in ("--queries", "--source all", "--min 90", "至少 3 组", "候选池")))
    check("v158量表多词检索纪律", "量表检索纪律" in sl and "同义词" in sl and "OR" in sl and "AND" in sl)
    check("v158检索脚本多词开关", all(x in psrc for x in ('--queries', '--source', '--min', 'action="append"')))
    check("v158卡片脚本与菜单项",
          (ROOT / "tools" / "literature_cards.py").exists() and "literature_cards.py" in menu and "【10/" in menu)
    check("v158卡片接入网页指南且不增类型", "literature_cards.py" in wg and "文献笔记网页" in wg)
    check("v158手机交接单与原生做法", all(s in mg for s in ("设备交接单", "全球学术快报", "literature_cards")))

