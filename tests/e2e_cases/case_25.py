# -*- coding: utf-8 -*-
"""v1.99 的机检：文献知识库（卡片 Schema、只读检索器、清点对账、两侧镜像、菜单分母同源）。
full_e2e.py 顺序片段 25/25（由壳按序 exec，不单独运行）。
临时命名空间一律用 _h199* 前缀（片段与壳共用 globals，撞名会静默改掉后续片段环境）。
全程离线：检索与清点的判定直接跑真函数与临时夹具，不依赖网络。
"""
if True:
    import importlib.util as _il199

    def _load199(rel):
        spec = _il199.spec_from_file_location(rel.replace("/", "_")[:-3], ROOT / rel)
        mod = _il199.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    _d199 = new_tmp("v199")
    _ks199 = _load199("tools/kb_search.py")
    _ki199 = _load199("tools/kb_index.py")

    # ---------- 一、卡片 Schema：四格证据字段一件不能少 ----------
    _tpl199 = tx("templates/文献卡片模板.md")
    check("v199 卡片模板含引用四要素与取证栏",
          all(k in _tpl199 for k in ("逐字原文", "**位置**", "我读到哪一层", "学生核对过没有",
                                     "这个数属于谁", "题录核验状态")))
    check("v199 卡片模板写明只有摘要不能下结论",
          "只能当线索" in _tpl199 and "原文未报告" in _tpl199)
    # 示范数字必须是合成量表名：真量表配假 α 正是 v1.93 拦过的那类事故（模板随包发给学生 AI 读）
    check("v199 卡片模板的示例用合成量表名",
          "XYZQ-16" in _tpl199 and "CAIDS" not in _tpl199, "示例里出现了真实量表名配假数字")

    # ---------- 二、检索器：纯标准库、只读、中文二元切分、命中带行号 ----------
    _src199 = tx("tools/kb_search.py") + tx("tools/kb_index.py") + tx("tools/menu_kb.py")
    check("v199 知识库工具纯标准库",
          all(k not in _src199 for k in ("import requests", "import pandas", "import numpy",
                                         "import torch", "sentence_transformers", "import faiss")))
    # 不依赖 sqlite3：本机 _sqlite3 与解释器 DLL 冲突（2026-09-22 实测 ImportError），
    # 押在 FTS5 上等于把"学生机器跑不起来"交给构建细节。
    check("v199 检索器不用 sqlite3/FTS5", "sqlite3" not in _src199)
    check("v199 两个工具都只读（无任何写盘调用）",
          all(k not in tx("tools/kb_search.py") for k in ("write_text", "write_bytes", "open(", "mkdir")))
    check("v199 编码守卫无条件生效",
          'if hasattr(sys.stdout, "reconfigure"):' in tx("tools/kb_search.py")
          and "and not sys.stdout.isatty()" not in _src199)
    # BM25 参数与 Lucene/Elasticsearch/SQLite FTS5 三处默认值同源（k1=1.2 b=0.75），写死要有出处
    check("v199 BM25 参数为业界默认 1.2/0.75", "K1, B = 1.2, 0.75" in tx("tools/kb_search.py"))

    _tk199 = _ks199.tokenize
    check("v199 中文按二元切分（孤独感→孤独/独感）",
          "孤独" in _tk199("孤独感") and "独感" in _tk199("孤独感"))
    check("v199 落单中文字退出一元（Lucene CJKAnalyzer 同款）",
          "德" in _tk199("德 a"))
    check("v199 句尾标点不粘进词（否则英文整条线静默漏召回）",
          "rumination" in _tk199("predicted rumination.") and "rumination." not in _tk199("predicted rumination."))
    check("v199 连字符不续接：CAIDS 能命中 CAIDS-20",
          "caids" in _tk199("CAIDS-20"))

    # ---------- 三、真跑一遍：命中带行号、摘要卡被标切片级 ----------
    _kb199 = _d199 / "10-知识库"
    _kb199.mkdir(parents=True)
    (_kb199 / "L01_假例2025_甲.md").write_text(
        "| **我读到哪一层** | `全文PDF` |\n| **本地原文在哪** | `无` |\n"
        "| 学生核对过没有 | `已逐字比对原文` |\n\n- **逐字原文**：\n"
        '  > "The scale showed good internal consistency."\n- **位置**：3.2 节 表 2\n', encoding="utf-8")
    (_kb199 / "L02_假例2024_乙.md").write_text(
        "| **我读到哪一层** | `仅摘要` |\n| **本地原文在哪** | `无` |\n"
        "| 学生核对过没有 | `还没比对` |\n\n- **逐字原文**：\n"
        '  > "Loneliness predicted self-injury through rumination."\n', encoding="utf-8")
    _r199 = run(["tools/kb_search.py", "internal", "consistency", "--dir", str(_kb199)])
    check("v199 检索命中并报出文件名与行号",
          _r199.returncode == 0 and "L01_假例2025_甲.md" in _r199.stdout
          and "L6" in _r199.stdout.replace("  ", " "), (_r199.stdout or "")[-260:])
    _r199b = run(["tools/kb_search.py", "loneliness", "--dir", str(_kb199)])
    check("v199 摘要卡命中时输出切片级警告", "切片级" in _r199b.stdout, (_r199b.stdout or "")[-200:])
    check("v199 未核对卡命中时输出不算已核实", "不算已核实" in _r199b.stdout)
    _r199c = run(["tools/kb_search.py", "loneliness", "--dir", str(_kb199), "--full-only"])
    check("v199 --full-only 真的把摘要级卡挡在外面",
          "L02" not in _r199c.stdout and "0 命中" in _r199c.stdout, (_r199c.stdout or "")[-200:])
    # 阴性：0 命中必须说"不等于没有"，不许说"没有"（evidence-rigor 第四节的否定闸门）
    _r199d = run(["tools/kb_search.py", "睡眠质量", "--dir", str(_kb199)])
    check("v199 零命中的措辞是未命中而非没有",
          _r199d.returncode == 0 and "不等于库里没有" in _r199d.stdout)
    check("v199 库不存在时给指路而不崩",
          "菜单第 28 项" in run(["tools/kb_search.py", "任意词", "--dir", str(_d199 / "没有这个库")]).stdout)

    # ---------- 四、清点器：分档计数、缺项点名、坏链、与台账对账、只读 ----------
    _r199e = run(["tools/kb_index.py", "--kb", str(_kb199)])
    check("v199 清点按读到哪一层分档并计数",
          _r199e.returncode == 0 and "全文PDF" in _r199e.stdout and "仅摘要" in _r199e.stdout)
    check("v199 清点把不能下结论那档的边界写清楚",
          "不得输出结论级断言" in _r199e.stdout and "独立第二源" in _r199e.stdout)
    check("v199 清点点名缺项（夹具缺作者年份与位置）",
          "谁（作者+年份）" in _r199e.stdout, (_r199e.stdout or "")[-260:])
    _before199 = sorted((p.name, p.stat().st_size) for p in _kb199.iterdir())
    _r199f = run(["tools/kb_index.py", "--kb", str(_kb199), "--write"])
    _after199 = sorted((p.name, p.stat().st_size) for p in _kb199.iterdir() if p.name != "知识库索引.md")
    check("v199 --write 只新增索引一个文件、卡片零改动",
          _before199 == _after199 and (_kb199 / "知识库索引.md").is_file())
    check("v199 --strict 有缺项时返回失败码",
          run(["tools/kb_index.py", "--kb", str(_kb199), "--strict"]).returncode == 1)
    # 阴性：把一张卡补全后，--strict 必须放过它——否则这条尺是空转的
    (_kb199 / "L03_全例2023_丙.md").write_text(
        "| 作者与年份 | Doe (2023) |\n| 题名 | 全例 |\n| 题录核验状态 | `双源一致` |\n"
        "| **我读到哪一层** | `全文PDF` |\n| **本地原文在哪** | `无` |\n"
        "- **逐字原文**：\n  > \"ok\"\n- **位置**：1 节\n| 学生核对过没有 | `已逐字比对原文` |\n",
        encoding="utf-8")
    _miss199 = [ln for ln in run(["tools/kb_index.py", "--kb", str(_kb199)]).stdout.splitlines()
                if "L03" in ln]
    check("v199 补全的卡不再被点缺项（阴性：尺不空转）", _miss199 == [], str(_miss199))

    # ---------- 五、工作区接线：目录随包、学生内容不进包、措辞不写死个数 ----------
    check("v199 LAYOUT 已含 10-知识库", '"10-知识库"' in tx("tools/setup_workspace.py"))
    check("v199 占位说明随包（否则干净副本里该目录不存在，文档引用必判悬空）",
          (ROOT / "我的工作区/10-知识库/把文献卡片放这里.txt").is_file())
    import subprocess as _sp199
    _tracked199 = _sp199.run(["git", "-c", "core.quotepath=false", "ls-files", "--", "我的工作区"],
                             capture_output=True, text=True, encoding="utf-8").stdout
    check("v199 学生的知识库卡片不进仓库",
          not [x for x in _tracked199.splitlines()
               if x.startswith("我的工作区/10-知识库/") and x.endswith(".md")],
          "库里混进了 .md 卡片")
    _live199 = "\n".join([tx("tools/menu.py"), tx("QUICKSTART.md"), tx("START.md"),
                          tx("core/coach-rules/stage-playbook.md")])
    check("v199 目录个数不再被写死（九个目录这类说法已清）",
          "九个目录" not in _live199 and "9 个目录" not in _live199)

    # ---------- 六、菜单分母与项数同源（v1.99 加到 29 项时改了一次全部分母，写死必漂）----------
    _menu199 = "\n".join(tx("tools/" + p.name) for p in sorted((ROOT / "tools").glob("menu*.py")))
    _mn199 = tx("tools/menu.py")
    _n_item199 = _mn199.count('\n    ("')
    _dens199 = set(__import__("re").findall(r"【\d+/(\d+)】", _menu199))
    check("v199 菜单分母等于菜单项数（真实不变量，不是点名清单）",
          _dens199 == {str(_n_item199)}, "分母 %s／实际 %d 项" % (sorted(_dens199), _n_item199))
    check("v199 第28/29项已接线且落在独立分册",
          "【28/" in _menu199 and "【29/" in _menu199 and "menu_kb.py" in _mn199)

    # ---------- 六之二、"规则也算功能"：形制尺必须不空转（宪法第十条）----------
    _ex199 = run(["tests/kb_experiment.py"])
    check("v199 知识库形制尺跑通且植入全判红",
          _ex199.returncode == 0 and "尺不空转" in (_ex199.stdout or ""),
          (_ex199.stdout or "")[-260:])
    check("v199 形制尺量的是四件必备而非语气",
          all(k in tx("tests/kb_experiment.py") for k in ("先查库", "不升格", "出处可核", "不代签")))
    check("v199 尺自带否定线索（提一嘴卡片不等于查过库）",
          "NEG_A" in tx("tests/kb_experiment.py") and "就不查" in tx("tests/kb_experiment.py"))
    check("v199 行为用例 T61–T65 已续编",
          all(("| T6%d |" % n) in tx("tests/behavior-self-test.md") for n in (1, 2, 3, 4, 5)))

    # ---------- 七、规则两侧同步 + 入口指针 ----------
    _full199, _lite199 = tx("core/literature-kb.md"), tx("doubao-skill/references/literature-kb.md")
    for _kw199 in ("定位器", "独立第二源", "逐字比对原文", "用库阶梯", "冲突"):
        check("v199 两侧都写到：%s" % _kw199, _kw199 in _full199 and _kw199 in _lite199)
    check("v199 两侧都拒绝库越大越准这个直觉",
          "库越大越准" in _full199 and "库越大越准" in _lite199)
    check("v199 轻量版如实写明手机端跑不了脚本",
          "没有文件系统" in _lite199 and "粘" in _lite199)
    check("v199 入口文档点名新规则（否则 AI 根本不会去读）",
          "core/literature-kb.md" in tx("AGENTS.md") and "core/literature-kb.md" in tx("START.md")
          and "knowledge-base-setup.md" in tx("START.md"))
    check("v199 每轮门禁两侧都挂了勾",
          "本地文献库" in tdoc("core/coaching-protocol.md")
          and "先查库" in tdoc("doubao-skill/references/coaching-protocol.md"))
    check("v199 手机版单文件已含知识库页正文",
          "卡片是定位器，不是第二源" in tx("doubao-skill/thesis-ai-coach-手机版.md"),
          "忘了重跑 build_mobile_single.py")
    check("v199 乙档不重教安装、改为指向既有手册",
          "environment-setup.md" in tx("workflows/knowledge-base-setup.md")
          and "toolchain-guide.md" in tx("workflows/knowledge-base-setup.md"))
    check("v199 既有笔记模板已补三格缺口（一个知识点只留一处）",
          "少三格" in tx("workflows/toolchain-guide.md")
          and "文献卡片模板.md" in tx("workflows/toolchain-guide.md"))
    check("v199 隐私红线写进规则（自伤主题不走上传路线）",
          "青少年自伤" in _full199 and "上传" in _full199)
    check("v199 零依赖承诺未被破坏",
          "kb" not in tx("requirements.txt").lower())
