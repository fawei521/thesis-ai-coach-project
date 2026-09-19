# -*- coding: utf-8 -*-
"""v1.83 记账归档：版本史/计划/用例台账的历史正文移入 维护档案/（git 追踪、不进发布包）。
full_e2e.py 顺序片段 15/15（由壳按序 exec，不单独运行）。
骨架名字与前面各段产出的变量都在同一命名空间里，与拆分前语义一致。
注意：本段的断言必须在“开发树”和“发布包干净副本”两种形态下都成立——
维护档案/ 按设计不进包，所以凡是读它的核对都只在开发树跑，包里改跑等价的指针核对。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    arch = ROOT / "维护档案"
    in_pkg = not arch.is_dir()          # 干净解压副本 / 学生包：按设计没有档案目录
    check("v183 档案三件齐（开发树）或指针在（包内）",
          (all((arch / f).is_file() for f in ["CHANGELOG-历史详情-v1.0-v1.75.md",
                                              "PROJECT_PLAN-逐版优化叙事.md",
                                              "e2e-test-历史用例-测试1至54.md", "README.md"])
           if not in_pkg else
           "维护档案/CHANGELOG-历史详情" in tx("CHANGELOG.md")
           and "维护档案/PROJECT_PLAN-逐版优化叙事" in tx("PROJECT_PLAN.md")
           and "维护档案/e2e-test-历史用例" in tx("tests/e2e-test.md")),
          "in_pkg=%s" % in_pkg)
    chg83 = tx("CHANGELOG.md")
    rows83 = [l for l in chg83.splitlines() if re.match(r"^\| \*\*v[\d.]+\*\* \|", l)]
    check("包内 CHANGELOG 索引仍全量", len(rows83) >= 93 and "| **v1.0** |" in chg83
          and "_发布包" in chg83, "rows=%d" % len(rows83))
    # 原来盯的是某版详情里一句写死的字面量——详情一归档就得手动换哨兵。改成真实不变量：
    # 包内 CHANGELOG 必须 <320 行、**最新那一版必须在包内留有详情块**、指向档案的指针仍在。
    _latest82 = rows83[0].split("|")[1].strip().strip("*")
    check("包内 CHANGELOG 已瘦身且最新版详情在包内", len(chg83.splitlines()) < 320
          and ("**" + _latest82 + " ") in chg83 and "维护档案/CHANGELOG-历史详情" in chg83,
          "lines=%d latest=%s" % (len(chg83.splitlines()), _latest82))
    check("最新索引行主题不超过40字", len(rows83[0].split("|")[3].strip()) <= 40,
          "%d 字：%s" % (len(rows83[0].split("|")[3].strip()), rows83[0][:60]))
    pp83 = tx("PROJECT_PLAN.md")
    check("PROJECT_PLAN 不再重复逐版清单", len(pp83.splitlines()) < 320
          and not re.search(r"^## .、v1\.\d+ 优化", pp83, re.M),
          "lines=%d" % len(pp83.splitlines()))
    et83 = tx("tests/e2e-test.md")
    lab_index = [x.strip() for x in re.findall(r"^\| 测试([^ |]+) \|", et83, re.M)]
    lab_here = re.findall(r"^## 测试([^：:]+)[：:]", et83, re.M)
    homes = re.findall(r"^\| 测试[^|]+\|[^|]+\| (.*) \|$", et83, re.M)
    check("e2e 用例索引全量且每条都有归属", len(lab_index) >= 84 and len(set(lab_index)) == len(lab_index)
          and all(h.strip().startswith(("`维护档案/", "本文件")) for h in homes)
          and all(n in lab_index for n in ("1", "14b", "14c-2", "54", "63", "64", "78")),
          "索引%d 归属%d" % (len(lab_index), len(homes)))
    check("包内正文的用例编号都在索引里（不产生孤儿用例）",
          all(n in lab_index for n in lab_here) and any(n in lab_here for n in ("77", "78")),
          "本文件正文%d 条" % len(lab_here))
    if not in_pkg:      # 只有开发树能做的核对：档案正文与索引必须一一对应、不重不漏
        lab_arch = re.findall(r"^## 测试([^：:]+)[：:]",
                              (arch / "e2e-test-历史用例-测试1至54.md").read_text(encoding="utf-8"), re.M)
        dup = sorted({x for x in lab_here + lab_arch if (lab_here + lab_arch).count(x) > 1})
        check("档案正文与索引一一对应（不重不漏）",
              sorted(lab_here + lab_arch) == sorted(lab_index) and not dup,
              "档案%d 包内%d 索引%d 重复%s" % (len(lab_arch), len(lab_here), len(lab_index), dup or "无"))
    check("维护档案被排除在发布包之外",
          "维护档案/** export-ignore" in tx(".gitattributes")
          and "\n维护档案 export-ignore\n" in ("\n" + tx(".gitattributes") + "\n"),
          "两条 export-ignore 规则应在 .gitattributes 里")
