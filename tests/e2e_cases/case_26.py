# -*- coding: utf-8 -*-
"""case_26 · 引导流程补漏（零起点／工具地图同源／12 阶段准入／紧急诊断补"没文献"）。

起因：审计发现六条"工具在包里、规则却没让 AI 在对的时机递出去"的缺口。
这一片把这些条各钉一道**真实不变量**（不是点名清单），每条都配阴性——尺子抓不到植入就等于没写。
"""
import re as _re26
import pathlib as _pl26

CR_MAIN = tx("core/coach-rules.md")
ERR_SHARD = tx("core/coach-rules/common-errors.md")
PLAY = tx("core/coach-rules/stage-playbook.md")
TOOLR = tx("core/coach-rules/tool-rules.md")
PROTO = tx("core/coaching-protocol.md")
MENU26 = "\n".join(tx("tools/" + p.name) for p in sorted((ROOT / "tools").glob("menu*.py")))
LIT = tx("workflows/literature-auto-search.md")
READ = tx("workflows/paper-reading-guide.md")
EMER = tx("core/coach-rules/emergency.md")
SK0 = tx("doubao-skill/stages/stage-0-init.md")
SK2 = tx("doubao-skill/stages/stage-2-literature.md")
SK3 = tx("doubao-skill/stages/stage-3-organize.md")
SKP = tx("doubao-skill/references/coaching-protocol.md")
BST = tx("tests/behavior-self-test.md")

# ---------- 一、工具地图只有一个来源：图形菜单注册表（隔壁会话在改 START.md，这一片不读它） ----------
def _undocumented(names, doc):
    """names: ['xxx.py']；返回 doc 里查不到登记的那几个（按脚本名去 .py 匹配）。"""
    return [n for n in sorted(names) if n[:-3] not in doc]

_out26 = sorted(p.name for p in (ROOT / "tools").glob("*.py")
                if "__main__" in (ROOT / "tools" / p.name).read_text(encoding="utf-8"))
check("补漏 对外脚本判据非空且不含实现模块（带 __main__ 才算对外）",
      len(_out26) >= 25 and not any(n.startswith("menu_") or n == "pptx_writer.py" for n in _out26),
      "%d 件：%s" % (len(_out26), _out26[:3]))
check("补漏 每个对外脚本都挂在图形菜单注册表上（加工具不挂菜单就判红）",
      not _undocumented(_out26, MENU26), "菜单里查无：%s" % _undocumented(_out26, MENU26))
check("补漏 上面那道尺不空转（植入一个没登记的脚本名必须被点出）",
      _undocumented(_out26 + ["ghost_tool_zz.py"], MENU26) == ["ghost_tool_zz.py"])

# ---------- 二、tool-rules 只给主题线，不再手抄名册 ----------
_LIT7 = ("paper_search.py", "literature_organizer.py", "literature_cards.py", "lit_fetch.py",
         "lit_verify.py", "kb_index.py", "kb_search.py")
check("补漏 tool-rules 不再抄名册、改为指向 START 与 menu 注册表",
      "名册不在这里抄" in TOOLR and "`START.md` 第五步" in TOOLR and "menu.py" in TOOLR)
check("补漏 文献七件在决策那一页点得到名（少一件即红）",
      not [n for n in _LIT7 if n not in TOOLR], "缺 %s" % [n for n in _LIT7 if n not in TOOLR])
check("补漏 tool-rules 写明学生那四句话对应文献这一摊",
      all(k in TOOLR for k in ("我没文献", "读不到全文", "这个数哪来的")))

# ---------- 三、主手册的错误枚举与分片标题同源、条数不写死 ----------
_titles26 = _re26.findall(r"^### 错误(\d+)：(.+)$", ERR_SHARD, _re26.M)
_ptr26 = [ln for ln in CR_MAIN.splitlines() if "先读 `core/coach-rules/common-errors.md`" in ln]
def _errors_off_list(pairs, pointer_line):
    return [t for _, t in pairs if t.split("（")[0] not in pointer_line]
check("补漏 分片里错误条目 ≥9 且主手册枚举逐条对齐",
      len(_titles26) >= 9 and len(_ptr26) == 1 and not _errors_off_list(_titles26, _ptr26[0]),
      "分片 %d 条｜指针行 %d 处｜不对齐 %s" % (len(_titles26), len(_ptr26), _errors_off_list(_titles26, _ptr26[0])))
check("补漏 主手册不再把错误条数写进标题（抄一次漂一次）",
      "## 八、常见错误处理" in CR_MAIN and "8个常见错误" not in CR_MAIN and "9个常见错误" not in CR_MAIN)
check("补漏 枚举对齐尺不空转（植入一条没进主手册的错误必须被点出）",
      _errors_off_list(_titles26 + [("99", "假装新增的一条错误")], _ptr26[0]) == ["假装新增的一条错误"])

# ---------- 四、12 阶段每段都有准入行（跳阶段先核对的那张表在完整版真实存在） ----------
def _stages_missing_admit(text):
    out = []
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        m = _re26.match(r"^### 阶段(\d+)", ln)
        if m:
            if not any(lines[j].startswith("- **准入**") for j in range(i + 1, min(i + 4, len(lines)))):
                out.append("阶段" + m.group(1))
    return out

_missing26 = _stages_missing_admit(PLAY)
check("补漏 完整版 12 阶段每段都写了准入行",
      not _missing26 and PLAY.count("### 阶段") == 12, "缺 %s／共 %d 段" % (_missing26, PLAY.count("### 阶段")))
_cut26 = PLAY.replace("- **准入**：问卷定稿（质量埋点齐）、开题已通过", "")
check("补漏 准入这尺不空转（抽掉阶段 7 那一行就要报缺）",
      _stages_missing_admit(_cut26) == ["阶段7"])
check("补漏 跳阶段那句要求指向的准入清单真的查得到",
      "先核对该阶段准入条件" in PROTO and "**准入**" in PLAY)

# ---------- 五、零起点这一支在四处都在 ----------
check("补漏 常见错误新增错误9（零起点没文献没头绪）",
      "### 错误9：零起点没文献没头绪" in ERR_SHARD and "零起点没文献没头绪" in _ptr26[0])
check("补漏 每轮必读的协议有一行接住“没文献没头绪”",
      "没文献、没头绪、什么都没开始" in PROTO)
check("补漏 阶段 2 准入把零起点学生领到正确的门",
      "一篇文献都没有" in PLAY and "从这里进，不是从写作进" in PLAY)
check("补漏 轻量版两侧同口径（阶段 0 卡点＋阶段 2 入口）",
      "完全没头绪" in SK0 and "没文献、没头绪" in SK2)

# ---------- 六、"可选"不等于"等学生开口"：主动递工具的义务 ----------
check("补漏 知网自动检索那一页写了 AI 的主动义务",
      "AI 的主动义务" in LIT and "“可选”不等于“等学生开口”" in LIT)
check("补漏 阶段卡与轻量版同口径（不等他开口／先讲成本收益再交他定）",
      "不等他开口" in PLAY and "先讲成本收益再交他定" in PLAY and "“可选”不等于“等他开口”" in SK2)

# ---------- 七、紧急模式补"没文献"这一支（两侧＋用例三处同源） ----------
check("补漏 紧急模式诊断枚举两侧都含没文献",
      "（没选题/没文献/没数据/没分析/没写/没改）" in CR_MAIN and "（没选题/没文献/没数据/没分析/没写/没改）" in SKP)
check("补漏 紧急分册写了没文献时先补半天检索、不直接进压缩综述",
      "卡点是“没文献”时" in EMER and "把空话写短一点" in EMER)
check("补漏 用例 T29 的预期与规则同一句（不再停在四条）",
      "（没选题/没文献/没数据/没分析/没写/没改）" in BST)

# ---------- 八、读不到全文先试第 26/27 项，再降级 ----------
check("补漏 阅读手册把“仅摘要”前面接上第 26/27 项",
      "第 26 项 `lit_fetch.py`" in READ and "第 27 项 `lit_verify.py`" in READ)
check("补漏 轻量版阶段 3 同口径（先探测再馆际互借）",
      "第 26 项探测公开全文" in SK3 and "第 27 项双源核验" in SK3)

# ---------- 九、规则也算功能：用例登记 + 尺子能判 ----------
check("补漏 行为用例登记了零起点这一支（T66 指向规则与尺）",
      "T66" in BST and "stuck_pressure" in BST and "错误9" in BST)
_ex26 = run(["tests/stuck_pressure.py"])
check("补漏 零起点尺跑通且植入各缺其应缺（末行须含“尺不空转”）",
      _ex26.returncode == 0 and "尺不空转" in (_ex26.stdout or ""), (_ex26.stdout or "")[-200:])
_b26 = (ROOT / "tests" / "stuck_pressure.py").read_bytes()
check("补漏 新增的尺子文件行尾单一（全 CRLF、无裸 LF）",
      _b26.count(b"\r\n") == _b26.count(b"\n"), "CRLF %d／换行 %d" % (_b26.count(b"\r\n"), _b26.count(b"\n")))
