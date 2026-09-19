# -*- coding: utf-8 -*-
"""v1.62 现代信效度：McDonald's ω（随 auto_stats 信度节产出）+ HTMT（--htmt 模式）----
full_e2e.py 顺序片段 2/14（原第 305–461 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ---- v1.62 现代信效度：McDonald's ω（随 auto_stats 信度节产出）+ HTMT（--htmt 模式）----
    # ω 在上面的 demo_survey 主回归里已随信度分析产出，这里核列、数值关系与纯标准库实现
    check("ω进入信度CSV", "McDonald_ω" in rel)
    omega = {}
    try:
        for row in csv.DictReader(open(TD / "demo_survey_信度分析.csv", encoding="utf-8-sig")):
            if row.get("McDonald_ω"):
                omega[row["量表"]] = float(row["McDonald_ω"])
    except Exception:
        pass
    check("ω数值合理", all(omega.get(k, 0) >= .70 for k in ["AI情感依赖", "孤独感", "反刍思维", "NSSI"])
          and all(omega[k] >= alpha[k] - .02 for k in omega if k in alpha), str(omega))
    check("ω进入stdout", "McDonald" in r.stdout and "ω" in r.stdout)
    rel_src = tx("tools/stats/reliability.py")
    check("ω纯标准库PAF", "def mcdonald_omega" in rel_src and "_paf_one_factor" in rel_src
          and "numpy" not in rel_src and "scipy" not in rel_src)
    # HTMT 固定夹具：两个正交 4 题构念（n=220），点估计黄金值 0.088（numpy 独立实现核对）
    hdir = new_tmp("htmt")
    for fn in ["demo_htmt.csv", "htmt_scales.txt"]:
        shutil.copy2(TD / fn, hdir / fn)
    hok = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt.csv"),
               "--scales", str(hdir / "htmt_scales.txt"), "--boot", "300"], 120)
    check("HTMT正交夹具", hok.returncode == 0 and "0.088" in hok.stdout and "区分效度成立" in hok.stdout
          and "CI上限" in hok.stdout, (hok.stderr or "")[-200:])
    mci = re.search(r"\[0\.\d{3}, (0\.\d{3})\]", hok.stdout)
    check("HTMT的CI上限<1", bool(mci) and float(mci.group(1)) < 0.5, hok.stdout[-400:])
    hcsv = hdir / "demo_htmt_HTMT区分效度.csv"
    check("HTMT导出CSV", hcsv.exists())
    if hcsv.exists():
        hrows = list(csv.reader(open(hcsv, encoding="utf-8-sig")))
        check("HTMT表内容", hrows[0][:6] == ["构念A", "构念B", "完整N", "HTMT", "CI下限", "CI上限"]
              and hrows[1][0] == "构念A" and abs(float(hrows[1][3]) - 0.0882) < .01, str(hrows[:2]))
    # 反向计分不变性：B 构念题项整体反向（6−x），scales 标 (R)，HTMT 点估计应保持一致
    with open(hdir / "demo_htmt.csv", encoding="utf-8-sig") as f:
        rdr = list(csv.reader(f)); hdr = rdr[0]; body = rdr[1:]
    bidx = [hdr.index(c) for c in ["B1", "B2", "B3", "B4"]]
    for row in body:
        for bi in bidx:
            row[bi] = str(6 - int(row[bi]))
    with open(hdir / "demo_htmt_rev.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(body)
    with open(hdir / "htmt_rev_scales.txt", "w", encoding="utf-8") as f:
        f.write("构念A:5=A1,A2,A3,A4\n构念B:5=B1(R),B2(R),B3(R),B4(R)\n")
    hrev = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt_rev.csv"),
                "--scales", str(hdir / "htmt_rev_scales.txt"), "--boot", "0"], 60)
    check("HTMT反向题等价", hrev.returncode == 0 and "0.088" in hrev.stdout, (hrev.stderr or "")[-200:])
    # 阴性夹具：同一因子拆成两个"量表"（n=220，固定随机种子），HTMT 应≥.90 且 CI 上限≥1
    import random as _rnd
    _rnd.seed(7)
    _lam = [0.74, 0.71, 0.69, 0.73, 0.67, 0.70]
    with open(hdir / "neg.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["id", "X1", "X2", "X3", "Y1", "Y2", "Y3"])
        for i in range(220):
            g = _rnd.gauss(0, 1); row = [i + 1]
            for L in _lam:
                v = 3 + .9 * (L * g + (1 - L * L) ** .5 * _rnd.gauss(0, 1))
                row.append(max(1, min(5, round(v))))
            w.writerow(row)
    with open(hdir / "neg_scales.txt", "w", encoding="utf-8") as f:
        f.write("构念X:5=X1,X2,X3\n构念Y:5=Y1,Y2,Y3\n")
    hneg = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "neg.csv"),
                "--scales", str(hdir / "neg_scales.txt"), "--boot", "300"], 120)
    check("HTMT同因子判失败", hneg.returncode == 0 and "不足" in hneg.stdout and "不通过" in hneg.stdout,
          hneg.stdout[-300:])
    # 守卫：缺 scales / 单量表 / boot 负数，均给中文提示且无 Traceback
    h_nosc = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt.csv")])
    check("HTMT缺scales守卫", h_nosc.returncode == 1 and "--scales" in h_nosc.stdout
          and "Traceback" not in (h_nosc.stdout or "") + (h_nosc.stderr or ""))
    with open(hdir / "one_scales.txt", "w", encoding="utf-8") as f:
        f.write("构念A:5=A1,A2,A3,A4\n")
    h_one = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt.csv"),
                 "--scales", str(hdir / "one_scales.txt")])
    check("HTMT单量表守卫", h_one.returncode == 1 and "不足 2 个" in h_one.stdout)
    h_negboot = run(["tools/validity_cr_ave.py", "--htmt", str(hdir / "demo_htmt.csv"),
                     "--scales", str(hdir / "htmt_scales.txt"), "--boot", "-1"])
    check("HTMT负boot守卫", h_negboot.returncode == 1 and "不能为负" in h_negboot.stdout
          and "Traceback" not in (h_negboot.stdout or "") + (h_negboot.stderr or ""))

    # ---- v1.60 预试项目分析工具 item_analysis.py（菜单14），决断值CR经 scipy 黄金核对 ----
    ia_src = tx("tools/item_analysis.py")
    check("项目分析纯标准库且复用stats", "import csv" in ia_src and "matplotlib" not in ia_src
          and "from stats.reliability import cronbach_alpha" in ia_src and "t_p_two_sided" in ia_src)
    ia_dir = new_tmp("item")
    ia_ok = run(["tools/item_analysis.py", str(TD / "demo_survey.csv"),
                 "--scales", str(TD / "demo_scales.txt"), "--only", "孤独感",
                 "--csv-out", str(ia_dir)])
    check("项目分析决断值", ia_ok.returncode == 0 and "18.519" in ia_ok.stdout
          and "决断值" in ia_ok.stdout and "高/低分组各 54 人" in ia_ok.stdout and "保留" in ia_ok.stdout)
    ia_out = ia_dir / "demo_survey_项目分析.csv"
    check("项目分析CSV导出", ia_out.exists())
    if ia_out.exists():
        ia_rows = list(csv.reader(open(ia_out, encoding="utf-8-sig")))
        check("项目分析CSV内容", ia_rows[0][:6] == ["量表", "题项", "均值", "标准差", "决断值CR", "自由度df"]
              and len(ia_rows) == 5 and all(r[10] == "保留" for r in ia_rows[1:]), str(ia_rows[:2]))
    ia_badg = run(["tools/item_analysis.py", str(TD / "demo_survey.csv"),
                   "--scales", str(TD / "demo_scales.txt"), "--group", "0.9"])
    check("项目分析坏比例守卫", ia_badg.returncode == 1 and "0.10" in ia_badg.stdout
          and "Traceback" not in (ia_badg.stdout or "") + (ia_badg.stderr or ""))
    ia_noscale = run(["tools/item_analysis.py", str(TD / "demo_survey.csv")])
    check("项目分析缺配置守卫", ia_noscale.returncode == 1 and "--scales" in ia_noscale.stdout)

    # ---- v1.60 自编量表内容效度 content_cvi.py（菜单15），黄金值对照 Lynn/Polit 算例 ----
    cvi_src = tx("tools/content_cvi.py")
    check("内容效度纯标准库", "import csv" in cvi_src and "matplotlib" not in cvi_src
          and "math.comb" in cvi_src and "read_data" in cvi_src)
    cvi_dir = new_tmp("cvi")
    cvi_ok = run(["tools/content_cvi.py", str(TD / "demo_cvi.csv"), "--csv-out", str(cvi_dir)])
    # 5专家×4题：A=5,5,4,2 → I-CVI 1/1/.8/.4；κ*=1/1/.763/.127；S-CVI/Ave=.80、UA=.50
    check("内容效度指数", cvi_ok.returncode == 0 and "I-CVI=1.000" in cvi_ok.stdout
          and "I-CVI=0.800" in cvi_ok.stdout and "κ*=0.763" in cvi_ok.stdout
          and "κ*=0.127" in cvi_ok.stdout and "S-CVI/Ave=0.800" in cvi_ok.stdout
          and "S-CVI/UA=0.500" in cvi_ok.stdout)
    cvi_out = cvi_dir / "demo_cvi_内容效度CVI.csv"
    check("内容效度CSV导出", cvi_out.exists())
    if cvi_out.exists():
        cvi_rows = list(csv.reader(open(cvi_out, encoding="utf-8-sig")))
        check("内容效度CSV内容", cvi_rows[0][:5] == ["条目", "专家数N", "评相关人数A", "I-CVI", "机遇一致Pc"]
              and len(cvi_rows) == 5 and cvi_rows[3][3] == "0.8" and cvi_rows[4][3] == "0.4"
              and cvi_rows[1][7] == "0.8", str(cvi_rows))
    cvi_bad = run(["tools/content_cvi.py", str(TD / "demo_cvi.csv"), "--threshold", "5"])
    check("内容效度坏阈值守卫", cvi_bad.returncode == 1 and "--threshold" in cvi_bad.stdout
          and "Traceback" not in (cvi_bad.stdout or "") + (cvi_bad.stderr or ""))

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
    # 菜单实现拆成 menu.py（入口与菜单表）+ menu_io/menu_data/menu_lit（交互件与两组处理器），
    # 断言一律看合并文本，免得每拆一次就要改一批断言。
    menu = "\n".join(tx("tools/" + p.name) for p in sorted((ROOT / "tools").glob("menu*.py")))
    check("menu第8项", "【8/22】" in menu and "sample_size.py" in menu)
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
