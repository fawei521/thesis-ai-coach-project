# -*- coding: utf-8 -*-
"""v1.72 单样本模式（--onesample/--constant） ==========
full_e2e.py 顺序片段 13/14（原第 1958–2100 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ========== v1.72 单样本模式（--onesample/--constant） ==========
    pc_src72 = tx("tools/paired_compare.py")
    check("单样本开关在源码", "--onesample" in pc_src72 and "--constant" in pc_src72
          and '"onesample"' in pc_src72)
    d72 = new_tmp("v172one")
    lik72 = d72 / "lik.csv"
    random.seed(17202)
    with open(str(lik72), "w", encoding="utf-8-sig", newline="") as f72:
        w72 = csv.writer(f72)
        w72.writerow(["id", "组别", "X"])
        for i in range(1, 81):
            g = "实验组" if i <= 40 else "对照组"
            w72.writerow([i, g, max(1, min(5, round(random.gauss(
                3.6 if g == "实验组" else 3.0, .9))))])
    # 手工确定性例：x=3,4,5 vs C=3 → t(2)=√3≈1.732
    hand72 = d72 / "hand.csv"
    hand72.write_text("X\n3\n4\n5\n", encoding="utf-8-sig")

    r = run([pc_tool, str(lik72), "--onesample", "X", "--constant", "3",
             "--csv-out", str(d72 / "o.csv"), "--report", str(d72 / "o.txt")])
    o = r.stdout or ""
    check("v172单样本跑通", r.returncode == 0 and "单样本检验" in o and "单样本 t(79)=3.064" in o
          and "检验常数=3.000" in o and "配对设计差异检验" not in o)
    rpt72 = open(str(d72 / "o.txt"), encoding="utf-8").read()
    csv72 = open(str(d72 / "o.csv"), encoding="utf-8-sig").read()
    check("v172报告口径", "单样本 t 检验显示" in rpt72 and "单样本 t 的前提" in rpt72)
    check("v172 CSV备注", "单样本(vs 3)" in csv72 and "3.0636" in csv72 and "0.3425" in csv72)

    r = run([pc_tool, str(lik72), "--onesample", "X", "--constant", "3",
             "--group", "组别", "--level", "实验组",
             "--csv-out", str(d72 / "og.csv"), "--report", str(d72 / "og.txt")])
    o = r.stdout or ""
    check("v172单样本分组", r.returncode == 0 and "有效 n=40" in o and "单样本 t(39)=5.176" in o)

    r = run([pc_tool, str(hand72), "--onesample", "X", "--constant", "3",
             "--csv-out", str(d72 / "h.csv"), "--report", str(d72 / "h.txt")])
    o = r.stdout or ""
    check("v172手工t", r.returncode == 0 and "单样本 t(2)=1.732" in o)

    # 坏组合
    r = run([pc_tool, str(lik72), "--onesample", "X",
             "--csv-out", str(d72 / "b1.csv")])
    check("v172缺常数", r.returncode != 0 and "--constant" in ((r.stdout or "") + (r.stderr or "")))
    r = run([pc_tool, str(lik72), "--constant", "3",
             "--csv-out", str(d72 / "b2.csv")])
    check("v172缺onesample", r.returncode != 0 and "--onesample" in ((r.stdout or "") + (r.stderr or "")))
    r = run([pc_tool, str(lik72), "--onesample", "NOPE", "--constant", "3",
             "--csv-out", str(d72 / "b3.csv")])
    check("v172缺列", r.returncode != 0 and "不在数据" in ((r.stdout or "") + (r.stderr or "")))
    r = run([pc_tool, str(lik72), "--onesample", "X", "--constant", "3", "--scales", "s.txt",
             "--csv-out", str(d72 / "b4.csv")])
    check("v172混scales", r.returncode != 0 and "单文件" in ((r.stdout or "") + (r.stderr or "")))
    # 配对模式回归：标题仍是配对口径
    r = run([pc_tool, str(lik72), "--pairs", "X:X",
             "--csv-out", str(d72 / "p.csv"), "--report", str(d72 / "p.txt")])
    check("v172配对回归", r.returncode == 0 and "配对设计差异检验" in (r.stdout or ""))


    # ========== v1.73 Durbin-Watson＋残差正态（SW 下沉 mathx） ==========
    mathx73 = tx("tools/stats/mathx.py")
    ass73 = tx("tools/assumption_check.py")
    reg73 = tx("tools/stats/regression.py")
    # v1.82：残差诊断随 regress.py 拆分落到 regression.py，这里按所属模块核对
    #（原先 reg73 只读不用，是死变量——现在真正断上）
    check("SW下沉mathx", "def shapiro_wilk" in mathx73 and "def durbin_watson" in mathx73
          and "def shapiro_wilk" not in ass73 and "shapiro_wilk" in ass73
          and "durbin_watson(resid)" in reg73 and "shapiro_wilk(resid)" in reg73)
    d73 = new_tmp("v173dw")
    reg_csv73 = d73 / "reg.csv"
    random.seed(17302)
    with open(str(reg_csv73), "w", encoding="utf-8-sig", newline="") as f73:
        w73 = csv.writer(f73)
        w73.writerow(["X1", "X2", "Y"])
        for _ in range(120):
            x1 = random.gauss(0, 1); x2 = random.gauss(0, 1)
            y = 1 + 0.5 * x1 - 0.3 * x2 + random.gauss(0, 1)
            w73.writerow([round(x1, 3), round(x2, 3), round(y, 3)])
    # DW 定义级手算
    sys.path.insert(0, str(ROOT / "tools"))
    from stats.mathx import durbin_watson as _dw73, shapiro_wilk as _sw73
    check("v173 DW手算", abs(_dw73([1.0, 2.0, 3.0]) - 2.0 / 14.0) < 1e-12
          and abs(_dw73([1.0] * 10) - 0.0) < 1e-12
          and abs(_dw73([1.0, -1.0] * 10) - 3.8) < 1e-12 and _dw73([1.0]) is None)
    w73h, p73h = _sw73([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    check("v173 SW下沉可用", w73h is not None and 0 < w73h <= 1)
    r = run([str(ROOT / "tools" / "auto_stats.py"), str(reg_csv73),
             "--y", "Y", "--x", "X1,X2"])
    o = r.stdout or ""
    check("v173回归跑通", r.returncode == 0 and "R²=0.292" in o and "F(2,117) = 24.112" in o)
    check("v173 DW输出", "Durbin-Watson=2.355" in o and "未见一阶自相关" in o)
    check("v173残差正态输出", "残差 Shapiro-Wilk：W=0.979，p=.060" in o and "近似正态" in o)
    # 自相关夹具：DW 必须跌破 1.5 并给正自相关提示
    ar_csv = d73 / "ar.csv"
    random.seed(17303)
    prev = 0.0
    with open(str(ar_csv), "w", encoding="utf-8-sig", newline="") as f73:
        w73 = csv.writer(f73)
        w73.writerow(["X", "Y"])
        for i in range(120):
            x = random.gauss(0, 1)
            prev = 0.8 * prev + random.gauss()
            w73.writerow([round(x, 3), round(prev + 0.3 * x, 3)])
    r = run([str(ROOT / "tools" / "auto_stats.py"), str(ar_csv), "--y", "Y", "--x", "X"])
    o = r.stdout or ""
    m73 = re.search(r"Durbin-Watson=([0-9.]+)", o)
    check("v173自相关报警", r.returncode == 0 and m73 is not None and float(m73.group(1)) < 1.5
          and "正自相关" in o)
    # 前提检验工具在 SW 迁移后仍正常
    r = run([str(ROOT / "tools" / "assumption_check.py"), str(reg_csv73), "--only", "X1"])
    check("v173前提工具回归", r.returncode == 0 and "Shapiro" in (r.stdout or ""))


    # ========== v1.74 论文模板接线（单样本/回归残差诊断进产出链） ==========
    outline74 = tx("templates/paper-outline.md")
    check("v174模板单样本接线", "--onesample" in outline74 and "单样本 t" in outline74
          and "偏离中点" in outline74)
    check("v174模板回归诊断接线", "Durbin-Watson" in outline74 and "残差 Shapiro-Wilk" in outline74
          and "VIF" in outline74)
    check("v174 START接线", "Durbin-Watson残差独立性" in tx("START.md"))
    quick74 = tx("QUICKSTART.md")
    check("v174 QUICKSTART接线", "Durbin-Watson" in quick74 and "单样本" in quick74)


    # ========== v1.75 路线图挂账与版本区收敛 ==========
    rm75 = tx("ROADMAP.md")
    check("v175 ROADMAP缺口挂账", all(k in rm75 for k in
          ("Friedman", "polychoric", "Schmid-Leiman", "HTMT2", "Cook", "PPT")))
    check("v175 MI决策落档", "不内置一键插补" in rm75 and "missing-imputation-guide" in rm75)
    # 原写法是"ROADMAP 不得提到 outline_to_ppt / pptx_writer"（当时它们尚未入库，
    # 禁令等价于防幽灵引用）。两个脚本已提交进仓库，禁令过时且会反向逼人把它们从
    # 文档里删掉。换成它本要表达的不变量：ROADMAP 点名的 .py 必须真实存在。
    ghost75 = [s for s in sorted(set(re.findall(r"([A-Za-z0-9_]+\.py)", rm75)))
               if not any((ROOT / d / s).exists()
                          for d in ("tools", "tools/stats", "tests", "doubao-skill"))]
    check("v175 ROADMAP引用的脚本都存在", not ghost75, str(ghost75))
    rdme75 = tx("README.md")
    check("v175 README版本区收敛", "更早版本（v1.64 及以前）" in rdme75
          and "上一个版本：v1." in rdme75 and len(rdme75.splitlines()) < 200)

    # ========== v1.76 文档勘误与行数守卫 ==========
    # v1.76 真正留下来的不变量是"README 版本区行数 ≤180"；当年顺带盯的那句勘误文字，
    # 已随 v1.85 记账瘦身进 维护档案/（不随包分发），所以这里改盯包内指针——
    # 与 case_15 的"包内 CHANGELOG 已瘦身且最新版详情在包内"同一条思路：盯活规矩，不盯历史正文的 Location。
    check("v176 勘误与行数守卫", len(tx("README.md").splitlines()) <= 180
          and "维护档案/CHANGELOG-历史详情" in tx("CHANGELOG.md"))

