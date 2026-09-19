# -*- coding: utf-8 -*-
"""v1.61 补丁集：手机边界修正/规则优先级/语气去人设命名/阈值争议/授权分级/进度卡更新块/AI 正文草稿边界 ----
full_e2e.py 顺序片段 7/14（原第 1122–1286 行，由壳按序 exec，不单独运行）。
骨架名字（check/run/tx/rt/ROOT/TD/new_tmp…）与前面各段产出的变量都在同一个
命名空间里注入，与拆分前的扁平脚本语义一致；本文件的 if True 容器只为保持
原 4 空格缩进逐字节不变（if 块不产生作用域）。
"""
# --- 输出编码守卫：由壳 tests/full_e2e.py 统一处理，本片段不在管道外单独运行 ---
if True:  # 容器不产生作用域，缩进与拆分前完全一致
    # ---- v1.61 补丁集：手机边界修正/规则优先级/语气去人设命名/阈值争议/授权分级/进度卡更新块/AI 正文草稿边界 ----
    check("v161手机边界两处换电脑",
          all(s in skm for s in ("手机可全程完成", "手机可做一半", "必须回电脑", "手机起草 + 电脑定稿"))
          and "第 8 阶段只能做一半" not in skm)
    check("v161规则优先级入入口", "规则优先级" in skm and "coaching-protocol.md" in skm)
    for oldnm, newnm in (("gentle-sister", "gentle-patient"),
                         ("strict-ceo", "concise-direct"),
                         ("puppy", "lively-warm")):
        check("v161语气文件改名_" + newnm,
              (SK / "personalities" / (newnm + ".md")).exists()
              and not (SK / "personalities" / (oldnm + ".md")).exists())
    # 合并单文件是构建产物（.gitignore 已排除），过期由 validate.py 的同步检查抓，
    # 不在这里当源码问题报——否则一条"旧语气名"能把人引到完全错的方向。
    check("v161旧语气名清零(除版本历史)",
          all(oldnm not in p.read_text(encoding="utf-8")
              for p in SK.rglob("*.md")
              if p.name not in ("CHANGELOG.md", "README.md", "thesis-ai-coach-手机版.md")
              for oldnm in ("strict-ceo", "gentle-sister", "puppy")))
    s8 = tx("doubao-skill/stages/stage-8-analysis.md")
    check("v161统计阈值标争议",
          "判读标准说明" in s8 and s8.count("阈值因教材而异，结合导师意见") == 4)
    s4 = tx("doubao-skill/stages/stage-4-scale.md")
    check("v161授权分级本地化", "授权与使用许可（分级处理）" in s4 and "以本校文件为准" in s4)
    check("v161进度卡更新块", "进度卡更新块" in skp and "过闸日期" in skp
          and "进度卡更新块" in tx("core/coach-rules.md"))
    an = tx("doubao-skill/references/academic-norms.md")
    check("v161AI正文草稿边界",
          all(s in an for s in ("AI 可做与不可做", "可编辑的论文正文草稿", "报告风险", "不可直接提交")))
    check("v161完整版草稿边界同步",
          "正文可起草、不可代交" in tx("core/coach-rules.md")
          and "可编辑草稿" in tx("core/coaching-protocol.md")
          and "可编辑草稿" in tx("workflows/writing-guide.md"))
    mg2 = tx("doubao-skill/references/mobile-guide.md")
    check("v161手机截断提示", "只读到一半" in mg2 and "分步喂" in mg2)
    check("v161完整版获取校验", "核对版本号与校验值" in tx("doubao-skill/references/tools.md"))

    # paper_search 纯函数 + collect 注入假 fetcher（离线、确定性）
    try:
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))
        import paper_search as psearch
        ql = psearch.split_queries(["AI dependence;AI attachment", "chatbot reliance", "AI attachment"])
        check("v158多词拆分去重", ql == ["AI dependence", "AI attachment", "chatbot reliance"], str(ql))
        check("v158DOI规范化",
              psearch.normalize_doi("https://doi.org/10.1/X") == "10.1/x"
              and psearch.normalize_doi("doi: 10.2/Y") == "10.2/y")
        bk = {}
        r_a = {"title": "Same Paper", "doi": "10.9/z", "cited": 5, "source_api": ["OpenAlex"]}
        r_b = {"title": "Same Paper", "doi": "10.9/Z", "cited": 9, "source_api": ["Semantic Scholar"]}
        psearch.add_record(bk, r_a); psearch.add_record(bk, r_b)
        merged_one = bk.get(psearch.dedup_key(r_a))
        check("v158跨源DOI去重合并", len(bk) == 1 and int(merged_one["cited"]) == 9
              and set(merged_one["source_api"]) == {"OpenAlex", "Semantic Scholar"}, "n=%d" % len(bk))
        _cnt = {"i": 0}
        def _fake_fetcher(source, query, offset, per_page, year):
            if offset:
                return []  # 第二页空 → 该"来源×词"穷尽
            out = []
            for _ in range(50):
                _cnt["i"] += 1
                out.append({"title": "Paper %d" % _cnt["i"], "doi": "10.7/%d" % _cnt["i"],
                            "cited": 1, "year": 2024, "source_api": [source]})
            return out  # 50 < per_page(100) → 首页即穷尽
        recs_p, stats_p = psearch.collect(["q1", "q2"], ["openalex", "semantic"], 90, 100,
                                          fetcher=_fake_fetcher, sleeper=lambda s: None, verbose=False)
        check("v158collect凑够90且去重", len(recs_p) >= 90 and len(stats_p) >= 2, "n=%d" % len(recs_p))
        check("v158不足目标非静默", "未达到目标" in psrc and "补" in psrc)
    except Exception as _pe:
        check("v158paper_search离线纯函数", False, repr(_pe))

    # literature_cards 端到端（UTF-8-sig + GBK、跨文件重复 DOI、强制精读入选）
    card_tmp = new_tmp("cards")
    try:
        import literature_cards as lc
        f_utf8 = card_tmp / "cand_utf8.csv"
        lines = ["标题,作者,年份,期刊/会议,DOI,链接,被引数,摘要,来源API,命中检索词,检索日期"]
        for i in range(1, 13):
            forced = "（强制精读）" if i == 12 else ""
            cited = 0 if i == 12 else (200 - i * 10)
            year = 2000 if i == 12 else 2020 + (i % 6)
            ab = "" if i == 12 else "摘要内容 AI dependence %d" % i
            lines.append("文献标题%d%s,作者%d,%d,期刊%d,10.5/%d,https://doi.org/10.5/%d,%d,%s,OpenAlex,q1,2026-09-17"
                         % (i, forced, i, year, i, i, i, cited, ab))
        f_utf8.write_text("\n".join(lines), encoding="utf-8-sig")
        gbk_lines = ["标题,作者,年份,期刊,DOI,被引数,摘要,是否精读",
                     "文献标题12（强制精读）,作者12,2000,期刊12,10.5/12,0,,是",
                     "文献标题1,作者1,2021,期刊1,10.5/1,190,摘要内容 AI dependence 1,"]
        f_gbk = card_tmp / "org_gbk.csv"
        f_gbk.write_bytes("\n".join(gbk_lines).encode("gb18030"))
        out_html = card_tmp / "cards.html"
        rc_c = run(["tools/literature_cards.py", str(f_utf8), str(f_gbk),
                    "--focus", "AI dependence", "--top", "5", "--output", str(out_html)], 90)
        check("v158卡片CLI退出0", rc_c.returncode == 0 and out_html.exists(), (rc_c.stderr or "")[-240:])
        htxt = out_html.read_text(encoding="utf-8") if out_html.exists() else ""
        check("v158卡片单文件无外网",
              all(x not in htxt for x in ("<script src=", "<link", "@import", "url(http", "https://cdn")),
              "len=%d" % len(htxt))
        check("v158卡片移动友好与可追溯",
              all(x in htxt for x in ("width=device-width", "application/json", "modal", "⭐",
                                      "不构成论文引用依据", "textContent")))
        papers_c, probs_c = lc.load_papers([f_utf8, f_gbk])
        check("v158卡片读GBK且跨文件去重", not probs_c and len(papers_c) == 12,
              "n=%d problems=%s" % (len(papers_c), probs_c))
        focus_c = lc.parse_focus("AI dependence")
        star_idx_c = lc.pick_stars(papers_c, focus_c, 5)
        data_c, cats_c = lc.build_payload(papers_c, star_idx_c, focus_c)
        forced_c = [d for d in data_c if "强制精读" in d["title"]]
        n_star = sum(1 for d in data_c if d["star"])
        check("v158卡片强制精读入选且篇数受控",
              len(forced_c) == 1 and forced_c[0]["star"] is True and n_star == 5, "stars=%d" % n_star)
    except Exception as _ce:
        check("v158literature_cards端到端", False, repr(_ce))
    finally:
        shutil.rmtree(card_tmp, ignore_errors=True)

    # ---- v1.64 全流程三轮演练健壮性回归（详见 e2e-test 测试63）----
    # 1) 模型图 direct 二变量直接效应（旧版菜单引导 2 变量却只支持 3/4 变量，必报错）
    cg = "tools/chart_generator.py"
    d_png = new_tmp("v164chart") / "direct.png"
    r = run([cg, "-v", "AI依赖,NSSI", "-c", "0.32", "-t", "direct", "-o", str(d_png)])
    check("v164模型图direct二变量", r.returncode == 0 and d_png.exists() and d_png.stat().st_size > 5000,
          (r.stderr or "")[-200:])
    r = run([cg, "-v", "AI依赖,NSSI", "-t", "simple", "-o", str(d_png)])
    check("v164模型图误型引导direct",
          r.returncode != 0 and "direct" in (r.stdout or "") and "Traceback" not in (r.stderr or ""))
    # 2) scales 文件缺失/题项与数据不匹配必须硬失败，不得静默退化成全量/部分题分析
    v64 = new_tmp("v164scales")
    bad_sc = v64 / "bad_scales.txt"
    bad_sc.write_text("虚构量表:5=Z1,Z2,Z3\n", encoding="utf-8")
    miss_sc = v64 / "nope.txt"
    for tag, argv in [
        ("auto_stats", ["tools/auto_stats.py", str(TD / "demo_survey.csv"), "--scales", str(miss_sc)]),
        ("cleaner", ["tools/data_cleaner.py", str(TD / "demo_survey.csv"), "--scales", str(miss_sc)]),
    ]:
        r = run(argv, 200)
        check(f"v164 {tag} scales缺失硬失败",
              r.returncode != 0 and "不存在" in (r.stdout or "")
              and "Traceback" not in ((r.stdout or "") + (r.stderr or "")))
    for tag, argv in [
        ("auto_stats", ["tools/auto_stats.py", str(TD / "demo_survey.csv"), "--scales", str(bad_sc)]),
        ("cleaner", ["tools/data_cleaner.py", str(TD / "demo_survey.csv"), "--scales", str(bad_sc)]),
        ("item", ["tools/item_analysis.py", str(TD / "demo_survey.csv"), "--scales", str(bad_sc)]),
        ("htmt", ["tools/validity_cr_ave.py", "--htmt", str(TD / "demo_survey.csv"),
                  "--scales", str(bad_sc), "--boot", "30"]),
    ]:
        r = run(argv, 200)
        check(f"v164 {tag} 题项不匹配硬失败",
              r.returncode != 0 and "找不到" in ((r.stdout or "") + (r.stderr or ""))
              and "Traceback" not in ((r.stdout or "") + (r.stderr or "")))
    # 3) 清洗器数值参数给非数字/越界值：中文报错、非零退出（不要 argparse 英文 usage）
    r = run(["tools/data_cleaner.py", str(TD / "demo_survey.csv"), "--min-seconds", "abc"])
    check("v164清洗非数字参数中文报错",
          r.returncode != 0 and "数字" in (r.stdout or "") and "Traceback" not in (r.stderr or ""))
    r = run(["tools/data_cleaner.py", str(TD / "demo_survey.csv"), "--max-missing", "9"])
    check("v164清洗参数越界中文报错", r.returncode != 0 and "不合理" in (r.stdout or ""))
    # 4) 效应量工具参数校验失败必须非零退出（旧版只 print 叉号然后 return，进程仍 0）
    r = run(["tools/effect_size.py", "r", "--r", "0.3", "--n", "1"])
    check("v164效应量坏参非零退出", r.returncode != 0 and "n>3" in (r.stdout or ""))
    r = run(["tools/effect_size.py", "d", "--m1", "10", "--n1", "30", "--m2", "9", "--n2", "30"])
    check("v164效应量缺参非零退出", r.returncode != 0 and "sd1" in (r.stdout or ""))
    # 5) 文献整理：空文件/读取失败必须非零退出（旧版静默导出空整理表并报成功）
    empty_lit = v64 / "empty.txt"
    empty_lit.write_text("", encoding="utf-8")
    r = run(["tools/literature_organizer.py", str(empty_lit)])
    check("v164文献整理空文件硬失败", r.returncode != 0 and "0 篇" in (r.stdout or ""))
