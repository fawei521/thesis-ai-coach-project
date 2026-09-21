# -*- coding: utf-8 -*-
"""就绪度自检的共用件：默认路径、读进度卡、判材料形态、两类材料都要过的通用检查。

PPT 大纲专属口径在 `outline.py`，报告体专属口径在 `report.py`。
本模块的检查一律是"两份材料都成立"的那部分——把只在一类材料里成立的规则写进这里，
就会对另一类假报（v1.86 真人走查 S4 的教训：拿报告八节去判 PPT 大纲）。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEF_OUTLINE = ROOT / "我的工作区" / "05-开题报告" / "我的开题大纲.md"
DEF_PROGRESS = ROOT / "我的工作区" / "我的论文进度.md"

# 进度卡字段 → 内部标签；值里留着" / "说明是模板选项、按未填处理
FIELDS = [("论文题目", "TITLE"), ("研究类型", "TYPE"), ("自变量", "X"), ("因变量", "Y"),
          ("中介变量 M1", "M1"), ("中介变量 M2", "M2"), ("调节变量", "W"),
          ("研究假设", "HYP"), ("计划答辩时间", "DEF")]
VARNAME = {"X": "自变量", "Y": "因变量", "M1": "中介变量1", "M2": "中介变量2", "W": "调节变量"}
CAUSAL = ["导致", "证明了", "引起", "决定了"]
CROSS = ["横断", "一次性施测", "同一时间", "横截面"]
MINOR = ["青少年", "未成年", "初中生", "高中生", "中学生", "小学生"]
CONSENT = ["知情同意", "监护人", "家长同意", "父母同意", "自愿", "匿名"]
TOOLISH = re.compile(r"(tools/\w+\.py|\w+\.py\b|auto_stats|outline_to_ppt|sample_size|paper_search"
                     r"|menu\.py|启动工具箱|--[a-z][a-z-]+)")


def clean_value(val):
    """把"- 字段：值"里的值净化成可比对的**核心词**：真人会写 `非自杀性自伤（NSSI）`、`暂无，待定`、
    `**自然**（走查时选的）`，整串拿去和大纲做子串比对必然假报"两边对不上"（v1.86 真人走查 S2）。"""
    v = val.strip().replace("**", "").replace("`", "").lstrip("*").strip()
    v = re.split(r"[（(—、；;，]| {2,}", v, maxsplit=1)[0].strip()
    if not v or v in ("无", "暂无", "暂定", "待定", "N/A", "na", "-") or " / " in val or "默认" in val:
        return ""
    return v


def parse_progress(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s*([^：:]+)[：:]\s*(.*)$", line)
        if not m:
            # 假设常写成缩进子条目（"- 研究假设：" 下面 "- H1 …"）：冒号后为空也要认成"已列条目"，
            # 否则会漏报"假设没写进大纲"（v186 真人走查 S3）。
            if "HYP" in out and not out["HYP"] and re.match(r"^\s+[-*]\s*H\d+\b", line):
                out["HYP"] = "已列条目"
            continue
        key, val = m.group(1).strip(), m.group(2).strip()
        for zh, tag in FIELDS:
            if zh in key and tag not in out:
                out[tag] = clean_value(val)
    return out


def parse_pages(text):
    """按标题切页；`> 讲稿：` 行与列表行分开算。"""
    pages, cur = [], {"t": "（封面/开头）", "lines": []}
    for ln in text.splitlines():
        if re.match(r"^#{1,4}\s", ln):
            pages.append(cur)
            cur = {"t": ln.lstrip("#").strip(), "lines": []}
        else:
            cur["lines"].append(ln)
    pages.append(cur)
    return pages


def detect_kind(text):
    """PPT 汇报大纲带"第N页"；其余按报告体（templates/proposal-template.md 那一套）核。"""
    return "ppt" if re.search(r"第\s*\d+\s*页", text) else "report"


def check_sections(secs, label, guide_sec, unit, scan):
    """secs 里任一关键词都没在 scan 中命中的节 → 缺项。scan 决定"去哪儿找"：
    PPT 给全文，报告体只给**标题**（正文里偶然出现"方法"两个字不算写了研究方法节）。"""
    return [("缺项", "%s里的「%s」没找到——按 proposal-guide %s补上这一%s" % (label, name, guide_sec, unit))
            for name, keys in secs if not any(k in scan for k in keys)]


def shared_checks(text, prog, base=None):
    """两类材料都成立的缺项/矛盾/风险，加上通用提示；返回 (want, got)。"""
    want, got = [], []
    base = Path(base) if base else DEF_OUTLINE.parent   # 图片按"材料自己所在目录"解析
    body = text.replace("\n", " ")
    lines = text.splitlines()
    # 占位符＝模板留给你写的那一格（【你来写…】【你填】【待填】【__】或空【】）；
    # 核验类标注（【缺：卷号】【预印本】【DOI 串号…】）不是"没填"，是"查到了但缺字段"——
    # 混在一起数会把一份内容完整的报告判成"占位没换"，也让人找不到真正要写的那几处（v1.98 实测各多算 16 处）。
    slot = re.compile(r"【\s*(你来|你填|你定|你选|你答|填|待|请|_{2,}|】)")
    ph = sum(len(slot.findall(l)) for l in lines)
    note = sum(l.count("【") for l in lines) - ph
    _mk = [i + 1 for i, l in enumerate(lines) if "[需核实]" in l]
    _tri = [i + 1 for i, l in enumerate(lines) if "[未查到]" in l or "[推断]" in l]
    if ph:
        tally, cur = {}, "（封面/开头）"
        for ln in lines:                       # 按页分组，零基础同学才对得上是哪一页要补（S6）
            if re.match(r"^#{1,4}\s", ln):
                cur = ln.lstrip("#").strip()[:14]
            if slot.search(ln):
                tally[cur] = tally.get(cur, 0) + len(slot.findall(ln))
        want.append(("缺项", "还有 %d 处【】没换成你自己的内容，按页看：%s——占位没换就交是硬伤"
                     % (ph, "、".join("%s %d 处" % (k, v) for k, v in list(tally.items())[:8]))))
    if _mk:
        want.append(("缺项", "第 %s 行还留着 [需核实]——回原文补上「逐字原文＋第几节/哪张表」，补不上就删掉这条（core/evidence-rigor.md）" % "、".join(str(i) for i in _mk[:6])))
    if note:
        got.append("另有 %d 处【…】是**核验类标注**（如【缺：卷号、页码】），不是模板没填；"
                   "但带缺字段的条目同样不得进正式稿——补齐或删条，二选一。" % note)
    if _tri:
        got.append("第 %s 行带着 [未查到]/[推断] 三态标记：这样写是**合规**的（空着比填一个看着像的数好），"
                   "但答辩要能一句话说清为什么空着（core/evidence-rigor.md 第〇节）。"
                   % "、".join(str(i) for i in _tri[:6]))
    imgs = list(dict.fromkeys(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
                            + re.findall(r"([^\s（）()]+\.png)", text)))
    if "模型" in body and not imgs:
        want.append(("缺项", "写了研究模型却没有模型图——假设与路径要靠图讲清（菜单第6项可生成）"))
    for im in imgs:
        if not any((d / im).is_file() for d in (base, ROOT, ROOT / "我的工作区")):
            want.append(("缺项", "大纲里引的图「%s」找不到，排成 PPT 会是空框" % im))
    for tag, zh in (("TITLE", "论文题目"), ("TYPE", "研究类型")):
        if prog and not prog.get(tag):
            want.append(("缺项", "进度卡的「%s」还没填——换 AI 接不上，也没法和大纲对账" % zh))
    for tag in ("X", "Y", "M1", "M2", "W"):
        v = (prog or {}).get(tag, "")
        if v and v not in text:
            want.append(("矛盾", "进度卡里的 %s=%s 在大纲中找不到，两边口径不一致（补进大纲或改进度卡，别留两套）"
                         % (VARNAME[tag], v)))
    if (prog or {}).get("DEF") and not re.search(r"\d{1,2}\s*月", body):
        want.append(("矛盾", "进度卡写了计划答辩时间（%s），大纲的进度安排里没有对应月份" % prog["DEF"]))
    if (prog or {}).get("HYP") and "H1" not in text.replace("h1", "H1"):
        want.append(("矛盾", "进度卡写了研究假设，大纲里却没有 H1/H2 编号——假设要一条条编号才能和模型图的箭头对上"))
    if any(w in body for w in MINOR) and not any(c in body for c in CONSENT):
        want.append(("风险", "对象涉及未成年人却没写知情同意/监护人同意——伦理硬伤，见 psychology/ethics.md"))
    if any(c in body for c in CROSS):
        # 只抓"导致/证明"这类强因果词；"…对…的影响"是 proposal-guide 第六节认可的标准句式，抓它=工具和自己教的口径打架
        hits = sorted({w for w in CAUSAL if w in body})
        if hits:
            want.append(("风险", "设计是横断（一次施测），却出现强因果措辞：%s。评审常问「横断能说明因果吗」，"
                         "建议改说“预测/关联”并承认局限（proposal-guide 第五节）" % "、".join(hits)))
    bad = sorted({m.group(0) for ln in lines if not ln.strip().startswith(">")
                  for m in [TOOLISH.search(ln)] if m})
    if bad:
        want.append(("风险", "正文里混进了工具脚本名/开关：%s。正式开题文本只写 SPSS/JASP/PROCESS/G*Power 等"
                     "公认软件，脚本只是你自己预览核对用的（proposal-guide 第三节的硬口径）" % "、".join(bad[:8])))
    if not re.search(r"\d{3,}\s*(份|人)|N\s*=|样本量\s*[:：]?\s*\d{3}", body):
        got.append("没看到样本量数字（份/人/N=）——用菜单第8项估算最小 N、叠加无效卷冗余，把依据写进方法")
    if "量表" in body and not re.search(r"\d+\s*题|信度|α|Cronbach", body):
        got.append("写了量表但没写题数/信度——老师会问“这个量表信效度怎么样”，每个量表补题数、维度、α、出处")
    return want, got
