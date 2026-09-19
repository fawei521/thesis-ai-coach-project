# -*- coding: utf-8 -*-
"""v1.83 记账归档：版本史/计划/用例台账的历史正文移入 维护档案/（git 追踪、不进发布包）。
full_e2e.py 顺序片段 15/15（由壳按序 exec，不单独运行）。
骨架名字与前面各段产出的变量都在同一命名空间里，与拆分前语义一致。"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    arch = ROOT / "维护档案"
    check("v183 三份历史档案已入库", all((arch / f).is_file() for f in [
        "CHANGELOG-历史详情-v1.0-v1.75.md", "PROJECT_PLAN-逐版优化叙事.md",
        "e2e-test-历史用例-测试1至54.md"]), str(sorted(p.name for p in arch.glob("*.md"))))
    chg83 = tx("CHANGELOG.md")
    rows83 = [l for l in chg83.splitlines() if re.match(r"^\| \*\*v[\d.]+\*\* \|", l)]
    check("包内 CHANGELOG 索引仍全量", len(rows83) >= 92 and "| **v1.0** |" in chg83
          and "维护档案/CHANGELOG-历史详情" in chg83, "rows=%d" % len(rows83))
    check("包内 CHANGELOG 已瘦身且关键事实未丢", len(chg83.splitlines()) < 300
          and "184→170 行，实计" in chg83 and "_发布包" in chg83,
          "lines=%d" % len(chg83.splitlines()))
    check("最新索引行主题不超过40字", len(rows83[0].split("|")[3].strip()) <= 40,
          "%d 字：%s" % (len(rows83[0].split("|")[3].strip()), rows83[0][:60]))
    pp83 = tx("PROJECT_PLAN.md")
    check("PROJECT_PLAN 不再重复逐版清单", len(pp83.splitlines()) < 320
          and "维护档案/PROJECT_PLAN-逐版优化叙事" in pp83
          and not re.search(r"^## .、v1\.\d+ 优化", pp83, re.M), "lines=%d" % len(pp83.splitlines()))
    et83 = tx("tests/e2e-test.md")
    et_arch = (arch / "e2e-test-历史用例-测试1至54.md").read_text(encoding="utf-8")
    # 用例编号带字母后缀（测试14b、14c-2），只取 \d+ 会把它们都算成 14 → 判成"重复"。
    # 真正要锁的是：索引表列出的每个编号，正文恰好存在一处（包内或档案），不重不漏。
    lab_body = (re.findall(r"^## 测试([^：:]+)[：:]", et83, re.M)
                + re.findall(r"^## 测试([^：:]+)[：:]", et_arch, re.M))
    lab_index = [x.strip() for x in re.findall(r"^\| 测试([^ |]+) \|", et83, re.M)]
    dup = sorted({x for x in lab_body if lab_body.count(x) > 1})
    check("e2e 用例索引与正文一一对应（不重不漏）",
          sorted(lab_body) == sorted(lab_index) and not dup and len(lab_index) >= 78,
          "正文%d 索引%d 重复%s" % (len(lab_body), len(lab_index), dup or "无"))
    check("跨文档点名的测试编号仍能解析",
          all(str(n) in lab_index for n in (63, 64)) and "14b" in lab_index and "14c-2" in lab_index,
          "缺 ROADMAP/CHANGELOG 点名的编号")
    check("维护档案不进发布包", "维护档案/** export-ignore" in tx(".gitattributes"))
