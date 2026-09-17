# -*- coding: utf-8 -*-
"""
thesis-ai-coach 全量端到端回归（测试金字塔 L7）。
随项目包分发：开发仓库根目录或解压后的干净副本里都能直接运行：
    python tests/full_e2e.py
覆盖：统计/清洗/样本量/模型图/文献脚本真实运行 + 文档-代码一致性 + 合规与事实断言。
约需 3-5 分钟（含 Bootstrap 5000、英文文献联网检索、缺库降级回归）。
退出码 0 = 全部通过；非 0 = 有失败项（见 FAIL 行）。
运行中会在 tests/test-data 生成并自动清理临时产物，结束时恢复被跟踪的基准样例。
"""
import os, sys, subprocess, csv, re, shutil
from pathlib import Path
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
TD = ROOT / "tests" / "test-data"
results = []

def check(n, c, e=""):
    results.append((n, bool(c), e)); print(("PASS " if c else "FAIL ") + n + ("  " + str(e) if e and not c else ""))

def run(a, t=240):
    try:
        return subprocess.run([sys.executable] + a, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=t)
    except subprocess.TimeoutExpired as ex:
        class R:
            returncode = "TIMEOUT"
            stdout = ex.stdout if isinstance(ex.stdout, str) else ""
            stderr = "timeout"
        return R()

def tx(rr): return (ROOT / rr).read_text(encoding="utf-8")
def rt(p): return Path(p).read_text(encoding="utf-8-sig", errors="replace") if Path(p).exists() else ""

# 备份可能被覆盖的被跟踪基准样例，结束时恢复（干净副本无 git，靠这里还原）
BACKUP = {}
for name in ["demo_survey.csv", "demo_scales.txt", "sample_literature.txt"]:
    f = TD / name
    if f.exists():
        BACKUP[name] = f.read_bytes()

def cleanup():
    # demo_survey_*.csv/png 只匹配带下划线后缀的生成物，不会动基准 demo_survey.csv
    for pat in ["_e2e*", "_special*", "_ps.csv", "demo_survey_*.csv", "demo_survey_*.png", "demo_survey_cleaned.csv"]:
        for f in TD.glob(pat):
            if f.is_file() and f.name != "demo_survey.csv":
                try: f.unlink()
                except OSError: pass
    for d in [TD / "_chart", TD / "_demo"]:
        shutil.rmtree(d, ignore_errors=True)
    for name, b in BACKUP.items():
        (TD / name).write_bytes(b)
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)

try:
    for pat in ["_e2e*", "demo_survey_*.csv", "demo_survey_*.png"]:
        for f in TD.glob(pat):
            if f.is_file(): f.unlink()
    r = run(["tools/data_cleaner.py", str(TD / "demo_survey.csv"), "--scales", str(TD / "demo_scales.txt"),
             "-o", str(TD / "_e2e_cleaned.csv")])
    nrows = 0; p = TD / "_e2e_cleaned.csv"
    if p.exists(): nrows = sum(1 for _ in csv.reader(open(p, encoding="utf-8-sig"))) - 1
    check("清洗后192份", nrows == 192, f"rows={nrows} rc={r.returncode}")
    check("清洗报告生成", (TD / "demo_survey_清洗报告.csv").exists())
    r = run(["tools/auto_stats.py", str(TD / "demo_survey.csv"), "--scales", str(TD / "demo_scales.txt"),
             "--y", "NSSI", "--x", "AI情感依赖", "--mediators", "孤独感,反刍思维", "--boot", "5000"], 300)
    stat = rt(TD / "demo_survey_统计结果.csv"); rel = rt(TD / "demo_survey_信度分析.csv")
    med = rt(TD / "demo_survey_中介效应.csv"); chi = rt(TD / "demo_survey_卡方检验.csv")
    check("auto_stats退出0", r.returncode == 0, r.stderr[-300:])
    alpha = {}
    try:
        for row in csv.DictReader(open(TD / "demo_survey_信度分析.csv", encoding="utf-8-sig")):
            alpha[row["量表"]] = float(row["Cronbach_alpha"])
    except Exception: pass
    ea = {"AI情感依赖": .93, "孤独感": .925, "反刍思维": .938, "NSSI": .933}
    check("α基准", all(alpha.get(k) is not None and abs(alpha[k] - v) < .0051 for k, v in ea.items()), str(alpha))
    check("分半SB列", "分半SpearmanBrown" in rel)
    check("Harman38.49", "38.49" in r.stdout)
    check("相关基准", all(s in stat for s in [".269", ".459", ".393"]))
    check("链式基准", ".034" in med and ".012" in med and ".063" in med)
    check("卡方p.418", ".418" in chi)
    heat = TD / "demo_survey_相关热图.png"
    check("热图生成", heat.exists() and heat.stat().st_size > 50000)
    try:
        import matplotlib.image as mi
        im = mi.imread(str(heat)); check("热图像素>300", im.shape[0] > 300, im.shape)
    except Exception as e:
        check("热图读取", False, str(e))
    r3 = run(["tools/sample_size.py"]); check("样本量速查", r3.returncode == 0 and ("85" in r3.stdout or "179" in r3.stdout))
    # Welch ANOVA 数值回归：强异方差下锁定 F/df1/df2/p，防止分母自由度公式退回 (k^3-k)/(3D)
    # 历史缺陷：df2 被放大 k 倍、p 系统性偏小（强异方差时可翻转显著性）；基准经教科书公式＋scipy 三方核对
    try:
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))
        import stats.compare as _wcmp
        _wg = [[1, 2, 2, 3, 2, 1, 3, 2], [6, 9, 14, 7, 12, 5, 13, 8], [2, 3, 1, 4, 2, 3, 2, 3]]
        _wF, _wd1, _wd2, _wp = _wcmp._welch_anova(_wg)
        check("Welch强异方差数值基准", _wF is not None and abs(_wF - 16.7979) < 2e-3 and _wd1 == 2
              and abs(_wd2 - 12.5210) < 2e-3 and _wp is not None and abs(_wp - 2.8522e-4) < 2e-5,
              f"F={_wF} df1={_wd1} df2={_wd2} p={_wp}（错误式会得 df2≈37.56、p≈6.1e-6）")
    except Exception as _we:
        check("Welch强异方差数值基准", False, repr(_we))
    p1 = run(["tests/consistency_check.py"]); check("一致性0", p1.returncode == 0, p1.stdout[-200:])
    g = ROOT / "_ghost_doc_xyz.md"
    g.write_text("运行 `tools/ghost_tool_xyz.py --fake-switch-xyz`，导出 `_幽灵分析.csv`，见 [假文档](ghost_page_xyz.md)，路径 `我的工作区/99-ghost/`", encoding="utf-8")
    p2 = run(["tests/consistency_check.py"]); g.unlink(); o2 = p2.stdout
    for nm, s in [("幽灵脚本", "ghost_tool_xyz.py"), ("假开关", "--fake-switch-xyz"), ("假导出", "幽灵分析.csv"),
                  ("假文档", "ghost_page_xyz.md"), ("假路径", "99-ghost")]:
        check("变异抓" + nm, s in o2)
    check("变异非0", p2.returncode != 0)
    qt = tx("templates/questionnaire-template.md")
    check("问卷注意力题", "注意力检查" in qt and "质量控制题" in qt)
    check("问卷时长埋点", "作答时长" in qt)
    check("问卷多选题示例", "可多选" in qt and "不计入任何量表" in qt)
    cr = tx("core/coach-rules.md")
    check("coach5埋点", "注意力检查题" in cr and "作答时长" in cr)
    check("coach5多选填空", "多选题" in cr and "scales.txt 时勿列入" in cr)
    check("coach6样本量", "sample_size.py" in cr)
    check("coach7五指标", "低变异" in cr and "注意力检查题答错" in cr)
    menu = tx("tools/menu.py"); check("menu第8项", "【8/9】" in menu and "sample_size.py" in menu)
    qs = tx("QUICKSTART.md"); check("QS菜单8", "8. 开题样本量" in qs)
    check("QS流程顺序", qs.find("查文献读文献") < qs.find("开题报告/开题答辩"))
    bad = []
    for md in ROOT.rglob("*.md"):
        t = md.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"0[123](?!-)(?:文献PDF|问卷数据|分析结果)", t): bad.append(md.name)
        if re.search(r"(?<!-)(?<!\d)文献PDF/", t): bad.append(md.name + ":裸")
    check("目录名统一", not bad, str(sorted(set(bad))))
    st = tx("START.md"); check("START第七步", "## 第七步：开始引导" in st and "第五步半" not in st)
    las = tx("workflows/literature-auto-search.md"); check("知网落点", "我的工作区/01-文献PDF/" in las and "`文献PDF/`" not in las)
    check("批量下载红线阈值", "单次登录全文下载不超过约 **30 篇**" in las and "30-50 篇以内" in las and "永久封禁" in las)
    check("全文不传播不批量工具", "不得传播、上传到公开网络" in las and "禁用迅雷" in las and "不整期/整卷下载" in las)
    check("题录总表归文献区", "文献总表 CSV 都归文献区" in las and "文献总表 CSV 放 `我的工作区/03" not in las)
    for d in ["01-文献PDF", "02-问卷数据", "03-分析结果"]: check("目录" + d, (ROOT / "我的工作区" / d).is_dir())
    bat = (ROOT / "启动工具箱.bat").read_bytes(); cc = bat.count(b"\r\n"); lo = bat.count(b"\n") - cc
    check("bat编码行尾", bat[:3] != b"\xef\xbb\xbf" and cc > 20 and lo == 0, f"crlf={cc} lf={lo}")
    df = tx("workflows/defense-guide.md")
    check("答辩24问+伦理", "24问" in df and "监护人书面知情同意" in df and "剔除" in df and "数据怎么保管" in df)
    et = tx("psychology/ethics.md")
    check("热线12356首选", "12356" in et and "国卫医政函" in et)
    check("400不误标全国", "全国心理援助热线：400-161-9995" not in et and "希望24热线（社会公益热线）" in et)
    check("即刻危机120/110", "120或110" in et)
    check("未成年人assent分层", "书面 assent" in et and "尊重未成年人的拒绝（dissent）" in et and "学生本人同意（assent）简短模板" in et)
    check("敏感话题风险预案", "研究前先定风险预案" in et and "校园投放伦理" in et)
    check("数据保存年限口径", "不少于5年" in et and "至少保存3年" not in et)
    check("问卷模板12356", "12356" in qt)
    check("问卷模板学段适配", "学段" in qt and "中学生版" in qt and "大学生版" in qt and "仅大学生填写；中学生样本删除" in qt)
    check("问卷性别第三项与最小化", "其他/不愿透露" in qt and "个人信息最小化" in qt)
    check("答辩答法12356", "12356" in df)
    es = tx("workflows/environment-setup.md")
    check("JASP中介内置+PROCESS可选", "Regression → Mediation" in es and "PROCESS 模块" in es and "Model 6" in es)
    check("Mac不预装Python", "不再预装" in es and "python3" in es)
    check("Zotero样式非插件", "引用样式" in es and "Zotero Style" not in es)
    check("Python勾选PATH", "Add python.exe to PATH" in es)
    check("只从官网下载", "只从官网下载" in es)
    check("coach答辩24问", "24个高频问题库" in cr and "20个高频问题库" not in cr)
    check("README能力表24", "24个高频问题" in tx("README.md"))
    check("coach12阶段", "12阶段工作流" in cr and "阶段11：答辩准备" in cr)
    check("coach三检查闸", "动机闸" in cr and "质量闸" in cr and "留痕闸" in cr)
    check("coach文献量口径", "30-50篇文献收集" in cr and "重点10-15篇" in cr)
    pg = tx("workflows/proposal-guide.md")
    check("开题脚本不进论文", "不写进开题报告" in pg and "公认软件" in pg)
    check("量表授权邮件", "书面许可" in pg and "授权邮件" in pg)
    check("开题八节对应", "预期困难与对策" in pg and "研究创新点" in pg)
    check("样本量口径统一", "sample_size.py" in pg and "链式≥300" in pg and "G*Power" in pg)
    ad = tx("templates/ai-usage-declaration.md")
    check("AI声明如实口径", "核心学术贡献由本人独立完成" in ad and "AI未参与的内容" not in ad)
    check("AI声明亲自核实", "亲自检索、阅读与核实" in ad)
    check("AI声明三版本", "详细版" in ad and "简洁版" in ad and "学校有固定格式" in ad)
    pr = tx("workflows/paper-reading-guide.md")
    check("精读IMRaD卡片", "IMRaD" in pr and "与本研究的关系" in pr)
    check("精读分层数量", "精读（10-15篇）" in pr and "泛读（20-40篇）" in pr)
    check("进度卡12阶段", "11 答辩准备" in tx("我的工作区/我的论文进度.md"))
    cm = ROOT / "workflows" / "communication-guide.md"
    check("沟通指南文件存在", cm.exists())
    if cm.exists():
        cg = cm.read_text(encoding="utf-8")
        check("沟通12场景", all(s in cg for s in ["场景1", "场景12", "带选择题", "12356", "关键决策日志"]))
        check("沟通原则与礼仪", "定期" in cg and "附件命名" in cg and "对事不对人" in cg)
    check("coach阶段10引用", "workflows/communication-guide.md" in cr)
    check("START导航沟通", "communication-guide.md" in st)
    rm = tx("README.md"); check("README沟通清单", "communication-guide.md" in rm)
    check("README数字修正", "16种" in rm and "10种统计方法" not in rm)
    daa = tx("workflows/data-analysis-auto.md")
    check("分析流程多选说明", "多选题" in daa and "开放填空题" in daa and "scales.txt" in daa)
    check("JASP链式走Process模块", "Process 模块后选 Model 6" in daa and "原生支持链式中介" not in daa)
    check("PROCESS官网域名", "processmacro.org" in daa and "hayesprocess.com" not in daa)
    check("样本量质量闸口径", "链式等复杂模型建议 300" in daa and "至少>150" not in daa)
    wg = tx("workflows/writing-guide.md")
    check("写作结果章节", "简单斜率" in wg and "热图" in wg and "卡方" in wg)
    check("结果章顺序规范", "人口学差异（t/方差分析/卡方等）→相关" in wg)
    sp = run(["tests/test_special_columns.py"]); check("特殊列测试0", sp.returncode == 0, (sp.stdout or "")[-300:] + (sp.stderr or "")[-200:])
    wp = tx("tools/wjx_preprocess.py"); dc = tx("tools/data_cleaner.py")
    check("预处理特殊列识别", "detect_special_column" in wp and "multi" in wp)
    check("清洗器排除0/1", "{0.0, 1.0}" in dc and "可多选" in dc)
    check("紧急三红线", "不可破的三条红线" in cr and "不编造" in cr and "延期" in cr)
    check("紧急逐日任务", "D1" in cr and "7天版" in cr and "1天版" in cr and "3天版" in cr)
    sl = tx("psychology/scale-library.md")
    check("NSSI循证量表", all(s in sl for s in ["FASM", "C-FASM", "DSHI", "ISAS", "Klonsky"]))
    check("幻觉量表已删", "ASFQ" not in sl and "SBI" not in sl and "Nixon" not in sl)
    check("RRQ修正24题", "24 | 自我反刍" in sl and "RRQ-C" in sl)
    check("RRQ旧10题删除", "反刍思维量表（RRQ） | 10" not in sl)
    check("AAS18题", "成人依恋量表（AAS） | 18" in sl and "各6题" in sl)
    check("FASM拼写Kelley", "Lloyd, Kelley & Hope, 1997" in sl and "Lloyd, Kelly" not in sl)
    check("UCLA第3版1996", "Russell, 1996（V3" in sl and "R-UCLA，第3版" not in sl)
    check("CDRISC简版作者", "Campbell-Sills & Stein, 2007" in sl)
    check("MPAI原始Leung", "Leung, 2008" in sl)
    po0 = tx("templates/paper-outline.md")
    check("大纲伦理埋点", "监护人书面知情同意" in po0 and "注意力检查题" in po0 and "Bootstrap 5000" in po0)
    check("大纲结果章完整", all(s in po0 for s in ["平行分析", "Games-Howell", "卡方", "简单斜率", "偏态"]))
    sg = tx("psychology/stats-guide.md")
    # v1.53.1：auto_stats 已拆为 tools/stats/ 包，实现函数按所属模块核对（不再只看 CLI 入口）
    acmp = tx("tools/stats/compare.py"); areg = tx("tools/stats/regress.py")
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
    guard_paths = (sorted((ROOT / "tools").glob("*.py"))
                   + sorted((ROOT / "tests").glob("*.py"))
                   + sorted((ROOT / "doubao-skill").glob("*.py")))
    no_guard = [str(p.relative_to(ROOT)) for p in guard_paths
                if "输出编码守卫" not in p.read_text(encoding="utf-8")]
    check("全部脚本有编码守卫", not no_guard, str(no_guard))
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
                                 for p in list((ROOT / "tools").glob("*.py")) + list(stats_pkg.glob("*.py"))))
    check("sample_size复用路径已更新", "from stats.mathx import" in tx("tools/sample_size.py"))
    check("一致性检查覆盖子包", "rglob" in tx("tests/consistency_check.py"))
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

    # ---- v1.54 学生自己做网页：引导手册 + 预览器 + 三个范例 + 工作区 ----
    wg = tx("workflows/webpage-guide.md")
    check("网页指南含硬规矩", all(s in wg for s in ["单文件", "自包含", "不引用外部资源", "不放个人隐私", "网页不是论文成果"]))
    check("网页指南含五类网页", all(s in wg for s in ["文献笔记网页", "数据分析结果看板", "研究流程图", "量表与问卷速查", "论文进度看板"]))
    check("网页指南含三闸", all(s in wg for s in ["闸 1 动机闸", "闸 2 质量闸", "闸 3 留痕闸"]))
    check("网页指南警示勿抄范例", "不要抄" in wg)
    ex = ROOT / "templates" / "网页范例"
    ex_pages = [ex / "01-文献笔记网页" / "index.html",
                ex / "02-术语词典网页" / "index.html",
                ex / "03-研究流程图" / "research-flow.html"]
    check("三个网页范例齐备", all(p.exists() for p in ex_pages),
          str([p.name for p in ex_pages if not p.exists()]))
    check("范例带勿直接使用标注",
          all("范例，请勿直接使用" in p.read_text(encoding="utf-8", errors="replace") for p in ex_pages))
    check("范例README提示只学做法",
          "只用来学" in tx("templates/网页范例/README.md") or
          ("可以学的是" in tx("templates/网页范例/README.md")
           and "只能参考代码结构与交互设计" in tx("templates/网页范例/README.md")))
    pw = tx("tools/webpage_preview.py")
    check("预览器只读", "SimpleHTTPRequestHandler" in pw and "do_POST" not in pw and "do_PUT" not in pw)
    check("预览器默认只绑本机", "127.0.0.1" in pw and "--lan" in pw)
    check("预览器防路径穿越", "normpath" in pw and "relative_to" in pw and "反斜杠" in pw)
    check("预览器声明charset", "charset=utf-8" in pw)
    pl = run(["tools/webpage_preview.py", "templates/网页范例", "--list"])
    check("预览器--list可运行", pl.returncode == 0 and "index.html" in (pl.stdout or ""), (pl.stderr or "")[-200:])
    wdir = ROOT / "我的工作区" / "04-网页"
    check("工作区04-网页就位", wdir.is_dir() and (wdir / "把网页放这里.txt").exists())
    check("菜单第9项", "【9/9】" in menu and "webpage_preview.py" in menu)
    check("网页能力已登记到入口",
          "webpage-guide.md" in st and "webpage_preview.py" in st and "webpage-guide.md" in cr)
    check("README登记网页能力", "webpage-guide.md" in rm and "webpage_preview.py" in rm)
    check("QUICKSTART登记第9项", "预览我做的网页" in tx("QUICKSTART.md"))
    check("工作区说明含04-网页", "04-网页" in tx("我的工作区/先读我.md"))

    # ---- v1.55 豆包 Skill 轻量版（doubao-skill/ 独立分发子包，自带 validate.py 门禁）----
    SK = ROOT / "doubao-skill"
    check("Skill目录就位", SK.is_dir() and (SK / "SKILL.md").exists())
    skr = run(["doubao-skill/validate.py"], 120)
    check("Skill自检退出0", skr.returncode == 0 and "全部通过" in (skr.stdout or ""),
          ((skr.stdout or "")[-400:]) + ((skr.stderr or "")[-200:]))
    skm = (SK / "SKILL.md").read_text(encoding="utf-8")
    check("Skill默认自然风格", "自然专业（默认" in skm and "不套任何人设" in skm)
    check("Skill鼓励默认可关", "标准（默认" in skm and "关闭鼓励" in skm)
    stage_list = list((SK / "stages").glob("stage-*.md"))
    check("Skill阶段12个", len(stage_list) == 12, "n=%d" % len(stage_list))
    check("Skill三闸入阶段", all(all(g in p.read_text(encoding="utf-8") for g in ("动机闸", "质量闸", "留痕闸"))
                                  for p in stage_list))
    skp = (SK / "references" / "coaching-protocol.md").read_text(encoding="utf-8")
    check("Skill危机与紧急", all(s in skp for s in ("12356", "120 或 110", "紧急模式")))
    ske = (SK / "references" / "encouragement-guide.md").read_text(encoding="utf-8")
    check("Skill鼓励P0不包装", "P0 不包装" in ske and "成长型思维" in ske)
    check("Skill进度模板", (SK / "templates" / "我的论文进度模板.md").exists())
    check("Skill轻量版不虚构工具", "不含脚本" in (SK / "references" / "tools.md").read_text(encoding="utf-8"))
    # 阴性测试：在临时副本植入断链与占位，validate.py 必须判失败（防止自检是空壳）
    import tempfile
    neg = Path(tempfile.mkdtemp(dir=TD, prefix="_skill_neg_"))
    try:
        shutil.copytree(SK, neg / "doubao-skill")
        vf = neg / "doubao-skill" / "SKILL.md"
        vf.write_text(vf.read_text(encoding="utf-8") + "\n见 `ghost-ref-xyz.md`，TODO 待补充\n",
                      encoding="utf-8")
        nr = run([str(neg / "doubao-skill" / "validate.py")], 60)
        check("Skill自检能抓变异", nr.returncode != 0 and "ghost-ref-xyz.md" in (nr.stdout or ""),
              "rc=%s" % nr.returncode)
    finally:
        shutil.rmtree(neg, ignore_errors=True)
    check("一致性检查跳过Skill子包", "doubao-skill" in tx("tests/consistency_check.py"))

    # ---- v1.56 本体反馈协议+鼓励系统（学习成熟技能范式：强制基准/分级/门禁/行为自测）----
    cp_path = ROOT / "core" / "coaching-protocol.md"
    eg_path = ROOT / "core" / "encouragement-guide.md"
    bt_path = ROOT / "tests" / "behavior-self-test.md"
    check("v156反馈协议文件", cp_path.exists() and bt_path.exists() and eg_path.exists())
    cp = cp_path.read_text(encoding="utf-8")
    eg = eg_path.read_text(encoding="utf-8")
    bt = bt_path.read_text(encoding="utf-8")
    check("v156协议核心结构", all(s in cp for s in ("引导循环", "反馈三段式", "P0", "P1", "P2", "回复前门禁")))
    check("v156协议触发与边界", all(s in cp for s in ("触发边界", "边界情况", "学生长时间失联", "复合请求")))
    check("v156协议学生指令", "关闭鼓励" in cp and "读进度卡继续" in cp and "跳到第 N 步" in cp)
    check("v156协议危机口径", "12356" in cp and "120 或 110" in cp and "不允诺保密" in cp)
    check("v156鼓励四理论依据", all(s in eg for s in ("正强化", "成长型思维", "反馈干预理论", "自我决定理论")))
    check("v156鼓励三档与默认", all(s in eg for s in ("标准", "精简", "关闭", "默认")))
    check("v156鼓励切换指令", all(s in eg for s in ("关闭鼓励", "鼓励精简一点", "开启鼓励")))
    check("v156鼓励P0不包装与奖赏", "P0 不包装" in eg and "里程碑" in eg and "挫折时刻协议" in eg)
    check("v156鼓励禁夸天赋", "禁止夸天赋" in eg and "每轮至多一次肯定" in eg)
    check("v156鼓励四人格措辞", all(s in eg for s in ("专业导师（默认）", "霸道总裁（可选）", "知心姐姐（可选）", "小奶狗（可选）")))
    check("v156行为自测用例与声明", "T1 " in bt and "T32" in bt and "测试计划" in bt and "不是" in bt)
    check("v156coach人格鼓励正交", "人格只管" in cr and "鼓励档" in cr and "core/encouragement-guide.md" in cr)
    check("v156coach旧鼓励表述移除", "不给无意义鼓励" not in cr)
    check("v156coach卡壳临时降档", "临时降一档" in cr)
    check("v156coach阶段0鼓励档", "鼓励档（默认" in cr)
    check("v156coach引用反馈协议", "core/coaching-protocol.md" in cr and "反馈三段式" in cr)
    check("v156START必读五份", "先读这五份" in st and "core/coaching-protocol.md" in st and "core/encouragement-guide.md" in st)
    check("v156START开场第五问", "关闭鼓励" in st and "反馈方式" in st)
    card_t = tx("templates/progress-template.md"); card_w = tx("我的工作区/我的论文进度.md")
    check("v156双进度卡鼓励档行", "鼓励反馈档" in card_t and "鼓励反馈档" in card_w)
    check("v156入口登记齐全", all(s in tx("AGENTS.md") for s in ("coaching-protocol.md", "encouragement-guide.md"))
          and "关闭鼓励" in rm and "关闭鼓励" in tx("QUICKSTART.md"))
    check("v156鼓励与Skill口径一致",
          "鼓励精简一点" in eg and "鼓励精简一点" in skm and "反馈三段式" in skp and "P0/P1/P2" in skp)
    # 注意：不能用 `"T1" in bt` 这类子串判断（"T1" 会匹配上 T10–T19），
    # 必须真正抽出编号再验连续性，否则删掉中间某条也发现不了
    bt_nums = sorted(int(x) for x in re.findall(r"\| T(\d+) \|", bt))
    check("v156自测用例编号连续", bt_nums == list(range(1, len(bt_nums) + 1)) and len(bt_nums) >= 32,
          "n=%d nums=%s" % (len(bt_nums), bt_nums[:5]))
    check("v156情绪与挫折用例", "T31" in bt and "T32" in bt and "接住情绪" in bt and "不得评价情绪本身" in bt)

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
          "手机做不了" in skm and "第 8 阶段只能做一半" in skm
          and "本阶段需要电脑" in tx("doubao-skill/stages/stage-8-analysis.md")
          and "必须回电脑" in tx("doubao-skill/stages/stage-7-data.md")
          and "预处理" in tx("doubao-skill/stages/stage-7-data.md"))
    check("v12工具表含手机对照", "手机上能用什么" in tx("doubao-skill/references/tools.md"))
    check("v12学校示例不绑定某校", "九江" not in tx("doubao-skill/references/tools.md"))
    # 合并单文件：生成到临时目录（不依赖项目外的 _发布包/，保证干净副本也能跑）
    bsp = ROOT / "doubao-skill" / "build_mobile_single.py"
    check("v12合并单文件生成器存在", bsp.exists())
    if bsp.exists():
        md_dir = Path(tempfile.mkdtemp(dir=TD, prefix="_v12mobile_"))
        try:
            tg = md_dir / "single.md"
            rg = run(["doubao-skill/build_mobile_single.py", "--out", str(tg)], 120)
            check("v12合并单文件可生成", rg.returncode == 0 and tg.exists(), (rg.stderr or "")[-200:])
            stext = tg.read_text(encoding="utf-8") if tg.exists() else ""
            check("v12合并单文件自包含",
                  all(s in stext for s in ("手机做不了", "引导循环", "阶段 11：答辩准备", "strict-ceo")),
                  "len=%d" % len(stext))
            check("v12合并单文件规模合理", len(stext) > 50000, "chars=%d" % len(stext))
            check("v12合并版排除维护者文件", "Skill 行为自测用例" not in stext)
            rc2 = run(["doubao-skill/build_mobile_single.py", "--check", "--out", str(tg)], 60)
            check("v12合并版同步校验通过", rc2.returncode == 0, (rc2.stdout or "")[-150:])
        finally:
            shutil.rmtree(md_dir, ignore_errors=True)
finally:
    cleanup()

fails = [x for x in results if not x[1]]
print(f"\n==== 共 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)} ====")
sys.exit(1 if fails else 0)
