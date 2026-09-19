# -*- coding: utf-8 -*-
"""并行复核会话交付物：行为锁定（防退回） ==========
full_e2e.py 顺序片段 14/14（原第 2101–2269 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ========== 并行复核会话交付物：行为锁定（防退回） ==========
    # 1) 前提假设工具：方差齐性的 df 必须按"实际参与的组"算，且小组要显式报出来
    v76 = new_tmp("v176guard")
    g76 = v76 / "g.csv"
    with open(g76, "w", encoding="utf-8-sig", newline="") as f76:
        w76 = csv.writer(f76)
        w76.writerow(["序号", "性别", "A1", "A2", "A3"])
        for i in range(40):
            lv = "男" if i % 2 == 0 else ("女" if i < 38 else "未填")
            w76.writerow([i + 1, lv, 2 + (i % 5), 3 + (i % 4), 2 + (i % 3)])
    s76 = v76 / "s.txt"
    s76.write_text("总量表:3=A1,A2,A3\n", encoding="utf-8")
    r = run(["tools/assumption_check.py", str(g76), "--scales", str(s76), "--group", "性别"])
    o76 = r.stdout or ""
    c76 = rt(v76 / "g_前提假设检验.csv")
    row76 = [ln for ln in c76.split("三、")[-1].splitlines() if ln.startswith("总量表,")]
    df1_76 = int(row76[0].split(",")[2]) if row76 and row76[0].split(",")[2].isdigit() else -99
    check("v176 小组被警告且进CSV", r.returncode == 0 and "未纳入组别" in c76
          and "未填" in o76 and "未填" in c76, o76[-200:])
    check("v176 df按实际参与组算", df1_76 == 1, f"读到 df1={df1_76}，两组参与应为 1")
    check("v176 单变量段落不写介于", "介于" not in o76)
    check("v176 声明记录未被删除", "未被删除" in o76 or "请勿当作已删除" in o76)

    # 2) 反向计分越界守卫：0 起编要报警，1 起编与 0/1 正向不得误报
    def _mk76(fn, vals, cols=3):
        p = v76 / fn
        with open(p, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["序号"] + [f"Q{j+1}" for j in range(cols)])
            for i, v in enumerate(vals):
                w.writerow([i + 1] + [v] * cols)
        return p
    cfg7 = v76 / "seven.txt"
    cfg7.write_text("七点:7=Q1(R),Q2,Q3\n", encoding="utf-8")
    for fn, vals, want in (("z.csv", [0, 1, 2, 3, 4, 5, 6, 1, 5, 3], True),
                           ("o.csv", [1, 2, 3, 4, 5, 6, 7, 1, 5, 4], False)):
        rr = run(["tools/assumption_check.py", str(_mk76(fn, vals)), "--scales", str(cfg7)])
        hit = "反向计分越界" in (rr.stdout or "")
        check("v176 反向计分守卫(0起编报警)" if want else "v176 反向计分守卫(1起编不误报)",
              rr.returncode == 0 and hit == want, rr.stdout[-160:])
    cfgb = v76 / "bin.txt"
    cfgb.write_text("计数:5=Q1,Q2,Q3\n", encoding="utf-8")
    rr = run(["tools/assumption_check.py", str(_mk76("b.csv", [0, 1, 0, 1, 1, 0, 1, 0, 1, 0])),
              "--scales", str(cfgb)])
    check("v176 0/1正向计分不误报", rr.returncode == 0 and "反向计分越界" not in (rr.stdout or ""))

    # 3) 大纲 → PPT：解析、坏输入硬失败、依赖缺失优雅降级
    op76 = "tools/outline_to_ppt.py"
    check("PPT工具声明只排版不代写", "只排版" in tx(op76) or "不替你写一个字" in tx(op76))
    check("PPT开题模板存在且自述用法",
          (ROOT / "templates" / "opening-ppt-outline.md").exists()
          and "outline_to_ppt.py" in tx("templates/opening-ppt-outline.md"))
    good76 = v76 / "大纲.md"
    good76.write_text("# 测试题目\n副标题：开题\n\n## 第1页：背景\n- 一级要点\n"
                      "  - 二级要点\n\n## 第2页：方法\n> 讲稿：这页讲方法\n- 甲\n\n"
                      "## 第3页：表\n| 变量 | 量表 |\n| --- | --- |\n| X | AIED |\n",
                      encoding="utf-8")
    rr = run([op76, str(good76), "--dry-run"])
    check("PPT大纲解析出4页(含封面)", rr.returncode == 0 and "解析到 4 页" in (rr.stdout or ""),
          (rr.stdout or "")[-200:])
    bad76 = v76 / "坏图.md"
    bad76.write_text("# T\n\n## 第1页：图\n![题注](根本没有.png)\n", encoding="utf-8")
    rr = run([op76, str(bad76)])
    check("PPT坏图片路径硬失败", rr.returncode != 0
          and "Traceback" not in (rr.stdout or "") + (rr.stderr or ""))
    # --dry-run 说"通过"而正式生成却硬失败，自检就成了误导（v1.80 修的正是这条）
    rr = run([op76, str(bad76), "--dry-run"])
    check("PPT自检与生成同口径拒坏图", rr.returncode != 0 and "图片找不到" in (rr.stdout or ""),
          (rr.stdout or "")[-160:])
    bad76b = v76 / "缺括号.md"
    bad76b.write_text("# T\n\n## 第1页：图\n![题注】\n", encoding="utf-8")
    rr = run([op76, str(bad76b)])
    check("PPT图片语法缺路径硬失败", rr.returncode != 0 and "图片语法不完整" in (rr.stdout or ""))
    try:
        import pptx  # noqa: F401
        outp = v76 / "x.pptx"
        rr = run([op76, str(good76), "-o", str(outp)])
        import zipfile
        okp = rr.returncode == 0 and outp.exists() and zipfile.is_zipfile(str(outp))
        if okp:
            # 必须显式 close：Windows 上句柄没释放就删不掉，会让收尾的
            # "测试临时文件残留"自检报 x.pptx 残留（踩过，别改成 with 以外的写法）
            zz = zipfile.ZipFile(str(outp))
            try:
                pts = re.findall(r'PartName="([^"]+)"', zz.read("[Content_Types].xml").decode())
                okp = zz.testzip() is None and len(pts) == len(set(pts))
            finally:
                zz.close()
        check("PPT真生成且包结构合法", okp, (rr.stdout or "")[-200:])

        # ---- v1.81 主题中文字体：生成物要拿到别处放映，字体必须写死在包里 ----
        # 默认模板的 a:ea 是空的，中文落到哪套字体全看各台机器的 Office 主题（宋体/等线/雅黑不一致）。
        def _theme_ea(pptx_path):
            zz = zipfile.ZipFile(str(pptx_path))
            try:
                th = zz.read("ppt/theme/theme1.xml").decode("utf-8")
            finally:
                zz.close()
            return re.findall(r'<a:ea typeface="([^"]*)"', th)

        if okp:
            ea_default = _theme_ea(outp)
            check("PPT主题默认写入中文字体",
                  len(ea_default) >= 2 and all(f == "微软雅黑" for f in ea_default), str(ea_default))
            out_song = v76 / "宋体.pptx"
            rr_s = run([op76, str(good76), "-o", str(out_song), "--cn-font", "宋体"])
            ea_song = _theme_ea(out_song) if rr_s.returncode == 0 and out_song.exists() else []
            check("PPT可换指定中文字体", bool(ea_song) and all(f == "宋体" for f in ea_song), str(ea_song))
            out_raw = v76 / "不改.pptx"
            rr_n = run([op76, str(good76), "-o", str(out_raw), "--cn-font", "none"])
            ea_raw = _theme_ea(out_raw) if rr_n.returncode == 0 and out_raw.exists() else ["跑不起来"]
            check("PPT选none时不动主题字体", all(f == "" for f in ea_raw), str(ea_raw))
            # 改主题要重写 zip：包还能被 python-pptx 打开、页页与越界不变量都不许退化
            try:
                from pptx import Presentation as _Pr76
                _pp = _Pr76(str(out_song))
                _w, _h = _pp.slide_width, _pp.slide_height
                _over = [(_i, sh.shape_type) for _i, _s in enumerate(_pp.slides, 1) for sh in _s.shapes
                         if sh.left is not None and sh.width is not None
                         and (sh.left + sh.width > _w + 100 or sh.top + sh.height > _h + 100)]
                check("PPT改字体后仍可回读且不越页", len(_pp.slides) == 4 and not _over, str(_over[:3]))
            except Exception as _e76:
                check("PPT改字体后仍可回读且不越页", False, repr(_e76)[:200])
    except ImportError:
        rr = run([op76, str(good76)])
        check("PPT缺依赖时优雅降级", rr.returncode != 0 and "python-pptx" in (rr.stdout or "")
              and "Traceback" not in (rr.stderr or ""))

    # 4) 工作区补齐：只新增、幂等、绝不删除已有
    wsroot = v76 / "proj"
    ws76 = wsroot / "我的工作区"
    (ws76 / "01-文献PDF").mkdir(parents=True)
    (ws76 / "01-文献PDF" / "学生的旧文件.txt").write_text("别动我", encoding="utf-8")
    rr = run(["tools/setup_workspace.py", "--root", str(wsroot)])
    dirs76 = sorted(p.name for p in ws76.iterdir() if p.is_dir())
    check("工作区补齐新建5个目录", rr.returncode == 0 and len(dirs76) == 9
          and "05-开题报告" in dirs76, str(dirs76))
    check("工作区补齐不动旧文件",
          (ws76 / "01-文献PDF" / "学生的旧文件.txt").read_text(encoding="utf-8") == "别动我")
    rr2 = run(["tools/setup_workspace.py", "--root", str(wsroot)])
    check("工作区补齐幂等", "没有新建" in (rr2.stdout or ""))
    rr3 = run(["tools/setup_workspace.py", "--root", str(wsroot), "--check"])
    check("工作区--check只报告不创建", rr3.returncode == 0 and "齐全" in (rr3.stdout or ""))

    # ========== v1.79 菜单拆分：结构不变量（防"搬完家忘了接线"） ==========
    check("v179菜单模块齐全", all((ROOT / "tools" / n).exists()
                                  for n in ("menu_io.py", "menu_data.py", "menu_lit.py")))
    check("v179菜单入口瘦身", len(tx("tools/menu.py").splitlines()) < 200,
          "lines=%d" % len(tx("tools/menu.py").splitlines()))
    # 用真实 import 核对菜单表，而不是再匹配一遍文本：处理器搬家后文本匹配抓不到
    # "某个 t_xxx 定义了却没进 MENU 表"（那正是拆分最容易犯的错）
    imp79 = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, 'tools'); "
         "import menu, menu_data, menu_lit, menu_thesis; "   # v1.85 起处理器三册，漏一册就判不平
         "wired = {f.__name__ for _, _, f in menu.MENU}; "
         "defs = {n for m in (menu_data, menu_lit, menu_thesis) for n in dir(m) if n.startswith('t_')};"
         "print(len(menu.MENU), all(callable(f) for _, _, f in menu.MENU), "
         "menu.MENU[0][0], menu.MENU[-1][0], defs == wired, sorted(defs - wired))"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    check("v179菜单表项数与标签一致且无漏接处理器",
          (imp79.stdout or "").strip() == "%d True 1 %d True []" % (MENU_N, MENU_N),
          ((imp79.stdout or "") + (imp79.stderr or ""))[-200:])
    # 拆完必须还能跑：喂一个"0"退出，主菜单要把 1..N 每一项都列出来，一项不能少
    mk79 = subprocess.run([sys.executable, "tools/menu.py"], input="0\n", capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=120)
    body79 = mk79.stdout or ""
    check("v179菜单可运行且列全各项",
          mk79.returncode == 0 and all(("\n  %d. " % i) in body79 for i in range(1, MENU_N + 1)),
          ((body79 or "") + (mk79.stderr or ""))[-200:])

    # ---- v1.86 编码守卫不再依赖 isatty() ----
    # 为什么钉这条：Git Bash 的 /dev/null 与 Windows 的 nul 都是字符设备，isatty() 返回 True，
    # 旧守卫于是跳过 UTF-8 归一、退回 GBK，打印 "文档 ↔ 代码" 这类字符直接 UnicodeEncodeError，
    # 让维护者看到"退出码 1 却没有一条漂移"的假失败。真控制台实测编码本就是 utf-8，无条件 reconfigure 对它无影响。
    nul86 = subprocess.run([sys.executable, "tests/consistency_check.py"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE, timeout=240)
    check("v186 输出丢给 NUL 时守卫脚本不假报失败", nul86.returncode == 0,
          (nul86.stderr or b"").decode("utf-8", "replace")[-260:])
    lazy86 = []
    for _d in ("tools", "tests", "doubao-skill"):
        for _p in (ROOT / _d).rglob("*.py"):
            if "__pycache__" in _p.parts:
                continue
            for _l in _p.read_text(encoding="utf-8").splitlines():
                if _l.strip().startswith("if hasattr(") and "reconfigure" in _l and "isatty" in _l:
                    lazy86.append(str(_p.relative_to(ROOT)))
    check("v186 守卫条件全仓库统一为无条件生效", not lazy86, str(sorted(set(lazy86))))
    # v1.86：菜单注释点名的分册必须与磁盘真实一致（v1.85 加 menu_thesis 时注释只提两册，就是这类错）。
    # 注：条数一律不写进注释——由 MENU 表自己数出来（`菜单标签编号连续且分母等于项数` 那条守），
    # 免得"改菜单忘改注释数字"再制造一次漂移。
    _m86 = tx("tools/menu.py")
    _named86 = sorted(set(re.findall(r"menu_\w+\.py", _m86)))
    _disk86 = sorted(p86.name for p86 in (ROOT / "tools").glob("menu_*.py"))
    check("v186菜单注释点名的分册齐全且真实", _named86 == _disk86
          and all((ROOT / "tools" / n).is_file() for n in _named86),
          "注释=%s 磁盘=%s" % (_named86, _disk86))
    check("v186菜单注释不再写死处理器条数", "个处理器" not in _m86,
          [l for l in _m86.splitlines() if "个处理器" in l][:2])

