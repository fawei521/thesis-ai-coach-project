# -*- coding: utf-8 -*-
"""v1.67 参数检验前提假设（正态性/方差齐性） ==========
full_e2e.py 顺序片段 10/14（原第 1497–1613 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ========== v1.67 参数检验前提假设（正态性/方差齐性） ==========
    ac_tool = str(ROOT / "tools" / "assumption_check.py")
    ac_src = tx("tools/assumption_check.py")
    check("前提假设工具存在", Path(ac_tool).exists())
    check("前提工具纯标准库", "pandas" not in ac_src and "numpy" not in ac_src
          and "import csv" in ac_src)
    check("前提工具编码守卫", "输出编码守卫" in ac_src and "reconfigure" in ac_src)
    check("菜单第18项前提假设", "【18/" in menu and "assumption_check.py" in menu
          and "Shapiro" in menu)
    check("统计指南接线前提工具", "assumption_check.py" in tx("psychology/stats-guide.md"))
    check("分析流程接线前提工具", "assumption_check.py" in tx("workflows/data-analysis-auto.md"))
    check("START登记前提工具", "assumption_check.py" in st)

    v67 = new_tmp("v167assump")

    def wcsv67(name, headers67, rows67, enc="utf-8-sig"):
        p67 = v67 / name
        with open(p67, "w", encoding=enc, newline="") as f67:
            w67 = csv.writer(f67)
            w67.writerow(headers67)
            w67.writerows(rows67)
        return p67

    random.seed(16701)
    grp_rows = []
    for i in range(120):
        g67 = "A" if i < 60 else "B"
        sd2 = 1.0 if g67 == "A" else 2.6
        grp_rows.append([g67, round(random.gauss(0, 1), 3),
                         round(random.gauss(0, sd2), 3)])
    gp67 = wcsv67("grp.csv", ["grp", "X1", "X2"], grp_rows)
    r = run([ac_tool, str(gp67), "--group", "grp"])
    out67 = r.stdout or ""
    check("v167分组跑通", r.returncode == 0 and "Brown-Forsythe" in out67)
    check("v167 X1不拒绝正态", "不拒绝正态" in out67)
    mW = re.search(r"X1\s+总体\s+120[^\n]*?(0\.\d{4})\s+\.120", out67)
    check("v167 X1 W黄金值", mW is not None and abs(float(mW.group(1)) - 0.9825) < 0.002,
          mW.group(1) if mW else "?")
    mlev = re.search(r"X2\s+([\d.]+)\s+1,118\s+<.001\s+方差不齐", out67)
    check("v167 X2方差不齐黄金F",
          mlev is not None and abs(float(mlev.group(1)) - 31.993) < 0.6,
          mlev.group(1) if mlev else "?")
    check("v167 X1方差齐", "方差齐性成立" in out67)
    csv67 = (v67 / "grp_前提假设检验.csv").read_text(encoding="utf-8-sig")
    check("v167 CSV三段式", all(s in csv67 for s in
          ["总体正态性", "分组组内正态性", "方差齐性"]))
    rep67 = (v67 / "grp_前提假设报告.txt").read_text(encoding="utf-8")
    check("v167报告段落", "Shapiro-Wilk" in rep67 and "Brown-Forsythe" in rep67)

    random.seed(16702)
    exp_rows = [[round(random.expovariate(1 / 3), 3)] for _ in range(120)]
    ep67 = wcsv67("exp.csv", ["Y"], exp_rows)
    r = run([ac_tool, str(ep67)])
    out_e = r.stdout or ""
    me = re.search(r"Y\s+总体[^\n]*?(0\.\d{4})\s+<.001", out_e)
    check("v167指数W黄金值", me is not None and abs(float(me.group(1)) - 0.8101) < 0.005,
          me.group(1) if me else "?")
    check("v167 z极显著建议Bootstrap主分析", "为主分析" in out_e)

    random.seed(16703)
    sev_rows = [[round(math.exp(random.gauss(0, 1)), 3)] for _ in range(120)]
    sp67 = wcsv67("severe.csv", ["Z"], sev_rows)
    r = run([ac_tool, str(sp67)])
    check("v167强偏态超Kline", r.returncode == 0 and "超Kline判据" in (r.stdout or ""))

    random.seed(16704)
    lik_head = ["grp"] + [f"L{j}" for j in range(1, 5)]
    lik_rows = []
    for i in range(100):
        f67 = random.gauss(0, 1)
        lik_rows.append(["A" if i < 50 else "B"] + [
            max(1, min(5, int(round(3 + 0.7 * f67 + 0.7 * random.gauss(0, 1)))))
            for _ in range(4)])
    lp67 = wcsv67("lik.csv", lik_head, lik_rows)
    lsc = v67 / "lik.txt"
    lsc.write_text("L量表:5=L1,L2,L3,L4\n", encoding="utf-8")
    r = run([ac_tool, str(lp67), "--scales", str(lsc), "--group", "grp"])
    check("v167 scales均分模式", r.returncode == 0 and "L量表" in (r.stdout or ""))

    random.seed(16705)
    big_rows = [[round(random.gauss(0, 1), 3)] for _ in range(5005)]
    bp67 = wcsv67("big.csv", ["X"], big_rows)
    r = run([ac_tool, str(bp67)])
    check("v167 n>5000口径提示", r.returncode == 0 and "n>5000" in (r.stdout or ""))

    tp67 = wcsv67("tiny.csv", ["grp", "X"], [["a", 1], ["a", 2], ["b", 5]])
    r = run([ac_tool, str(tp67), "--group", "grp"])
    check("v167组内n<3降级", r.returncode == 0 and "样本不足" in (r.stdout or ""))
    random.seed(16706)
    cp67 = wcsv67("const.csv", ["X", "Y"],
                  [[3, round(random.gauss(0, 1), 3)] for _ in range(40)])
    r = run([ac_tool, str(cp67)])
    check("v167常量列提示", r.returncode == 0 and "常量" in (r.stdout or ""))

    r = run([ac_tool, str(v67 / "nope.csv")])
    check("v167文件不存在硬失败", r.returncode != 0 and "找不到数据文件" in (r.stdout or ""))
    epm = v67 / "empty.csv"
    epm.write_text("", encoding="utf-8")
    r = run([ac_tool, str(epm)])
    check("v167空文件硬失败", r.returncode != 0 and "数据为空" in (r.stdout or ""))
    bad67 = v67 / "bad.txt"
    bad67.write_text("坏表:8=Q1,不存在\n", encoding="utf-8")
    r = run([ac_tool, str(lp67), "--scales", str(bad67)])
    check("v167坏量表硬失败", r.returncode != 0)
    r = run([ac_tool, str(gp67), "--group", "无此列"])
    check("v167分组列缺失硬失败", r.returncode != 0 and "找不到分组列" in (r.stdout or ""))
    g1p = wcsv67("g1.csv", ["grp", "X"], [["同", float(x)] for x in range(30)])
    r = run([ac_tool, str(g1p), "--group", "grp"])
    check("v167仅一组硬失败", r.returncode != 0 and "只有 1 个" in (r.stdout or ""))
    r = run([ac_tool, str(gp67), "--alpha", "x"])
    check("v167坏alpha硬失败", r.returncode != 0 and "--alpha" in (r.stdout or ""))
    r = run([ac_tool])
    check("v167无参数硬失败", r.returncode != 0 and "usage" in (r.stdout or ""))
    check("v167红线声明", "凑正态" in ac_src and "不得为了" in ac_src)



