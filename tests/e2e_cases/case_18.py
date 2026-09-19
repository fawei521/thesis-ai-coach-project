# -*- coding: utf-8 -*-
"""case_18：轻量版 v1.5 口径追平（v1.89）＋ 轻量版点名的完整版能力必须真实存在。

盯两件事：
1. **追平不许回退**——本版补进轻量版的统计与开题口径（ω/HTMT/前提假设/校正/缺失机制/就绪度/24 问）逐条有字面量锚点；
2. **不许虚构完整版**——轻量版是"指引到完整版"的形态，一旦它点名的脚本或菜单编号对不上实物，
   学生照做就会失败。`consistency_check.py` 整目录跳过 doubao-skill，所以这活儿在这里补。
"""

_SK18 = ROOT / "doubao-skill"


def _skread(rel):
    p = _SK18 / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _menu_total():
    """从真实菜单标签【N/M】里数出菜单项数（不写死数字，改菜单不用来改这里）。"""
    labels = set()
    for f in ("menu.py", "menu_io.py", "menu_data.py", "menu_lit.py", "menu_thesis.py"):
        p = ROOT / "tools" / f
        if p.exists():
            labels |= {(int(a), int(b)) for a, b in re.findall(r"【(\d+)/(\d+)】",
                                                               p.read_text(encoding="utf-8"))}
    return labels


def _citation_problems(skill_text, tool_names, total):
    """轻量版正文里点名的完整版脚本与菜单编号，对不上实物就是问题（纯函数供阴性测试）。"""
    bad = []
    for name in set(re.findall(r"`([a-z][a-z0-9_]{3,})\.py`", skill_text)):
        if name in ("validate", "build_mobile_single"):
            continue                       # 轻量版自带
        if name not in tool_names:
            bad.append("幽灵脚本 " + name + ".py")
    for n in {int(x) for x in re.findall(r"菜单第 (\d+) 项", skill_text)}:
        if not 1 <= n <= total:
            bad.append("菜单编号越界 第 %d 项（实际共 %d 项）" % (n, total))
    return bad


# ---- 1. v1.5 追平的口径锚点 ----
_labels = _menu_total()
_totals = {t for _, t in _labels}
_maxn = max(_totals) if _totals else 0          # 菜单实际项数，从标签自己数
s6, s7, s8, s11 = (tx("doubao-skill/stages/stage-6-method.md"),
                   tx("doubao-skill/stages/stage-7-data.md"),
                   tx("doubao-skill/stages/stage-8-analysis.md"),
                   tx("doubao-skill/stages/stage-11-defense.md"))
tl = tx("doubao-skill/references/tools.md")
check("v189开题就绪度自检进阶段6（手机＋回电脑两条路）",
      all(k in s6 for k in ("就绪度自检", "缺项", "矛盾", "只报问题、不代写")))
check("v189就绪度入阶段6准出闸", "就绪度自检" in s6.split("六、准出检查")[1])
check("v189缺失机制与插补进阶段7",
      all(k in s7 for k in ("Little's MCAR", "多重插补", "FIML", "MNAR", "成列删除")))
check("v189现代信效度指标进阶段8",
      all(k in s8 for k in ("McDonald's ω", "HTMT", "CR 与 AVE", ".85", ".90", "√AVE")))
check("v189前提假设与校正进阶段8",
      all(k in s8 for k in ("Shapiro-Wilk", "Brown-Forsythe", "Welch", "Kline",
                            "Bonferroni", "Holm", "BH", "BY", "FWER", "FDR")))
check("v189配对效应量与回归诊断进阶段8",
      all(k in s8 for k in ("d_z", "rank-biserial", "Durbin-Watson", "残差")))
check("v189完整版工具链指引同步（菜单项数从标签里数）", "共 %d 项" % _maxn in tl
      and "开题就绪度自检" in tl and "GB/T 7714" in tl and "多重比较校正" in tl and "大纲排 PPT" in tl)
check("v189答辩24问口径修正且旧措辞清零",
      all(k in s11 for k in ("24 问", "7 类")) and "24 类高频" not in s11
      and all("24类" not in _skread("references/" + f) and "24 类高频" not in _skread("references/" + f)
              for f in ("stage-checklist.md", "mobile-guide.md", "faq.md")))
st = tx("doubao-skill/references/self-test.md")
st_nums = sorted(int(x) for x in re.findall(r"^\| T(\d+) \|", st, flags=re.M))
check("v189自测用例编号连续含T37-T43",
      st_nums == list(range(1, len(st_nums) + 1)) and all(n in st_nums for n in range(37, 44)),
      "n=%d tail=%s" % (len(st_nums), st_nums[-4:]))

# ---- 2. 轻量版点名的完整版能力必须真实存在（含阴性自测）----
check("v189菜单标签分母自洽且非零", _maxn > 0 and len(_totals) == 1, "分母集合=%s" % _totals)
_tools = {p.stem for p in (ROOT / "tools").glob("*.py")} | {p.stem for p in (ROOT / "tools" / "stats").glob("*.py")}
_all_skill = "".join(_skread(str(p.relative_to(_SK18)))
                     for p in _SK18.rglob("*.md")
                     if p.name not in ("CHANGELOG.md", "README.md", "thesis-ai-coach-手机版.md"))
_probs = _citation_problems(_all_skill, _tools, _maxn)
check("v189轻量版不虚构完整版脚本与菜单编号", not _probs, str(_probs))
_neg = _citation_problems(_all_skill + "\n用 `ghost_tool_xyz.py` 跑，或点菜单第 99 项\n", _tools, _maxn)
check("v189幽灵引用尺子抓得到（阴性）",
      any("幽灵脚本" in x for x in _neg) and any("越界" in x for x in _neg), str(_neg))
check("v189阴性输入不误伤", not _citation_problems("只看 `validate.py` 与 `menu.py`", _tools, _maxn))

# ---- 3. 同一文件内不得混用行尾 ----
# 起因：full_e2e.py 里有一个裸 CR，Python 认它当换行（case_17 一直在跑），但 sed/grep/编辑器
# 会把 case_16 与 case_17 显示成同一行——谁编辑那行就会把 case_17 的注册静默摘掉，断言少一片还不报警。
def _mixed_eol(data):
    """返回 (CRLF 数, 裸 LF 数, 裸 CR 数)——三种分隔符同时出现即为混用。"""
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


_EOL_EXT = {".py", ".md", ".txt", ".json", ".yaml", ".html", ".bat"}
_mixed = []
for _p in ROOT.rglob("*"):
    if not _p.is_file() or _p.suffix.lower() not in _EOL_EXT:
        continue
    if any(x in _p.parts for x in (".git", "__pycache__", "test-data", "我的工作区")):
        continue                          # 学生工作区由学生自己的编辑器决定，不归包管
    _c, _l, _r = _mixed_eol(_p.read_bytes())
    if (_c and (_l or _r)) or (_l and _r):
        _mixed.append(str(_p.relative_to(ROOT)))
check("v189同一文件内行尾单一", not _mixed, str(_mixed[:4]))
_n1, _n2 = _mixed_eol(b"a\r\nb\rc\n"), _mixed_eol(b"a\nb\r\n")
check("v189行尾尺子算得准（阴性）", _n1 == (1, 1, 1) and _n2 == (1, 1, 0), "%s %s" % (_n1, _n2))
