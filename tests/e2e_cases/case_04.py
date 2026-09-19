# -*- coding: utf-8 -*-
"""v1.63 量表库三扩：10 个高频量表(29→39组、10→11大类)，硬事实逐条锁定（均经联网核查）----
full_e2e.py 顺序片段 4/14（原第 616–797 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ---- v1.63 量表库三扩：10 个高频量表(29→39组、10→11大类)，硬事实逐条锁定（均经联网核查）----
    check("GritS事实", all(s in sl for s in [
        "Grit-S", "Duckworth & Quinn, 2009", "兴趣一致性(4)＋坚持努力(4)",
        "总分（8-40）", "Li 等, 2018"]))
    check("IAS事实", all(s in sl for s in [
        "IAS", "Leary, 1983", "彭纯子等, 2004",
        "第 3、6、10、15 题为反向计分", "总分 15-75"]))
    check("ITS事实", all(s in sl for s in [
        "ITS", "Rotter, 1967", "总分 25-125、中值 75",
        "约半数题项为反向计分", "特殊信任（对身边人）＋普遍信任"]))
    check("INCOM事实", all(s in sl for s in [
        "INCOM", "Gibbons & Buunk, 1999", "王明姬、王垒、施俊琦, 2006",
        "白学军等, 2013", "6题上行版无反向题", "中文版α约.88、四周重测约.89"]))
    check("FoMO事实", all(s in sl for s in [
        "FoMOs", "Przybylski, Murayama, DeHaan & Gladwell, 2013",
        "李琦、王佳宁、赵思琦、贾彦茹, 2019", "10题求和（10-50）", "8 题二维修订版"]))
    check("SCSSF事实", all(s in sl for s in [
        "SCS-SF", "Neff, 2003", "Raes, Pommier, Neff & Van Gucht, 2011",
        "只用总分、不报告各成分分", "三个负性子量表的题项**反向计分**"]))
    check("PPQ事实", all(s in sl for s in [
        "PPQ", "张阔、张赛、董颖红, 2010",
        "自我效能(7)＋韧性(7)＋希望(6)＋乐观(6)", "总分 26-182", "第 8,10,12,14,25 题"]))
    check("AAQ2事实", all(s in sl for s in [
        "AAQ-II", "Bond 等, 2011", "曹静、吉阳、黄峥, 2013",
        "总分 7-49", "全部同向、无反向题"]))
    check("UWESS事实", all(s in sl for s in [
        "UWES-S", "Schaufeli, Martínez, Pinto, Salanova & Bakker, 2002",
        "方来坛、时勘、张风华, 2008", "李西营、黄荣怀, 2010",
        "活力(6)＋奉献(5)＋专注(6)"]))
    check("学业倦怠事实", all(s in sl for s in [
        "连榕、杨丽娴, 2005", "情绪低落(8)＋行为不当(6)＋成就感低(6)",
        "总α约.86", "MBI-SS", "不可混用条目或互相替代引用"]))
    po0 = tx("templates/paper-outline.md")
    check("大纲伦理埋点", "监护人书面知情同意" in po0 and "注意力检查题" in po0 and "Bootstrap 5000" in po0)
    check("大纲结果章完整", all(s in po0 for s in ["平行分析", "Games-Howell", "卡方", "简单斜率", "偏态"]))
    sg = tx("psychology/stats-guide.md")
    # v1.53.1：auto_stats 已拆为 tools/stats/ 包，实现函数按所属模块核对（不再只看 CLI 入口）
    acmp = tx("tools/stats/compare.py"); areg = tx("tools/stats/regression.py")
    check("stats能力真实", "Welch" in sg and "_welch_anova" in acmp and "_levene" in acmp and "_welch_t" in acmp)
    check("GamesHowell引导JASP", "Games-Howell" in sg and "JASP" in sg)
    check("正态性边界引导JASP", "Shapiro-Wilk" in sg and "Q-Q" in sg and "JASP" in sg)
    check("stats指南PROCESS域名", "processmacro.org" in sg and "hayesprocess.com" not in sg)
    check("网络分析稳定性检验", "corStability" in sg and "expected influence" in sg and "CS>.25" in sg)
    lit = tx("core/ai-literacy.md")
    check("AI素养agentic去魅", all(s in lit for s in ["能联网", "虚拟电脑", "关键动作", "动手查", "动手算"]))
    check("AI素养隐私去标识化", all(s in lit for s in ["去标识化", "身份证号", "验证码"]))
    check("START能力清单VIF真实", "_vif" in areg and "VIF" in st and "Bonferroni" in acmp)
    pt = tx("templates/proposal-template.md")
    check("开题功效依据", "G*Power" in pt and "300" in pt and "15%" in pt)
    check("开题伦理不预填α", "监护人书面知情同意" in pt and "注意力检查题" in pt and "不要预先填写" in pt and "慎用" in pt)
    check("开题数据处理补全", all(s in pt for s in ["分半", "探索性因子分析", "Welch", "卡方", "模型 1"]))
    pp = tx("templates/defense-ppt-outline.md")
    check("PPT伦理合规", ("监护人书面同意" in pp or "监护人书面知情同意" in pp) and "心理援助" in pp)
    check("PPT空白谨慎", "较少有研究" in pp and "差异" in pp)
    prt = tx("templates/progress-template.md")
    check("进度卡五指标功效分半", "长直线" in prt and "注意力题答错" in prt and "功效" in prt and "分半" in prt and "剔除" in prt)
    tc = tx("workflows/toolchain-guide.md")
    check("工具链脚本真实", "literature_organizer.py" in tc and (ROOT / "tools" / "literature_organizer.py").exists())
    check("工具链区分插件职责", "只负责把 Zotero 里的文献信息和 PDF 标注" in tc and "没有 \"Insert Citation\" 命令" in tc)
    check("工具链引用插件指引", "Citations** 插件" in tc and "Zotero Citations" in tc and "Add/Edit Citation" in tc)
    check("工具链Zotero7菜单", "设置（Zotero 6 旧版叫" in tc)
    cg2 = "tools/chart_generator.py"; cd = TD / "_chart"; cd.mkdir(exist_ok=True)
    o1 = cd / "m1.png"; r = run([cg2, "--variables", "AI,孤独,反刍,NSSI", "--type", "chain", "--output", str(o1)])
    check("模型图不传系数出图", r.returncode == 0 and o1.exists() and o1.stat().st_size > 5000, (r.stderr or "")[-200:])
    o2 = cd / "m2.png"; r = run([cg2, "-v", "AI,孤独,反刍,NSSI", "-c", "0.2,0.3", "-o", str(o2)])
    check("模型图少填补0", r.returncode == 0 and o2.exists(), (r.stderr or "")[-200:])
    r = run([cg2, "-v", "AI,孤独,反刍,NSSI", "-c", "a,b,c,d", "-o", str(cd / "m3.png")])
    check("非数字系数友好报错", r.returncode != 0 and "Traceback" not in (r.stderr or "") and "数字" in (r.stdout or ""))
    csrc = tx("tools/chart_generator.py")
    check("模型图无bold且系数可选", "fontweight='bold'" not in csrc and "default=None" in csrc)
    dd = TD / "_demo"; r = run(["tools/generate_demo_data.py", "--outdir", str(dd)])
    check("菜单7演示数据", r.returncode == 0 and (dd / "demo_survey.csv").exists() and (dd / "demo_scales.txt").exists(), (r.stderr or "")[-200:])
    check("菜单7默认归位工作区02", "我的工作区/02-问卷数据" in menu)
    r = run(["tools/literature_organizer.py", str(TD / "sample_literature.txt")])
    check("菜单5文献整理", r.returncode == 0 and "去重" in (r.stdout or ""), (r.stderr or "")[-200:])
    # 文献整理器吃"带中文表头的CSV"（paper_search 导出 / 知网导出 / Excel 另存）
    # 关键回归点：识别列名与解析必须用同一编码，否则 GBK 导出会静默导出 0 篇
    lit_tmp = new_tmp("litcsv")
    try:
        utf8_csv = lit_tmp / "utf8.csv"
        utf8_csv.write_text("序号,标题,作者,年份,期刊,DOI\n1,大学生AI依赖与孤独感,张三,2025,心理科学,10.1/x\n"
                            "2,反刍思维的中介作用,李四,2024,心理学报,\n", encoding="utf-8")
        r = run(["tools/literature_organizer.py", str(utf8_csv), "-o", str(lit_tmp / "o1.csv")])
        check("整理器吃UTF8标准CSV", r.returncode == 0 and "读取文献：2篇" in (r.stdout or ""), (r.stdout or "")[-200:])
        # 知网/Excel 另存的 GBK CSV：必须同样读出 2 篇（此前会解成乱码、静默 0 篇）
        gbk_csv = lit_tmp / "gbk.csv"
        gbk_csv.write_bytes("序号,标题,作者,年份,期刊\n1,大学生AI依赖与孤独感,张三,2025,心理科学\n"
                            "2,反刍思维的中介作用,李四,2024,心理学报\n".encode("gb18030"))
        r = run(["tools/literature_organizer.py", str(gbk_csv), "-o", str(lit_tmp / "o2.csv")])
        check("整理器吃GBK中文CSV", r.returncode == 0 and "读取文献：2篇" in (r.stdout or ""), (r.stdout or "")[-240:])
        # 有表头但无内容：必须中文提示而不是静默吐出 0 篇整理表
        empty_csv = lit_tmp / "empty.csv"
        empty_csv.write_text("序号,标题,作者\n1,,\n", encoding="utf-8")
        r = run(["tools/literature_organizer.py", str(empty_csv), "-o", str(lit_tmp / "o3.csv")])
        check("整理器空表不静默", r.returncode == 1 and "没有解析到任何一行文献" in (r.stdout or ""),
              (r.stdout or "")[-200:])
    finally:
        shutil.rmtree(lit_tmp, ignore_errors=True)
    check("菜单6提示回车", "直接回车" in menu)
    r = run(["tools/paper_search.py", "--query", "AI dependence", "--limit", "2", "--output", str(TD / "_ps.csv")], 90)
    check("菜单4英文检索不崩", r.returncode == 0 or "Traceback" not in (r.stderr or ""), (r.stderr or "")[-200:])
    psrc = tx("tools/paper_search.py")
    check("菜单4默认归位01", "我的工作区/01-文献PDF/英文文献.csv" in menu)
    check("去Sci-Hub改合法途径", "Sci-Hub" not in psrc and "馆际互借" in psrc and "mkdir" in psrc)
    gd = run(["tests/test_graceful_degradation.py"], 260)
    check("降级与闭环回归测试0", gd.returncode == 0, ((gd.stdout or "")[-600:]) + ((gd.stderr or "")[-200:]))

    # ---- v1.53.1 工程化：编码守卫 + auto_stats 拆包 ----
    # 覆盖 tools/、tests/ 与 doubao-skill/（轻量版自带 validate.py 也必须有守卫；
    # 此前只扫前两个目录，validate.py 的守卫存在与否没有回归保护）
    import ast as _ast
    # 编码守卫真正该管的是“能被单独运行的脚本”，故按模块级 if __name__ == "__main__" 判定，
    # 而不是按目录点名——原写法有盲区：tools/stats/ 与 tests/e2e_cases/ 都不在 glob 覆盖里。
    def _runnable(_p):
        try:
            _t = _ast.parse(_p.read_text(encoding="utf-8"))
        except SyntaxError:
            return False
        return any(isinstance(_n, _ast.If) and "__main__" in _ast.dump(_n.test) for _n in _t.body)
    guard_paths = [p for _d in ("tools", "tests", "doubao-skill")
                   for p in (ROOT / _d).rglob("*.py") if "__pycache__" not in p.parts]
    runnable_scripts = [p for p in guard_paths if _runnable(p)]
    no_guard = [str(p.relative_to(ROOT)) for p in runnable_scripts
                if "输出编码守卫" not in p.read_text(encoding="utf-8")]
    check("全部脚本有编码守卫", not no_guard, str(no_guard))
    check("编码守卫按可运行脚本判定", len(runnable_scripts) >= 25, "runnable=%d" % len(runnable_scripts))
    # 管道运行不得因 GBK 崩溃：默认编码下跑一致性自检，退出码必须为 0
    env_min = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    pc = subprocess.run([sys.executable, "tests/consistency_check.py"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=120, env=env_min)
    check("管道下一致性自检不崩", pc.returncode == 0 and "Traceback" not in (pc.stderr or ""),
          (pc.stderr or "")[-200:])
    check("管道下输出中文正常", "一致性自检" in (pc.stdout or "") and "\ufffd" not in (pc.stdout or ""))
    stats_pkg = ROOT / "tools" / "stats"
    check("auto_stats已拆包", stats_pkg.is_dir() and len(list(stats_pkg.glob("*.py"))) >= 10,
          "modules=%d" % len(list(stats_pkg.glob("*.py"))))
    check("CLI入口瘦身", len((ROOT / "tools" / "auto_stats.py").read_text(encoding="utf-8").splitlines()) < 300,
          "lines=%d" % len((ROOT / "tools" / "auto_stats.py").read_text(encoding="utf-8").splitlines()))
    check("原大文件已分解", not any(len(p.read_text(encoding="utf-8").splitlines()) > 700
                                 for p in list((ROOT / "tools").rglob("*.py"))
                                 + list((ROOT / "tests").rglob("*.py"))))
    check("sample_size复用路径已更新", "from stats.mathx import" in tx("tools/sample_size.py"))
    # ========== 大文件拆分（第一批）：尺寸棘轮与 regress 五件套接线 ==========
    sr = subprocess.run([sys.executable, "tests/size_ratchet.py"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=120)
    check("尺寸棘轮检查通过", sr.returncode == 0,
          (sr.stdout or "")[-400:] + (sr.stderr or "")[-200:])
    srn = subprocess.run([sys.executable, "tests/size_ratchet.py", "--selftest"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=120)
    check("尺寸棘轮尺子不空转", srn.returncode == 0 and "阴性自测通过" in (srn.stdout or ""),
          (srn.stdout or "")[-250:])
    check("存量冻结清单已入库且非空", (ROOT / "tests" / "size_baseline.txt").is_file()
          and any(not l.startswith("#") and l.strip()
                  for l in tx("tests/size_baseline.txt").splitlines()))
    check("统计拆分五件套齐全", all((ROOT / "tools" / "stats" / (m + ".py")).is_file()
                                   for m in ["correlation", "regression", "mediation",
                                             "moderation", "outliers"]))
    fac82 = tx("tools/stats/regress.py")
    check("拆分后历史入口仅再导出且六个公开函数仍可导入",
          all(("from .%s import" % m) in fac82 for m in ["correlation", "mediation", "moderation",
                                                         "outliers", "regression"])
          and all(fn in fac82 for fn in ["correlation_matrix", "partial_correlation_analysis",
                                         "linear_regression", "mediation_analysis",
                                         "moderation_analysis", "mahalanobis_outliers"])
          and len(fac82.splitlines()) < 40, "lines=%d" % len(fac82.splitlines()))
    check("一致性检查覆盖子包", "rglob" in tx("tests/consistency_check.py"))
    # 断言片段一旦被“搬出壳但没挂进顺序清单”，它里面所有断言会静默不跑——这是拆分最怕的事故，
    # 故要求磁盘上的片段与壳里的 FRAGMENTS 完全同序同名。
    _frag_disk = sorted(p.name for p in (ROOT / "tests" / "e2e_cases").glob("*.py")
                        if "__pycache__" not in p.parts)
    check("断言片段无孤儿且顺序清单完整", _frag_disk == list(FRAGMENTS) and len(_frag_disk) >= 14,
          "磁盘%d 清单%d" % (len(_frag_disk), len(FRAGMENTS)))
    check("片段正文合计守恒（壳里不再藏断言）",
          sum(1 for _f in _frag_disk for _l in (ROOT / "tests" / "e2e_cases" / _f).read_text(
              encoding="utf-8").splitlines() if "    check(" in _l) >= 600
          and sum(1 for _l in tx("tests/full_e2e.py").splitlines() if "    check(" in _l) == 0,
          "壳内 check 调用数应为 0")
    # auto_stats 拆包后必须能被 runpy.run_path 调用：runpy 不把脚本目录加入 sys.path，
    # 少了显式 sys.path 引导就会 ModuleNotFoundError: stats（tests/test_graceful_degradation.py 走的正是这条路）
    rpy = subprocess.run(
        [sys.executable, "-c",
         "import runpy,sys; sys.argv=['auto_stats.py','tests/test-data/demo_survey.csv','--profile'];"
         " runpy.run_path('tools/auto_stats.py', run_name='__main__')"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    check("auto_stats可被runpy调用", rpy.returncode == 0 and "ModuleNotFoundError" not in (rpy.stderr or ""),
          (rpy.stderr or "")[-250:])
    # ---- v1.53.1 版本日志单文件化：CHANGELOG.md 是唯一版本历史，其余人只留指针 ----
    chg = tx("CHANGELOG.md")
    check("CHANGELOG存在且带日期索引", "版本索引（含日期）" in chg and "_发布包" in chg)
    check("README指向CHANGELOG", "CHANGELOG.md" in rm)
    check("ROADMAP指向CHANGELOG", "CHANGELOG.md" in tx("ROADMAP.md"))
    check("PROJECT_PLAN指向CHANGELOG", "CHANGELOG.md" in tx("PROJECT_PLAN.md"))
    check("版本历史不再四处重复", len(tx("ROADMAP.md").splitlines()) < 60
          and len(tx("README.md").splitlines()) < 200, "roadmap=%d readme=%d" % (
              len(tx("ROADMAP.md").splitlines()), len(tx("README.md").splitlines())))
    # 版本号三处一致：从 START.md 解析当前版本，要求 CHANGELOG 与 README 都能对上
    # （不写死版本号，避免每次发版都要改断言）
    mver = re.search(r"版本\s*(v[\d.]+)", st)
    cur_ver = mver.group(1) if mver else ""
    check("版本号三处一致", bool(cur_ver) and cur_ver in chg and cur_ver in rm,
          "解析到 START=%s, CHANGELOG命中=%s, README命中=%s" % (
              cur_ver or "(未解析到)", cur_ver in chg, cur_ver in rm))
    check("DEVELOPMENT引用CHANGELOG", "CHANGELOG.md" in tx("DEVELOPMENT.md"))

