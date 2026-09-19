# -*- coding: utf-8 -*-
"""v1.68 配对设计差异检验（前后测/两条件） ==========
full_e2e.py 顺序片段 11/14（原第 1614–1763 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ========== v1.68 配对设计差异检验（前后测/两条件） ==========
    pc_tool = str(ROOT / "tools" / "paired_compare.py")
    pc_src = tx("tools/paired_compare.py")
    check("配对工具存在", Path(pc_tool).exists())
    check("配对工具纯标准库", "pandas" not in pc_src and "numpy" not in pc_src
          and "import csv" in pc_src)
    check("配对工具编码守卫", "输出编码守卫" in pc_src and "reconfigure" in pc_src)
    check("菜单第19项配对检验", "【19/22】" in menu and "paired_compare.py" in menu
          and "Wilcoxon" in menu)
    check("统计指南接线配对工具", "paired_compare.py" in tx("psychology/stats-guide.md"))
    check("分析流程接线配对工具", "paired_compare.py" in tx("workflows/data-analysis-auto.md"))
    check("START登记配对工具", "paired_compare.py" in st)

    v68 = new_tmp("v168paired")

    def wcsv68(name, headers68, rows68, enc="utf-8-sig"):
        p68 = v68 / name
        with open(p68, "w", encoding=enc, newline="") as f68:
            w68 = csv.writer(f68)
            w68.writerow(headers68)
            w68.writerows(rows68)
        return p68

    def both68(rr):
        return (rr.stdout or "") + (rr.stderr or "")

    # 宽表夹具：n=60，后测=前测+0.6+小噪声；前30实验组
    random.seed(16803)
    pre68 = [random.gauss(3, 1) for _ in range(60)]
    post68 = [x + 0.6 + random.gauss(0, 0.5) for x in pre68]
    wide68 = wcsv68("wide.csv", ["编号", "组别", "前测X", "后测X", "同前", "同后"],
                    [[i + 1, "实验组" if i < 30 else "对照组",
                      round(pre68[i], 4), round(post68[i], 4),
                      round(pre68[i], 4), round(pre68[i], 4)] for i in range(60)])
    r = run([pc_tool, str(wide68), "--pairs", "前测X:后测X"])
    out68 = both68(r)
    check("v168基本配对跑通", r.returncode == 0 and "配对 t" in out68
          and "Wilcoxon" in out68 and "d_z" in out68)
    mt = re.search(r"配对 t\(59\)=([\d.]+)", out68)
    check("v168配对t黄金值", mt is not None and abs(float(mt.group(1)) - 9.319) < 0.02,
          mt.group(1) if mt else "?")
    mdz = re.search(r"d_z=([\d.]+)", out68)
    check("v168 d_z黄金值", mdz is not None and abs(float(mdz.group(1)) - 1.203) < 0.01,
          mdz.group(1) if mdz else "?")
    mw = re.search(r"差值 Shapiro-Wilk 不显著（p=([\d.]+)）", out68)
    check("v168差值正态", mw is not None)
    check("v168 Wilcoxon近似", "z=" in out68 and "连续性校正" in out68)
    r = run([pc_tool, str(wide68), "--pairs", "前测X:后测X",
             "--group", "组别", "--level", "实验组"])
    check("v168分组内配对", r.returncode == 0 and "配对数 n=30" in (r.stdout or ""))
    csv68 = (v68 / "wide_配对检验.csv").read_text(encoding="utf-8-sig")
    check("v168 CSV表头", "配对n" in csv68 and "Wilcoxon_p" in csv68 and "差值Shapiro_p" in csv68)
    rep68 = (v68 / "wide_配对检验报告.txt").read_text(encoding="utf-8")
    check("v168报告段落", "配对样本 t 检验" in rep68 and "差值近似正态" in rep68)
    r = run([pc_tool, str(wide68), "--pairs", "同前:同后"])
    check("v168常量差值优雅降级", r.returncode == 0 and "差值标准差为 0" in (r.stdout or ""))

    # 强偏态差值：Shapiro 显著 → 建议以 Wilcoxon 为准
    random.seed(16804)
    skew68 = wcsv68("skew.csv", ["前测Y", "后测Y"],
                    [[0, round(random.expovariate(1 / 3), 4)] for _ in range(60)])
    r = run([pc_tool, str(skew68), "--pairs", "前测Y:后测Y"])
    out_s = both68(r)
    ms = re.search(r"W=([\d.]+)，", out_s)
    check("v168偏态差值W黄金值", ms is not None and abs(float(ms.group(1)) - 0.7613) < 0.01,
          ms.group(1) if ms else "?")
    check("v168偏态推Wilcoxon", r.returncode == 0 and "建议以 Wilcoxon 为准" in out_s)

    # 小样本精确检验（n=5，无结无零）
    exact68 = wcsv68("exact.csv", ["a", "b"],
                     [[0, 1.1], [0, -2.3], [0, 0.7], [0, 3.2], [0, -0.4]])
    r = run([pc_tool, str(exact68), "--pairs", "a:b"])
    check("v168精确Wilcoxon", r.returncode == 0 and "精确双侧 p=" in (r.stdout or ""))

    # 两文件 id 配对（打乱+各自多出人）
    pre_rows68 = [[i + 1, round(pre68[i], 4)] for i in range(60)] + [[801, 2.9]]
    order68 = list(range(60))
    random.seed(16805)
    random.shuffle(order68)
    post_rows68 = [[j + 1, round(post68[j], 4)] for j in order68] + [[901, 3.1], [902, 3.2]]
    fpre68 = wcsv68("pre.csv", ["编号", "前测X"], pre_rows68)
    fpost68 = wcsv68("post.csv", ["编号", "后测X"], post_rows68)
    r = run([pc_tool, str(fpre68), str(fpost68), "--id", "编号",
             "--pairs", "前测X:后测X"])
    out_id = both68(r)
    check("v168双文件id配对", r.returncode == 0 and "配对数 n=60" in out_id
          and "前测独有 1 人、后测独有 2 人" in out_id)

    # 两文件 scales（含反向题，各缺 2 人）
    (v68 / "sc.txt").write_text("积极:5=P1,P2,P3(R)\n", encoding="utf-8")
    rnd68 = random.Random(16806)
    def lik68(shift):
        return [[i, rnd68.randint(2, 5), rnd68.randint(2, 5),
                 min(5, rnd68.randint(2, 5) + shift)] for i in range(1, 51)]
    spre68 = wcsv68("s_pre.csv", ["编号", "P1", "P2", "P3"], lik68(0))
    spost68 = wcsv68("s_post.csv", ["编号", "P1", "P2", "P3"],
                     [[i, rnd68.randint(2, 5), rnd68.randint(2, 5),
                       min(5, rnd68.randint(2, 5) + 1)] for i in range(3, 53)])
    r = run([pc_tool, str(spre68), str(spost68), "--id", "编号",
             "--scales", str(v68 / "sc.txt")])
    check("v168双文件scales", r.returncode == 0 and "积极" in (r.stdout or "")
          and "配对数 n=48" in (r.stdout or ""))

    # n<3 优雅提示
    tiny68 = wcsv68("tiny.csv", ["a", "b"], [[1, 2], [1.5, 2.5]])
    r = run([pc_tool, str(tiny68), "--pairs", "a:b"])
    check("v168配对n<3提示", r.returncode == 0 and "至少需要 3 对" in (r.stdout or ""))

    # 坏输入硬失败
    r = run([pc_tool, str(v68 / "nope.csv"), "--pairs", "a:b"])
    check("v168文件不存在", r.returncode != 0 and "找不到文件" in both68(r))
    r = run([pc_tool, str(wide68)])
    check("v168缺pairs", r.returncode != 0 and "--pairs" in both68(r))
    r = run([pc_tool, str(wide68), "--pairs", "前测X"])
    check("v168 pairs格式", r.returncode != 0 and "前测列:后测列" in both68(r))
    r = run([pc_tool, str(wide68), "--pairs", "前测X:后测Y"])
    check("v168列不存在", r.returncode != 0 and "不在数据中" in both68(r))
    r = run([pc_tool, str(fpre68), str(fpost68), "--pairs", "前测X:后测X"])
    check("v168双文件缺id", r.returncode != 0 and "--id" in both68(r))
    r = run([pc_tool, str(wide68), "--pairs", "前测X:后测X", "--group", "组别"])
    check("v168 group缺level", r.returncode != 0 and "--level" in both68(r))
    r = run([pc_tool, str(wide68), "--pairs", "前测X:后测X", "--alpha", "0"])
    check("v168坏alpha", r.returncode != 0 and "alpha" in both68(r))
    emp68 = v68 / "empty.csv"
    emp68.write_text("", encoding="utf-8")
    r = run([pc_tool, str(emp68), "--pairs", "a:b"])
    check("v168空文件", r.returncode != 0)
    r = run([pc_tool, str(wide68), "--scales", str(v68 / "sc.txt")])
    check("v168单文件禁scales", r.returncode != 0 and "不支持 --scales" in both68(r))
    r = run([pc_tool, str(fpre68), str(fpost68), "--id", "学号",
             "--pairs", "前测X:后测X"])
    check("v168 id列缺失", r.returncode != 0 and "编号列" in both68(r))
    badsc68 = v68 / "badsc.txt"
    badsc68.write_text("坏表:5=P1,不存在\n", encoding="utf-8")
    r = run([pc_tool, str(spre68), str(spost68), "--id", "编号",
             "--scales", str(badsc68)])
    check("v168坏scales", r.returncode != 0)
    # GBK 输入
    gbk68 = v68 / "gbk.csv"
    gbk68.write_text("编号,前测A,后测A\n" +
                     "\n".join(f"{i+1},{pre68[i]:.4f},{post68[i]:.4f}" for i in range(60)),
                     encoding="gbk")
    r = run([pc_tool, str(gbk68), "--pairs", "前测A:后测A"])
    check("v168 GBK可读", r.returncode == 0 and "配对 t" in (r.stdout or ""))
    # 红线
    check("v168红线同一个体", "配对必须是同一个体" in pc_src)
    check("v168红线差值前提", "差值" in pc_src and "近似正态" in pc_src)
    check("v168红线多时点", "重复测量" in pc_src and "交互作用" in pc_src)


