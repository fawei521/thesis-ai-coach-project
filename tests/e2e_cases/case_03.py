# -*- coding: utf-8 -*-
"""账号密码红线（P0）：项目任何文件都不得出现"AI 代填/凭据文件"这类写法 ----
full_e2e.py 顺序片段 3/14（原第 462–615 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ---- 账号密码红线（P0）：项目任何文件都不得出现"AI 代填/凭据文件"这类写法 ----
    # 起因：并行会话把"AI 读取本地凭据文件代填图书馆密码"写进了 literature-auto-search，
    # 与 CONSTITUTION 第七条、ai-literacy、behavior-self-test T25 三处直接冲突。
    # 该缺陷此前能一路过关，是因为没有任何断言守这条红线——本组断言即为它补的闸。
    cred_md = [p for p in ROOT.rglob("*.md")
               if "CHANGELOG" not in p.name and p.name not in ("e2e-test.md", "behavior-self-test.md")
               and "doubao-skill" not in p.parts]
    cred_hits = []
    for p in cred_md:
        t = p.read_text(encoding="utf-8", errors="ignore")
        for bad in ("AI代填", "授权AI代填", "library-login.local.json", "代填并提交", "读取凭据文件"):
            if bad in t:
                cred_hits.append(f"{p.name}:{bad}")
    check("凭据代填红线", not cred_hits, str(sorted(set(cred_hits))))
    check("登录交学生本人", "登录一律由学生本人" in las or "学生本人输入" in las)
    check("拒绝代填明确入工作流", "不索取、不接受、不存储、不代填" in las and "T25" in las)
    # v1.92（P9）：包里只带空白模板。原先随包分发的两份"就地填写"文件（进度卡、检索记录）
    # 会在学生装新包时把自己的记录盖成空白——现在从源头断掉，填写版由菜单第 22 项缺才生成。
    check("检索记录模板存在", (ROOT / "templates" / "检索记录模板.md").exists())
    check("进度卡基线存在", (ROOT / "templates" / "progress-template.md").exists())
    check("检索记录入口", "检索记录.md" in las and "检索记录.md" in tx("我的工作区/先读我.md"))
    check("进度卡接检索留痕", "文献与检索留痕" in tx("templates/progress-template.md"))
    check("菜单5接受CSV", "标准 CSV" in menu and "txt" in menu)
    # 发布形态安全：预置文件必须在 git 索引里，否则 git archive 打出的包会缺它，
    # 而开发树里看着"明明存在"（.gitignore 的目录级排除曾把新建的 检索记录.md 挡在包外）。
    if (ROOT / ".git").exists():
        ls = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(ROOT))
        tracked = set(ls.stdout.split("\0")) if ls.returncode == 0 else set()
        want = {"templates/检索记录模板.md", "templates/progress-template.md", "我的工作区/先读我.md"}
        check("预置文件已入库", want <= tracked, str(sorted(want - tracked)))
        # v1.92 的根治闸：这些路径一旦重新入库，装新包就又会把学生的记录盖成空白模板。
        # 它们改由 tools/setup_workspace.py 在缺失时从模板复制生成，所以"不在包里"才是正确状态。
        # 这里的硬编码是刻意的第二来源：往 GENERATED 里加东西，必须同时在这里交代"它为什么不进包"
        filled = {"我的工作区/我的论文进度.md", "我的工作区/01-文献PDF/检索记录.md",
                  "我的工作区/我的毕业材料清单.md", "我的工作区/06-论文正文/我的写作留痕.md"}
        check("包内不带学生填写版", not (filled & tracked), str(sorted(filled & tracked)))
        # 生成清单与豁免名单同源：setup_workspace 说要生成的，必须正好是上面那两条
        sw = (ROOT / "tools" / "setup_workspace.py").read_text(encoding="utf-8")
        gen = {"我的工作区/" + m for m in re.findall(r'^\s+\("([^"]+)",\s*"templates/', sw, re.M)}
        check("第22项生成清单与不进包的清单同源", gen == filled, f"GENERATED={sorted(gen)}")
        # 反向：学生本人的数据/成果/凭据不得入库（题录 txt、CSV、真实数据）
        # 白名单用模式而不是逐个文件名：`把…放这里.txt` 是各目录占位说明的统一命名，
        # 逐个列举会让"新加一个工作区目录"必须先改这条断言（v1.77 踩过）。
        preset = ("先读我.md",)
        leak = [t for t in tracked if t.startswith("我的工作区/")
                and not (re.match(r"^我的工作区/[^/]+/把.+放这里\.txt$", t)
                         or t.rsplit("/", 1)[-1] in preset)]
        check("学生数据不入库", not leak, str(sorted(leak)))
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
    check("coach文献量口径", "至少 90 篇候选池" in cr and "10–20 篇重点" in cr and "多词交叉核验" in cr)
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
    check("精读分层数量", "精读（10–20 篇，从约 90 篇候选池中筛）" in pr and "泛读（20-40篇）" in pr)
    check("进度卡12阶段", "11 答辩准备" in tx("templates/progress-template.md"))
    cm = ROOT / "workflows" / "communication-guide.md"
    check("沟通指南文件存在", cm.exists())
    if cm.exists():
        cg = cm.read_text(encoding="utf-8")
        check("沟通12场景", all(s in cg for s in ["场景1", "场景12", "带选择题", "12356", "关键决策日志"]))
        check("沟通原则与礼仪", "定期" in cg and "附件命名" in cg and "对事不对人" in cg)
    check("coach阶段10引用", "workflows/communication-guide.md" in cr)
    check("START导航沟通", "communication-guide.md" in st)
    rm = tx("README.md"); check("README沟通清单", "communication-guide.md" in rm)
    # 反向钉：README 不抄量表组数/模块数（曾把过期的"16种"当正确答案锁在断言里，等于给漂移续命）。
    check("README数字修正", "16种" not in rm and "24组" not in rm and "10种统计方法" not in rm)
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
    # ---- v1.59 量表库扩充：8 个新小节(17-24)+BSMAS，硬事实逐条锁定（均经联网核查）----
    check("DASS21事实", all(s in sl for s in [
        "DASS-21", "龚栩等, 2010", "21（抑郁/焦虑/压力各7题）", "求和后**×2**", "不作临床诊断"]))
    check("PSS10事实", all(s in sl for s in [
        "PSS-10", "Cohen & Williamson, 1988", "失控/无助感（6个负向题：1,2,3,6,9,10）",
        "4个正向题反向计分", "过去一个月"]))
    check("SCSQ事实", all(s in sl for s in [
        "SCSQ", "解亚宁, 1998", "积极应对1-12题", "消极应对13-20题", "0=不采取"]))
    check("ERQ事实且区别CERQ", all(s in sl for s in [
        "ERQ", "王力等, 2007", "认知重评6题：1,3,5,7,8,10", "表达抑制4题：2,4,6,9",
        "**7点计分**", "不可混用或互相替代引用"]))
    check("SCS谭树华19题", all(s in sl for s in [
        "谭树华、郭永玉, 2008", "节制娱乐(6)", "专注工作(4)", "谭树华**19题**中文版", "BSCS 为13题"]))
    check("CSES中文10题", all(s in sl for s in [
        "CSES", "杜建政、张翔、赵燕, 2012", "中文版10题（原版12题", "第2,3,5,7,8,10题为反向计分"]))
    check("SWLS事实", all(s in sl for s in [
        "SWLS", "Diener, Emmons, Larsen & Griffin, 1985", "总分5-35", "30-35非常满意"]))
    check("BPNS题数存疑标注", all(s in sl for s in [
        "BPNS", "刘俊升、林丽玲、吕媛等, 2013", "自主7+胜任6+关系8", "多被记为19题",
        "必须查刘俊升2013原文确认总题数"]))
    check("BSMAS六要素", all(s in sl for s in [
        "BSMAS", "Andreassen等, 2016", "显著性+心境改变", "耐受+戒断+冲突+复发", "总分6-30"]))
    check("量表库编号到39且十一大类", "### 36. 基本心理需要" in sl and "### 37. 睡眠质量（PSQI）" in sl
          and "## 九、自我评价、幸福感与基本需要类" in sl and "## 十、睡眠与心身健康类" in sl
          and "## 七、负性情绪综合筛查" in sl and "## 八、压力、应对与自我调节类" in sl
          and "## 十一、学习心理与教育情境类" in sl and "### 38. 学习投入（UWES-S）" in sl
          and "### 39. 学业倦怠（连榕量表 / MBI-SS）" in sl)
    # ---- v1.60 量表库再扩充：5 个高频量表(PANAS/IRI-C/GQ-6/GHQ-12/PSQI)，硬事实逐条锁定（均经联网核查）----
    check("PANAS事实", all(s in sl for s in [
        "PANAS", "Watson, Clark & Tellegen, 1988", "20（正性10+负性10）",
        "张卫东、刁静、Schick, 2004", "各 10-50"]))
    check("IRIC事实", all(s in sl for s in [
        "IRI-C", "Davis, 1980", "22（PT5＋FS5＋EC6＋PD6）",
        "28（4 维度各 7 题）", "张凤凤、董毅等, 2010"]))
    check("GQ6事实", all(s in sl for s in [
        "GQ-6", "McCullough, Emmons & Tsang, 2002", "第 3、6 题反向计分", "总分 6-42"]))
    check("GHQ12事实", all(s in sl for s in [
        "GHQ-12", "12（6 正向＋6 负向）", "GHQ 双峰法 0-0-1-1",
        "Likert 法 0-1-2-3", "总分 0-36", "不作临床诊断"]))
    check("PSQI事实", all(s in sl for s in [
        "PSQI", "Buysse 等, 1989", "刘贤臣、唐茂芹等, 1999",
        "19 个自评＋5 个他评（仅 18 个自评条目计分）", "总分 0-21"]))
