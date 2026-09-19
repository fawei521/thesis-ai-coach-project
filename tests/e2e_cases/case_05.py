# -*- coding: utf-8 -*-
"""v1.54 学生自己做网页：引导手册 + 预览器 + 三个范例 + 工作区 ----
full_e2e.py 顺序片段 5/14（原第 798–994 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ---- v1.54 学生自己做网页：引导手册 + 预览器 + 三个范例 + 工作区 ----
    wg = tx("workflows/webpage-guide.md")
    check("网页指南含硬规矩", all(s in wg for s in ["单文件", "自包含", "不引用外部资源", "不放个人隐私", "网页不是论文成果"]))
    check("网页指南含五类网页", all(s in wg for s in ["文献笔记网页", "数据分析结果看板", "研究流程图", "量表与问卷速查", "论文进度看板"]))
    check("网页指南含三闸", all(s in wg for s in ["闸 1 动机闸", "闸 2 质量闸", "闸 3 留痕闸"]))
    check("网页指南警示勿抄范例", "不要抄" in wg)
    ex = ROOT / "templates" / "网页范例"
    ex_pages = [ex / "01-文献笔记网页" / "index.html",
                ex / "02-术语词典网页" / "index.html",
                ex / "03-研究流程图" / "research-flow.html",
                ex / "04-统计方法选择器" / "index.html"]
    check("四个网页范例齐备", all(p.exists() for p in ex_pages),
          str([p.name for p in ex_pages if not p.exists()]))
    check("范例带勿直接使用标注",
          all("范例，请勿直接使用" in p.read_text(encoding="utf-8", errors="replace") for p in ex_pages))
    check("范例README提示只学做法",
          "只用来学" in tx("templates/网页范例/README.md") or
          ("可以学的是" in tx("templates/网页范例/README.md")
           and "只能参考代码结构与交互设计" in tx("templates/网页范例/README.md")))
    sel = tx("templates/网页范例/04-统计方法选择器/index.html")
    check("方法选择器范例标注", "范例，请勿直接使用" in sel)
    check("方法选择器自包含无外链", not any(s in sel for s in
          ['src="http', 'href="http', "<link", "@import", "cdn", "<script src"]))
    check("方法选择器决策覆盖", all(s in sel for s in
          ["Welch t", "Mann-Whitney", "Kruskal-Wallis", "Games-Howell", "Cramér",
           "模型6", "Mahalanobis", "Spearman", "偏相关", "Fisher", "不显著也是结果"]))
    pw = tx("tools/webpage_preview.py")
    check("预览器只读", "SimpleHTTPRequestHandler" in pw and "do_POST" not in pw and "do_PUT" not in pw)
    check("预览器默认只绑本机", "127.0.0.1" in pw and "--lan" in pw)
    check("预览器防路径穿越", "normpath" in pw and "relative_to" in pw and "反斜杠" in pw)
    check("预览器声明charset", "charset=utf-8" in pw)
    pl = run(["tools/webpage_preview.py", "templates/网页范例", "--list"])
    check("预览器--list可运行", pl.returncode == 0 and "index.html" in (pl.stdout or ""), (pl.stderr or "")[-200:])
    wdir = ROOT / "我的工作区" / "04-网页"
    check("工作区04-网页就位", wdir.is_dir() and (wdir / "把网页放这里.txt").exists())
    check("菜单第9项", "【9/" in menu and "webpage_preview.py" in menu)
    check("网页能力已登记到入口",
          "webpage-guide.md" in st and "webpage_preview.py" in st and "webpage-guide.md" in cr)
    check("README登记网页能力", "webpage-guide.md" in rm and "webpage_preview.py" in rm)
    check("QUICKSTART登记第9项", "预览我做的网页" in tx("QUICKSTART.md"))
    check("工作区说明含04-网页", "04-网页" in tx("我的工作区/先读我.md"))

    # ---- v1.59 数据去标识化工具（隐私闸：假名化/删除直接标识符 + 准标识符 k-匿名体检）----
    an_src = tx("tools/anonymize_data.py")
    check("脱敏工具纯标准库", "import csv" in an_src and "matplotlib" not in an_src and "pandas" not in an_src)
    check("脱敏工具有安全开关", all(s in an_src for s in ["--dry-run", "--no-key", "--columns", "--k"]))
    check("脱敏工具另存不改原文件", "_去标识化.csv" in an_src and "同名同路径" in an_src)
    check("菜单第11项去标识化", "【11/" in menu and "anonymize_data.py" in menu and "去标识化" in menu)
    check("菜单第12项效应量", "【12/" in menu and "effect_size.py" in menu and "效应量" in menu)
    check("菜单第13项效度", "【13/" in menu and "validity_cr_ave.py" in menu and "区分效度" in menu)
    check("菜单13含HTMT", "HTMT" in menu)
    check("菜单第14项项目分析", "【14/" in menu and "item_analysis.py" in menu and "决断值" in menu)
    check("菜单第15项内容效度", "【15/" in menu and "content_cvi.py" in menu and "CVI" in menu)
    check("START登记去标识化", "anonymize_data.py" in st and "去标识化" in st)
    check("QUICKSTART登记第11项", "去标识化" in tx("QUICKSTART.md"))
    check("AI素养接线去标识化工具", "anonymize_data.py" in tx("core/ai-literacy.md"))
    check("数据工作流接线去标识化", "anonymize_data.py" in tx("workflows/data-analysis-auto.md"))

    pii_fixture = ROOT / "tests/test-data/sample_pii.csv"
    check("脱敏夹具就位", pii_fixture.exists())
    an_dir = new_tmp("anonymize")
    an_dry = run(["tools/anonymize_data.py", str(pii_fixture), "--dry-run", "-o", str(an_dir / "dry.csv")])
    check("脱敏dry-run退出0", an_dry.returncode == 0, (an_dry.stderr or "")[-200:])
    check("脱敏dry-run零写入", not (an_dir / "dry.csv").exists() and "体检模式" in (an_dry.stdout or "")
          and "k-匿名" in (an_dry.stdout or ""))
    an_r = run(["tools/anonymize_data.py", str(pii_fixture), "-o", str(an_dir / "out.csv"),
                "--report", str(an_dir / "r.txt"), "--key", str(an_dir / "key.csv")])
    check("脱敏正式运行退出0", an_r.returncode == 0 and (an_dir / "out.csv").exists(), (an_r.stderr or "")[-300:])
    with open(an_dir / "out.csv", encoding="utf-8-sig") as an_f:
        an_out_rows = list(csv.reader(an_f))
    an_out_header, an_out_body = an_out_rows[0], an_out_rows[1:]
    an_out_text = "\n".join([",".join(an_out_header)] + [",".join(x) for x in an_out_body])
    check("脱敏行数守恒", len(an_out_body) == 12, "rows=%d" % len(an_out_body))
    for an_removed in ["姓名", "学号", "手机号", "邮箱", "身份证号", "微信号", "QQ", "IP地址", "C1"]:
        check("脱敏删除列_" + an_removed, an_removed not in an_out_header, "header=%s" % an_out_header)
    check("脱敏保留编号与分析列", all(c in an_out_header for c in ["编号", "序号", "性别", "年级", "专业", "生源地", "Q1"]))
    for an_leak in ["张三", "李四", "13800000001", "13900000001", "zhangsan", "110101200001011234",
                    "zhangsan_wx", "192.168.1.10", "20210101"]:
        check("脱敏无泄漏_" + an_leak, an_leak not in an_out_text, "found %s" % an_leak)
    check("脱敏编号形如P码", all(row[an_out_header.index("编号")].startswith("P") for row in an_out_body if row))
    with open(an_dir / "key.csv", encoding="utf-8-sig") as an_kf:
        an_key_text = "\n".join([",".join(x) for x in list(csv.reader(an_kf))])
    check("假名对照表可还原", "P001" in an_key_text and "张三" in an_key_text and "原姓名" in an_key_text)
    an_nk = run(["tools/anonymize_data.py", str(pii_fixture), "-o", str(an_dir / "nk.csv"),
                 "--report", str(an_dir / "nk_r.txt"), "--no-key"])
    check("no-key退出0且无对照表", an_nk.returncode == 0 and (an_dir / "nk.csv").exists()
          and not (an_dir / "sample_pii_假名对照表.csv").exists() and "不可复原" in (an_nk.stdout or ""))
    an_refuse = run(["tools/anonymize_data.py", str(pii_fixture), "-o", str(pii_fixture)])
    check("脱敏拒绝覆盖原文件", an_refuse.returncode != 0 and "同名同路径" in (an_refuse.stdout or ""))
    (an_dir / "gbk.csv").write_bytes("姓名,手机号,性别,Q1\n张三,13812345678,男,4\n李四,13987654321,女,5\n".encode("gbk"))
    an_gbk_run = run(["tools/anonymize_data.py", str(an_dir / "gbk.csv"), "-o", str(an_dir / "gbk_out.csv"),
                      "--report", str(an_dir / "gbk_r.txt"), "--key", str(an_dir / "gbk_key.csv")])
    an_gbk_text = (an_dir / "gbk_out.csv").read_text(encoding="utf-8-sig") if (an_dir / "gbk_out.csv").exists() else ""
    check("脱敏兼容GBK", an_gbk_run.returncode == 0 and "编号" in an_gbk_text and "手机号" not in an_gbk_text
          and "13812345678" not in an_gbk_text, (an_gbk_run.stderr or "")[-200:])
    (an_dir / "nopii.csv").write_text("性别,年级,Q1\n男,大四,4\n女,大三,5\n男,大四,3\n", encoding="utf-8")
    an_nopii_run = run(["tools/anonymize_data.py", str(an_dir / "nopii.csv"), "-o", str(an_dir / "nopii_out.csv"),
                        "--report", str(an_dir / "nopii_r.txt")])
    check("脱敏无标识符友好退出", an_nopii_run.returncode == 0 and not (an_dir / "nopii_out.csv").exists()
          and "未发现" in (an_nopii_run.stdout or ""))
    an_mask_run = run(["tools/anonymize_data.py", str(pii_fixture), "-o", str(an_dir / "mask.csv"),
                       "--report", str(an_dir / "mask_r.txt"), "--no-key",
                       "--columns", "手机号:mask;姓名:drop;学号:drop"])
    an_mask_text = (an_dir / "mask.csv").read_text(encoding="utf-8-sig") if (an_dir / "mask.csv").exists() else ""
    check("脱敏mask打码", an_mask_run.returncode == 0 and "手机号" in an_mask_text and "138****0001" in an_mask_text
          and "13800000001" not in an_mask_text, (an_mask_run.stderr or "")[-200:])
    check("k匿名识别稀有组合", "考古学" in (an_r.stdout or "") and "最小等价类 k = 1" in (an_r.stdout or ""))
    an_raw = pii_fixture.read_text(encoding="utf-8")
    check("脱敏原文件不变", "张三" in an_raw and "13800000001" in an_raw)

    # ---- v1.55 豆包 Skill 轻量版（doubao-skill/ 独立分发子包，自带 validate.py 门禁）----
    SK = ROOT / "doubao-skill"
    check("Skill目录就位", SK.is_dir() and (SK / "SKILL.md").exists())
    skr = run(["doubao-skill/validate.py"], 120)
    check("Skill自检退出0", skr.returncode == 0 and "全部通过" in (skr.stdout or ""),
          ((skr.stdout or "")[-400:]) + ((skr.stderr or "")[-200:]))
    skm = (SK / "SKILL.md").read_text(encoding="utf-8")
    check("Skill默认自然语气", "自然（默认" in skm and "不套任何人设" in skm)
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
    # 临时目录用**系统临时区**，不放 tests/test-data：实测 Windows 下在仓库内 mkdtemp + copytree
    # 会被杀软/索引器短暂锁住（WinError 5），既可能打断回归、又会留下删不掉的目录污染仓库。
    neg = new_tmp("skill_neg")
    try:
        # copytree 到刚建的目录仍可能被瞬时占用，保留小退避重试（此前无重试，直接抛 PermissionError 打断全量回归）
        copied = False
        for attempt in range(5):
            try:
                shutil.copytree(SK, neg / "doubao-skill")
                copied = True
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(0.4 * (attempt + 1))
        check("Skill阴性副本就位", copied)
        vf = neg / "doubao-skill" / "SKILL.md"
        vf.write_text(vf.read_text(encoding="utf-8") + "\n见 `ghost-ref-xyz.md`，TODO 待补充\n",
                      encoding="utf-8")
        nr = run([str(neg / "doubao-skill" / "validate.py")], 60)
        check("Skill自检能抓变异", nr.returncode != 0 and "ghost-ref-xyz.md" in (nr.stdout or ""),
              "rc=%s" % nr.returncode)
    finally:
        if not rmtree_retry(neg):
            print("WARN 阴性测试临时目录未能删除（请手动清理）：" + str(neg))
    check("一致性检查跳过Skill子包", "doubao-skill" in tx("tests/consistency_check.py"))
    # ---- v1.88 跨包守卫：两侧硬口径必须同源（合并单文件在位由 validate.py 缺件判红兜底）----
    ss = run(["tests/skill_sync_check.py"], 120)
    check("v188跨包口径同源核对0", ss.returncode == 0, (ss.stdout or "")[-400:])
    s2 = run(["tests/skill_sync_check.py", "--selftest"], 120)
    check("v188跨包守卫抓得到变异", s2.returncode == 0 and "全部被抓" in (s2.stdout or ""),
          (s2.stdout or "")[-300:])
    if (ROOT / ".git").exists():               # 发布副本没有 .git，自然跳过（同 case_17 口径）
        # 必须带 -c core.quotePath=false：git 默认把非 ASCII 路径转义成八进制（\346\211\213…），不加会误报"没入库"（v1.88 踩到）
        gl = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "doubao-skill"],
                            capture_output=True, text=True,
                            encoding="utf-8", timeout=60, cwd=str(ROOT)).stdout.replace("\\", "/")
        check("v188手机合并单文件已入库随包", "doubao-skill/thesis-ai-coach-手机版.md" in gl, gl[:100])

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
    check("v156鼓励禁夸天赋且去机械计数", "禁止夸天赋" in eg and "每轮至多一次肯定" not in eg and "密度自然" in eg)
    check("v158鼓励四语气措辞", all(s in eg for s in ("自然（默认）", "简洁直接（可选）", "温和耐心（可选）", "活泼热情（可选）"))
          and "专业导师（默认）" not in eg and "小奶狗（可选）" not in eg)
    check("v156行为自测用例与声明", "T1 " in bt and "T32" in bt and "测试计划" in bt and "不是" in bt)
    check("v156coach人格鼓励正交", "人格只管" in cr and "鼓励档" in cr and "core/encouragement-guide.md" in cr)
    check("v156coach旧鼓励表述移除", "不给无意义鼓励" not in cr)
    check("v156coach卡壳临时降档", "临时降一档" in cr)
    check("v156coach阶段0鼓励档", "鼓励档（默认" in cr)
    check("v156coach引用反馈协议", "core/coaching-protocol.md" in cr and "反馈三段式" in cr)
    check("v156START必读六份", "先读这六份" in st and "core/companionship.md" in st and "core/coaching-protocol.md" in st and "core/encouragement-guide.md" in st)
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

