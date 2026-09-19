# -*- coding: utf-8 -*-
"""v1.66 缺失值分析与 Little's MCAR =================
full_e2e.py 顺序片段 9/14（原第 1375–1496 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ================= v1.66 缺失值分析与 Little's MCAR =================
    mr_tool = "tools/missing_report.py"
    mr_src = tx(mr_tool)
    check("缺失值工具纯标准库", "pandas" not in mr_src and "numpy" not in mr_src
          and "import csv" in mr_src)
    check("缺失值工具编码守卫", "输出编码守卫" in mr_src and "reconfigure" in mr_src)
    check("菜单第17项缺失值", "【17/" in menu and "missing_report.py" in menu and "MCAR" in menu)
    check("统计指南接线缺失值工具", "missing_report.py" in tx("psychology/stats-guide.md"))
    check("分析流程接线缺失值工具", "missing_report.py" in tx("workflows/data-analysis-auto.md"))
    check("START登记缺失值工具", "missing_report.py" in st)
    v66 = new_tmp("v166missing")
    K66 = 8
    LOAD66 = [0.55 + 0.05 * j for j in range(K66)]

    def gen66(n, seed, miss=0.0, mar=False):
        random.seed(seed)
        rows = []
        for _ in range(n):
            f = random.gauss(0, 1)
            rows.append([round(LOAD66[j] * f + math.sqrt(1 - LOAD66[j] ** 2) * random.gauss(0, 1), 3)
                         for j in range(K66)])
        if miss:
            for row in rows:
                for j in range(K66):
                    if random.random() < miss:
                        row[j] = ""
        if mar:
            cut = sorted(rr[0] for rr in rows)[n // 2]
            for row in rows:
                if row[0] < cut:
                    if random.random() < 0.4:
                        row[4] = ""
                    if random.random() < 0.4:
                        row[5] = ""
        return rows

    def wcsv66(name, rows, enc="utf-8-sig"):
        p66 = v66 / name
        with open(p66, "w", encoding=enc, newline="") as f66:
            w66 = csv.writer(f66)
            w66.writerow(["序号"] + [f"Q{j+1}" for j in range(K66)])
            for i, row in enumerate(rows):
                w66.writerow([i + 1] + row)
        return p66

    sc66 = v66 / "scales66.txt"
    sc66.write_text("总量表:8=" + ",".join(f"Q{j+1}" for j in range(K66)) + "\n", encoding="utf-8")

    rows_mcar = gen66(240, 1660918, miss=0.07)
    exp_miss = sum(1 for row in rows_mcar for v in row if v == "")
    exp_complete = sum(1 for row in rows_mcar if all(v != "" for v in row))
    pats66 = {}
    for row in rows_mcar:
        o = tuple(j for j in range(K66) if row[j] != "")
        pats66[o] = pats66.get(o, 0) + 1
    exp_df = sum(len(o) for o in pats66) - K66
    mp = wcsv66("mcar.csv", rows_mcar)
    r = run([mr_tool, str(mp), "--scales", str(sc66)])
    out = r.stdout or ""
    m_chi = re.search(r"χ²\((\d+)\) = ([\d.]+)，([\d.]+)", out)
    check("v166 MCAR跑通", r.returncode == 0 and m_chi is not None, out[-300:])
    if m_chi:
        check("v166 df与手算一致", int(m_chi.group(1)) == exp_df,
              f"工具 {m_chi.group(1)} vs 手算 {exp_df}")
        check("v166 χ²黄金值", abs(float(m_chi.group(2)) - 165.839) < 0.5, m_chi.group(2))
        check("v166 MCAR不拒绝且措辞正确", float(m_chi.group(3)) > 0.05
              and "未拒绝完全随机缺失" in out)
    check("v166总缺失格数", f"{exp_miss}/{240 * K66} 格" in out)
    check("v166完整样本量", f"完整作答 {exp_complete} 份" in out)
    csv66 = (v66 / "mcar_缺失值分析.csv").read_text(encoding="utf-8-sig")
    check("v166 CSV三段式", all(s in csv66 for s in ["逐题缺失", "缺失模式", "MCAR 检验"])
          and "○" in csv66 and "×" in csv66)
    rep66 = (v66 / "mcar_缺失值报告.txt").read_text(encoding="utf-8")
    check("v166报告段落", "Little's MCAR 检验" in rep66 and "总缺失率" in rep66)
    check("v166报告含模式明细", "缺失模式（○=作答 ×=缺失）" in rep66 and "完整作答" in rep66)

    ap = wcsv66("mar.csv", gen66(240, 1660918, mar=True))
    r = run([mr_tool, str(ap), "--scales", str(sc66)])
    out_a = r.stdout or ""
    ma = re.search(r"χ²\((\d+)\) = ([\d.]+)", out_a)
    check("v166 MAR拒绝并给插补建议", r.returncode == 0 and "拒绝完全随机缺失" in out_a
          and "多重插补" in out_a)
    check("v166 MAR黄金值", ma is not None and int(ma.group(1)) == 20
          and abs(float(ma.group(2)) - 63.698) < 0.5, out_a[-200:])

    fp = wcsv66("full.csv", gen66(120, 1660920))
    r = run([mr_tool, str(fp), "--scales", str(sc66)])
    check("v166无缺失不出检验", r.returncode == 0 and "无任何缺失" in (r.stdout or ""))

    rc_rows = gen66(60, 1660920)
    for row in rc_rows:
        row[0] = ""
    cp = wcsv66("colmiss.csv", rc_rows)
    r = run([mr_tool, str(cp), "--scales", str(sc66)])
    check("v166整列缺失硬失败", r.returncode != 0 and "全部缺失" in (r.stdout or ""))
    bad = v66 / "bad.txt"
    bad.write_text("坏表:8=Q1,不存在题\n", encoding="utf-8")
    r = run([mr_tool, str(mp), "--scales", str(bad)])
    check("v166坏量表硬失败", r.returncode != 0)
    r = run([mr_tool, str(v66 / "nope.csv")])
    check("v166文件不存在硬失败", r.returncode != 0 and "文件不存在" in (r.stdout or ""))
    r = run([mr_tool])
    check("v166无参数硬失败", r.returncode != 0 and "问卷数据 CSV" in (r.stdout or ""))
    ep66 = v66 / "empty.csv"
    ep66.write_text("", encoding="utf-8")
    r = run([mr_tool, str(ep66)])
    check("v166空文件硬失败", r.returncode != 0 and "没有任何记录行" in (r.stdout or ""))
    r = run([mr_tool, str(mp), "--scales", str(sc66), "--alpha", "x"])
    check("v166坏alpha硬失败", r.returncode != 0 and "--alpha" in (r.stdout or ""))
    gp66 = wcsv66("gbk.csv", rows_mcar, enc="gbk")
    r = run([mr_tool, str(gp66), "--scales", str(sc66)])
    check("v166 GBK输入", r.returncode == 0)
    const_rows = []
    random.seed(1)
    for i in range(60):
        const_rows.append(["" if i % 7 == 0 else 3,
                           round(random.gauss(0, 1), 2), round(random.gauss(0, 1), 2)])
    kp66 = wcsv66("const.csv", const_rows)
    r = run([mr_tool, str(kp66)])
    check("v166常量列硬失败", r.returncode != 0 and "常量列" in (r.stdout or ""))
    check("v166红线声明", "检验不能证明 MCAR" in mr_src)

