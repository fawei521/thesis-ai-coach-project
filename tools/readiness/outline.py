# -*- coding: utf-8 -*-
"""PPT 汇报大纲口径（`templates/opening-ppt-outline.md` 那一套，proposal-guide 第四节）。

页数、每页要点数这类规则**只在汇报大纲上成立**——报告体正文没有"页"，拿它去判会假报
"现在 16 页，口径是 8-12 页"（P8 要修的那条：报告体走的是另一套节次口径）。
"""
import re

from .common import check_sections, parse_pages

# PPT 汇报八项（proposal-guide.md 第四节）：与报告体**不是一套**，
# 拿报告口径去判 PPT 大纲会假报"参考文献没找到"（v1.86 真人走查 S4）。
SECTIONS_PPT = [("封面（题目/姓名/导师/日期）", ["副标题", "汇报人", "指导教师"]),
                ("选题背景", ["背景"]),
                ("文献综述与研究空白", ["综述", "空白"]),
                ("研究模型与假设", ["模型", "假设"]),
                ("研究方法（对象/量表/分析）", ["方法", "对象", "量表", "分析"]),
                ("创新点", ["创新"]),
                ("进度安排", ["进度"]),
                ("致谢/请老师指正", ["指正", "致谢", "谢谢"])]


def kind_checks(text):
    """本形态特有的缺项与提示；跨形态都成立的在 common.shared_checks。"""
    body = text.replace("\n", " ")
    want = check_sections(SECTIONS_PPT, "汇报八项", "第四节", "项", body)
    got = []
    yrs = [int(y) for y in re.findall(r"\b(20[0-2]\d)\b", text)]
    if yrs and sum(1 for y in yrs if y >= 2021) * 2 < len(yrs):
        got.append("出现的年份里近五年（2021 及以后）偏少：%d 处中只有 %d 处——综述以近五年为主"
                   % (len(yrs), sum(1 for y in yrs if y >= 2021)))
    pages = [p for p in parse_pages(text) if p["lines"] or "页" in p["t"]]
    npg = len(re.findall(r"第\s*\d+\s*页", text)) or len(pages)   # 优先按"第N页"数：模板自带的 ## 标题页混进来会多数一页
    if npg < 8 or npg > 12:
        got.append("现在 %d 页，口径是 8-12 页（proposal-guide 第四节）——多了念不完，少了讲不清" % npg)
    fat = [p["t"] for p in pages
           if len([l for l in p["lines"] if l.strip().startswith(("-", "|"))]) > 7
           or any(len(l) > 46 for l in p["lines"] if l.strip().startswith("-"))]
    if fat:
        got.append("这几页要点偏多偏长（每页一个核心信息、字少图多）：%s" % "、".join(fat[:6]))
    return want, got
