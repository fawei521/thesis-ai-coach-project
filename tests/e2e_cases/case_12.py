# -*- coding: utf-8 -*-
"""v1.69 多重比较校正（Bonferroni/Holm/BH/BY） ==========
full_e2e.py 顺序片段 12/14（原第 1764–1957 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ========== v1.69 多重比较校正（Bonferroni/Holm/BH/BY） ==========
    mc_tool = str(ROOT / "tools" / "mult_compare.py")
    mc_src = tx("tools/mult_compare.py")
    check("多重校正工具存在", Path(mc_tool).exists())
    check("多重校正纯标准库", "pandas" not in mc_src and "numpy" not in mc_src
          and "import csv" in mc_src)
    check("多重校正编码守卫", "输出编码守卫" in mc_src and "reconfigure" in mc_src)
    check("菜单第20项多重校正", "【20/" in menu and "mult_compare.py" in menu
          and "Bonferroni" in menu and "Holm" in menu)
    check("统计指南接线多重校正", "mult_compare.py" in tx("psychology/stats-guide.md"))
    check("分析流程接线多重校正", "mult_compare.py" in tx("workflows/data-analysis-auto.md"))
    check("START登记多重校正", "mult_compare.py" in st)

    v69 = new_tmp("v169mc")
    out69 = v69 / "mc.csv"
    rpt69 = v69 / "mc.txt"
    common_out = ["--csv-out", str(out69), "--report", str(rpt69)]

    def both69(rr):
        return (rr.stdout or "") + (rr.stderr or "")

    # R p.adjust 经典向量：bonf=.05/.10/.15/.20/.25，holm 尾部累积 .09，BH 全 .05
    r = run([mc_tool, "--ps", ".01,.02,.03,.04,.05", "--method", "bonferroni"] + common_out)
    o = both69(r)
    check("v169 bonf经典值", r.returncode == 0 and ".050" in o and ".250" in o and ".150" in o)
    r = run([mc_tool, "--ps", ".01,.02,.03,.04,.05", "--method", "holm"] + common_out)
    o = both69(r)
    check("v169 holm默认", r.returncode == 0 and "Holm" in o and "显著 0/5" in o)
    r = run([mc_tool, "--ps", ".01,.02,.03,.04,.05", "--method", "bh"] + common_out)
    check("v169 bh经典", r.returncode == 0 and "显著 0/5" in (r.stdout or "")
          and ".050" in (r.stdout or ""))
    r = run([mc_tool, "--ps", ".001,.008,.039,.041,.042,.06,.1,.25,.37,.49,.82",
             "--method", "all"] + common_out)
    o = both69(r)
    check("v169四法全列", r.returncode == 0 and all(s in o for s in
          ["Bonferroni", "Holm", "BH", "BY"]))
    r = run([mc_tool, "--ps", ".01,.04", "--names", "性别差异,年级差异"] + common_out)
    check("v169名称列", r.returncode == 0 and "性别差异" in (r.stdout or "")
          and "年级差异" in (r.stdout or ""))

    # CSV 模式
    def wcsv69(name, text, enc="utf-8-sig"):
        pp = v69 / name
        pp.write_text(text, encoding=enc)
        return pp
    res69 = wcsv69("res.csv", "对比,p值\n男-女,.002\n低-高,.033\n中-高,.12\n")
    r = run([mc_tool, str(res69), "--pcol", "p值", "--namecol", "对比"] + common_out)
    check("v169 csv模式", r.returncode == 0 and "男-女" in (r.stdout or "")
          and "中-高" in (r.stdout or ""))
    gbk69 = wcsv69("gbk.csv", "对比,p值\n男女,.001\n年级,.06\n", enc="gbk")
    r = run([mc_tool, str(gbk69), "--pcol", "p值", "--namecol", "对比"] + common_out)
    check("v169 gbk", r.returncode == 0 and "男女" in (r.stdout or ""))
    badrow69 = wcsv69("badrow.csv", "name,p\na,.01\nb,NA\n")
    r = run([mc_tool, str(badrow69), "--pcol", "p"] + common_out)
    check("v169坏p行", r.returncode != 0 and "不是数字" in both69(r))
    empty69 = wcsv69("empty.csv", "")
    r = run([mc_tool, str(empty69), "--pcol", "p"] + common_out)
    check("v169空csv", r.returncode != 0)

    # 坏输入
    r = run([mc_tool, "--ps", ".01,abc"] + common_out)
    check("v169非数字p", r.returncode != 0 and "数字" in both69(r))
    r = run([mc_tool, "--ps", ".01,1.2"] + common_out)
    check("v169越界p", r.returncode != 0 and "0～1" in both69(r))
    r = run([mc_tool, "--ps", ".01"] + common_out)
    check("v169单个p", r.returncode != 0 and "至少需要 2 个" in both69(r))
    r = run([mc_tool])
    check("v169无来源", r.returncode != 0 and "--ps" in both69(r))
    r = run([mc_tool, "--ps", ".01,.02", "--names", "a"] + common_out)
    check("v169名称不符", r.returncode != 0 and "不一致" in both69(r))
    r = run([mc_tool, str(res69), "--pcol", "不存在"] + common_out)
    check("v169 csv缺列", r.returncode != 0 and "不在 CSV" in both69(r))
    r = run([mc_tool, str(v69 / "nope.csv"), "--pcol", "p"] + common_out)
    check("v169 csv无文件", r.returncode != 0 and "找不到文件" in both69(r))
    r = run([mc_tool, str(res69)] + common_out)
    check("v169 csv无pcol", r.returncode != 0 and "--pcol" in both69(r))
    r = run([mc_tool, "--ps", ".01,.02", "--alpha", "x"] + common_out)
    check("v169坏alpha", r.returncode != 0)
    r = run([mc_tool, "--ps", ".01,.02", "--alpha", "2"] + common_out)
    check("v169 alpha越界", r.returncode != 0 and "alpha" in both69(r))

    # 产物与红线
    csv69 = out69.read_text(encoding="utf-8-sig")
    rpt69_txt = rpt69.read_text(encoding="utf-8")
    check("v169产物齐全", "BH_FDR校正q" in csv69 and "Holm校正p" in csv69
          and "多重比较校正" in rpt69_txt)
    check("v169报告红线", "分析前确定" in rpt69_txt and "校正后不显著也是结果" in rpt69_txt)
    check("v169源码红线", "不能三种都跑" in mc_src and "一个家族" in mc_src
          and "校正后不显著也是结果" in mc_src)


    # ========== v1.70 Wilcoxon rank-biserial r 效应量 ==========
    pc_src = tx("tools/paired_compare.py")
    check("r_rb公式在源码", "r_rb" in pc_src and "w_plus - w_minus" in pc_src
          and "rank-biserial" in pc_src)
    v70 = new_tmp("v170rrb")
    small70 = v70 / "small.csv"
    small70.write_text("pre,post\n" + "".join(f"0,{d}\n" for d in
                       [1.1, -2.3, 0.7, 3.2, -0.4]), encoding="utf-8-sig")
    import random as _rnd70
    _rnd70.seed(17002)
    wide70 = v70 / "wide.csv"
    with open(str(wide70), "w", encoding="utf-8-sig", newline="") as f70:
        w70 = csv.writer(f70)
        w70.writerow(["id", "pre", "post"])
        for i in range(1, 61):
            pre = _rnd70.gauss(3, 1)
            w70.writerow([i, round(pre, 3), round(pre + 0.6 + _rnd70.gauss(0, .5), 3)])
    # Likert 差值、n<30、有结：小样本结警告（v1.69 顺带维护特性）回归
    lik70 = v70 / "lik.csv"
    lik70.write_text("pre,post\n" + "".join(f"3,{3 + d}\n" for d in
                     [1, -1, 0, 2, -2, 1, 1, -1, 2, 0, 1, -1]), encoding="utf-8-sig")

    r = run([pc_tool, str(small70), "--pairs", "pre:post",
             "--csv-out", str(v70 / "s.csv"), "--report", str(v70 / "s.txt")])
    o = r.stdout or ""
    check("v170手工r_rb", r.returncode == 0 and "r=0.333" in o and "精确双侧 p=.625" in o)
    s_csv = open(str(v70 / "s.csv"), encoding="utf-8-sig").read()
    s_rpt = open(str(v70 / "s.txt"), encoding="utf-8").read()
    check("v170 CSV表头含r", "Wilcoxon_r_rb" in s_csv)
    # 报告的 Wilcoxon 句只在差值非正态（以非参数为准）时出现：偏态差值夹具
    import random as _r70b
    _r70b.seed(17003)
    skew70 = v70 / "skew.csv"
    with open(str(skew70), "w", encoding="utf-8-sig", newline="") as f70b:
        wb = csv.writer(f70b)
        wb.writerow(["pre", "post"])
        for _ in range(60):
            wb.writerow([0, round(_r70b.expovariate(1 / 3), 3)])
    r = run([pc_tool, str(skew70), "--pairs", "pre:post",
             "--csv-out", str(v70 / "k.csv"), "--report", str(v70 / "k.txt")])
    k_rpt = open(str(v70 / "k.txt"), encoding="utf-8").read()
    k_o = r.stdout or ""
    check("v170偏态报告含r", r.returncode == 0 and "建议以 Wilcoxon 为准" in k_o
          and "rank-biserial r=" in k_rpt and "Wilcoxon_r_rb" in
          open(str(v70 / "k.csv"), encoding="utf-8-sig").read())

    r = run([pc_tool, str(wide70), "--pairs", "pre:post", "--id", "id",
             "--csv-out", str(v70 / "w.csv"), "--report", str(v70 / "w.txt")])
    o = r.stdout or ""
    check("v170大样本r_rb", r.returncode == 0 and "r=0.820" in o and "大效应" in o)
    # r 必在 [-1,1]
    m70 = float(re.search(r"r=(-?[0-9.]+)", o).group(1))
    check("v170 r有界", -1.0 <= m70 <= 1.0)

    r = run([pc_tool, str(lik70), "--pairs", "pre:post",
             "--csv-out", str(v70 / "l.csv"), "--report", str(v70 / "l.txt")])
    o = r.stdout or ""
    check("v170小样本结警告回归", r.returncode == 0 and "小样本且有" in o and "正态近似" in o
          and "rank-biserial r=" in o)


    # ========== v1.71 多重插补/FIML 教学指引 ==========
    guide71 = ROOT / "psychology" / "missing-imputation-guide.md"
    check("MI指引文件存在", guide71.exists())
    g71 = tx("psychology/missing-imputation-guide.md")
    check("MI指引含决策与红线", "MCAR" in g71 and "成列删除" in g71
          and "禁止均值" in g71 and "LOCF" in g71)
    check("MI指引含三软件步骤", ("预测均值匹配" in g71 or "PMM" in g71)
          and "mice" in g71 and "估计均值与截距" in g71 and "FIML" in g71)
    check("MI指引含Rubin与敏感性", "Rubin" in g71 and "T = " in g71
          and "敏感性" in g71 and "MNAR" in g71)
    check("MI指引含论文模板", "方法章" in g71 and "局限" in g71)
    mr_src71 = tx("tools/missing_report.py")
    check("缺失工具指向MI指引", "missing-imputation-guide.md" in mr_src71)
    check("统计指南指向MI指引", "missing-imputation-guide.md" in tx("psychology/stats-guide.md"))
    check("流程指向MI指引", "missing-imputation-guide.md" in tx("workflows/data-analysis-auto.md"))
    check("README登记MI指引", "missing-imputation-guide.md" in open(
        str(ROOT / "README.md"), encoding="utf-8").read())
    check("START登记MI指引", "missing-imputation-guide.md" in st)
    # 功能：MAR 场景控制台与报告段落都给出指南指引
    d71 = new_tmp("v171mi")
    mar71 = d71 / "mar.csv"
    random.seed(71)
    with open(str(mar71), "w", encoding="utf-8-sig", newline="") as f71:
        wm = csv.writer(f71)
        wm.writerow(["id", "X", "Y", "Z"])
        for i in range(1, 301):
            x = random.gauss(0, 1)
            y = 0.8 * x + random.gauss(0, 1)
            z = random.gauss(0, 1)
            wm.writerow([i, round(x, 3),
                         "" if (x < -0.3 and random.random() < 0.3) else round(y, 3),
                         round(z, 3)])
    r = run([str(ROOT / "tools" / "missing_report.py"), str(mar71),
             "--csv-out", str(d71 / "out")])
    o = r.stdout or ""
    check("v171 MAR拒绝且指引进控制台", r.returncode == 0 and "拒绝 MCAR" in o
          and "missing-imputation-guide.md" in o)
    rpt71 = list((d71 / "out").glob("*报告.txt"))
    check("v171 报告段落含指引", rpt71 and "missing-imputation-guide.md"
          in open(str(rpt71[0]), encoding="utf-8").read())


