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
    menu = tx("tools/menu.py"); check("menu第8项", "【8/8】" in menu and "sample_size.py" in menu)
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
    sg = tx("psychology/stats-guide.md"); asrc = tx("tools/auto_stats.py")
    check("stats能力真实", "Welch" in sg and "_welch_anova" in asrc and "_levene" in asrc and "_welch_t" in asrc)
    check("GamesHowell引导JASP", "Games-Howell" in sg and "JASP" in sg)
    check("正态性边界引导JASP", "Shapiro-Wilk" in sg and "Q-Q" in sg and "JASP" in sg)
    check("stats指南PROCESS域名", "processmacro.org" in sg and "hayesprocess.com" not in sg)
    check("网络分析稳定性检验", "corStability" in sg and "expected influence" in sg and "CS>.25" in sg)
    lit = tx("core/ai-literacy.md")
    check("AI素养agentic去魅", all(s in lit for s in ["能联网", "虚拟电脑", "关键动作", "动手查", "动手算"]))
    check("AI素养隐私去标识化", all(s in lit for s in ["去标识化", "身份证号", "验证码"]))
    check("START能力清单VIF真实", "_vif" in asrc and "VIF" in st and "Bonferroni" in asrc)
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
finally:
    cleanup()

fails = [x for x in results if not x[1]]
print(f"\n==== 共 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)} ====")
sys.exit(1 if fails else 0)
