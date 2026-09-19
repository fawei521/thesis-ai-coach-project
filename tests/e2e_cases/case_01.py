# -*- coding: utf-8 -*-
"""首段·夹具与基准样例
full_e2e.py 顺序片段 1/14（原第 156–304 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
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
    # v1.60 样本量补 t 检验设计（t²=F 复用非中心F，黄金值对照 scipy.stats.nct）
    ss_ind = run(["tools/sample_size.py", "--design", "ttest-ind", "--effect", "0.5"])
    check("独立t样本量", ss_ind.returncode == 0 and "N=128" in ss_ind.stdout and "每组至少 64 人" in ss_ind.stdout)
    ss_pair = run(["tools/sample_size.py", "--design", "ttest-paired", "--effect", "0.5"])
    check("配对t样本量", ss_pair.returncode == 0 and "N=34" in ss_pair.stdout)
    ss_ind3 = run(["tools/sample_size.py", "--design", "ttest-ind"])
    check("独立t三档", ss_ind3.returncode == 0 and all(s in ss_ind3.stdout for s in ["788", "128", "52"]))
    ss_bad = run(["tools/sample_size.py", "--design", "ttest-paired", "--effect", "0"])
    check("t样本量坏参守卫", ss_bad.returncode == 1 and "d（配对为 dz）" in ss_bad.stdout
          and "Traceback" not in (ss_bad.stdout or "") + (ss_bad.stderr or ""))
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
    # ---- Mahalanobis 多元异常值筛查（纯标准库；D²/标记已用 numpy/scipy 黄金对照；只标记不删）----
    import random as _rnd
    mdir = new_tmp("mahalanobis")
    _rgen = _rnd.Random(20260918)
    def _ih(): return _rgen.random() + _rgen.random() + _rgen.random() - 1.5
    mrows = []
    for _ in range(80):
        _z1 = _ih(); _z2 = 0.6 * _z1 + 0.4 * _ih(); _z3 = 0.3 * _z1 + 0.7 * _ih()
        mrows.append([round(20 + 5 * _z1, 2), round(15 + 4 * _z2, 2), round(10 + 3 * _z3, 2)])
    mrows.append([45, 35, 28])  # 极端多元异常点（最后一行→数据行号82）
    with open(mdir / "mah.csv", "w", encoding="utf-8-sig", newline="") as _mf:
        _mw = csv.writer(_mf); _mw.writerow(["V1", "V2", "V3"]); _mw.writerows(mrows)
    rdef = run(["tools/auto_stats.py", str(mdir / "mah.csv")], 200)
    check("Mahalanobis默认关闭", "多元异常值筛查" not in (rdef.stdout or "")
          and not (mdir / "mah_多元异常值.csv").exists())
    rmh = run(["tools/auto_stats.py", str(mdir / "mah.csv"), "--mahalanobis"], 200)
    check("Mahalanobis检出极端点", rmh.returncode == 0 and "发现 1 个多元异常个案" in (rmh.stdout or "")
          and "数据行号 82" in (rmh.stdout or ""), (rmh.stderr or "")[-200:])
    with open(mdir / "mah_多元异常值.csv", encoding="utf-8-sig") as _mf:
        mout = list(csv.reader(_mf))
    mflag = [row for row in mout[1:] if row[-1] == "是"]
    check("Mahalanobis仅标记极端点",
          mout[0] == ["数据行号", "D2", "df", "p", "是否多元异常值"] and len(mflag) == 1 and mflag[0][0] == "82",
          str(mflag))
    check("Mahalanobis不删原数据", sum(1 for _ in open(mdir / "mah.csv", encoding="utf-8-sig")) - 1 == 81)
    rtwo = run(["tools/auto_stats.py", str(mdir / "mah.csv"), "--mahalanobis", "V1", "V2"], 200)
    check("Mahalanobis指定变量", rtwo.returncode == 0 and "变量 2 个" in (rtwo.stdout or ""))
    rbad = run(["tools/auto_stats.py", str(mdir / "mah.csv"), "--mahalanobis", "--mah-alpha", "1.5"], 200)
    check("Mahalanobis坏alpha守卫", "--mah-alpha" in (rbad.stdout or "") and "0 与 1" in (rbad.stdout or ""))
    check("Mahalanobis只标记不删口径",
          "不能为了让模型好看而删点" in (rmh.stdout or "") and "敏感性分析" in (rmh.stdout or ""))
    # ---- 效应量换算/复核 effect_size.py（纯标准库；关键数值已用 numpy/scipy 黄金对照）----
    esd = run(["tools/effect_size.py", "d", "--m1", "10", "--sd1", "2", "--n1", "30",
               "--m2", "9", "--sd2", "2", "--n2", "30"])
    check("效应量d均值换算", esd.returncode == 0 and "Cohen's d = 0.500" in esd.stdout
          and "Hedges' g = 0.494" in esd.stdout and ".2/.5/.8" in esd.stdout)
    esdt = run(["tools/effect_size.py", "d-t", "--t", "2.65", "--n1", "60", "--n2", "60"])
    check("效应量d由t换算", esdt.returncode == 0 and "Cohen's d = 0.484" in esdt.stdout)
    esr = run(["tools/effect_size.py", "r", "--r", "0.34", "--n", "120"])
    check("效应量r的Fisher区间", esr.returncode == 0 and "[0.171, 0.489]" in esr.stdout
          and "d ≈ 0.723" in esr.stdout)
    ese = run(["tools/effect_size.py", "eta", "--F", "5.20", "--df1", "2", "--df2", "117"])
    check("效应量偏eta2", ese.returncode == 0 and "= 0.082" in ese.stdout and ".01/.06/.14" in ese.stdout)
    esv = run(["tools/effect_size.py", "v", "--chi2", "6.10", "--n", "200", "--rows", "2", "--cols", "2"])
    check("效应量CramersV", esv.returncode == 0 and "Cramér's V = √(χ²/(N·df_min)) = 0.175" in esv.stdout
          and "φ(phi) = √(χ²/N) = 0.175" in esv.stdout)
    esbad = run(["tools/effect_size.py", "r", "--r", "0.9", "--n", "2"])
    check("效应量坏参守卫", esbad.returncode == 1 and "Traceback" not in (esbad.stdout or "")
          and "n>3" in (esbad.stdout or ""))
    # ---- 聚合/区分效度 validity_cr_ave.py（纯标准库；CR/AVE 公式已用 numpy 黄金对照）----
    vca_src = tx("tools/validity_cr_ave.py")
    check("效度工具纯标准库", "import csv" in vca_src and "matplotlib" not in vca_src and "pandas" not in vca_src)
    check("效度工具公式与红线", "(Σλ" in vca_src and "Fornell" in vca_src and "真实 CFA" in vca_src)
    vca_ok = run(["tools/validity_cr_ave.py",
                  "--factor", "学习投入=0.72,0.68,0.74,0.70",
                  "--factor", "学业倦怠=0.60,0.65,0.58,0.62",
                  "--corr", "学习投入,学业倦怠,0.45"])
    check("效度CR_AVE黄金值", vca_ok.returncode == 0 and all(s in vca_ok.stdout for s in
          ["0.803", "0.505", "0.710", "0.706", "0.376", "0.613"]), (vca_ok.stderr or "")[-200:])
    check("效度区分成立", "区分效度成立" in vca_ok.stdout and "Fornell-Larcker" in vca_ok.stdout)
    vca_bad_disc = run(["tools/validity_cr_ave.py",
                        "--factor", "学习投入=0.72,0.68,0.74,0.70",
                        "--factor", "学业倦怠=0.60,0.65,0.58,0.62",
                        "--corr", "学习投入,学业倦怠,0.65"])
    check("效度区分存疑能识别", vca_bad_disc.returncode == 0 and "区分效度存疑" in vca_bad_disc.stdout
          and "0.613" in vca_bad_disc.stdout and "0.650" in vca_bad_disc.stdout)
    vca_bad_load = run(["tools/validity_cr_ave.py", "--factor", "X=1.02,0.7"])
    check("效度坏载荷守卫", vca_bad_load.returncode == 1 and "标准化载荷" in vca_bad_load.stdout
          and "Traceback" not in (vca_bad_load.stdout or "") + (vca_bad_load.stderr or ""))
    vca_bad_fac = run(["tools/validity_cr_ave.py", "--factor", "X=0.7,0.6", "--corr", "X,Y,0.3"])
    check("效度未知因子守卫", vca_bad_fac.returncode == 1 and "未提供载荷" in vca_bad_fac.stdout
          and "Traceback" not in (vca_bad_fac.stdout or "") + (vca_bad_fac.stderr or ""))
    vca_neg = run(["tools/validity_cr_ave.py", "--factor", "X=0.72,-0.68,0.74"])
    check("效度负载荷警示", vca_neg.returncode == 0 and "负载荷" in vca_neg.stdout
          and "反向题" in vca_neg.stdout)
    vca_nofile = run(["tools/validity_cr_ave.py", "--loadings-csv", " definitely_missing_xyz.csv"])
    check("效度缺文件守卫", vca_nofile.returncode == 1 and vca_nofile.stdout.lstrip().startswith("✗")
          and "Traceback" not in (vca_nofile.stdout or "") + (vca_nofile.stderr or ""))
    vca_dir = new_tmp("validity")
    vca_csv = run(["tools/validity_cr_ave.py",
                   "--factor", "学习投入=0.72,0.68,0.74,0.70",
                   "--factor", "学业倦怠=0.60,0.65,0.58,0.62",
                   "--corr", "学习投入,学业倦怠,0.45",
                   "--csv-out", str(vca_dir)])
    vca_out = vca_dir / "_聚合区分效度.csv" if (vca_dir / "_聚合区分效度.csv").exists() else None
    check("效度CSV导出", vca_csv.returncode == 0 and vca_out is not None and vca_out.exists())
    if vca_out:
        vca_rows = list(csv.reader(open(vca_out, encoding="utf-8-sig")))
        check("效度CSV内容", vca_rows[0][:5] == ["因子", "题项数", "CR组合信度", "AVE平均方差抽取", "√AVE"]
              and vca_rows[1][0] == "学习投入" and abs(float(vca_rows[1][2]) - 0.803) < 5e-3
              and "成立" in vca_rows[1][7], str(vca_rows[:2]))

