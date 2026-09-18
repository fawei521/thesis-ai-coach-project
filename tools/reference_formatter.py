#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参考文献格式化工具（GB/T 7714-2015 顺序编码制）
================================================
吃结构化题录 CSV（paper_search 导出、literature_organizer 整理表，或本工具
--save-template 生成的模板），输出可直接粘进论文的 [1][2][3] 编号参考文献。

支持文献类型：期刊[J]、专著[M]、学位论文[D]、会议论文[C]、报纸[N]、电子资源[EB/OL]；
中文作者超过 3 人补"等"、英文作者补"et al"；欧美著者按国标"姓全大写、名缩写不带点"。
纯 Python 标准库实现，不联网、不生成文献（工具只做格式化，题录必须真实、自己读过）。

用法：
  python tools/reference_formatter.py 文献.csv
  python tools/reference_formatter.py 文献.csv --fullwidth          # 用全角标点（．，：）
  python tools/reference_formatter.py 文献.csv --name-case 2025     # 外国作者姓氏首字母大写（GB/T 7714-2025 口径）
  python tools/reference_formatter.py --save-template 参考文献模板.csv
"""
import argparse
import csv
import io
import os
import re
import sys
from datetime import date
from pathlib import Path

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与其他工具同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- 表头同义词
HEADER_ALIASES = {
    "title":      ["标题", "题名", "题目", "文献标题", "title", "article title", "article"],
    "authors":    ["作者", "著者", "作者们", "author", "authors", "creator"],
    "year":       ["年份", "出版年", "年", "日期", "year", "date", "publication year"],
    "journal":    ["期刊/会议", "刊名/论文集/报纸", "期刊", "刊名", "期刊名", "来源", "出处", "journal", "source", "journal name"],
    "volume":     ["卷", "卷次", "volume", "vol", "vol."],
    "issue":      ["期", "期次", "issue", "number", "no"],
    "pages":      ["页码", "起止页", "页数", "pages", "page", "pp"],
    "type":       ["类型", "文献类型", "type", "reference type"],
    "publisher":  ["出版社", "出版者", "publisher"],
    "place":      ["出版地", "出版地点", "place", "location"],
    "institution": ["学位单位", "授予单位", "保存单位", "出版社/学位单位", "学校", "院校", "institution", "school", "university"],
    "conference": ["会议名", "论文集", "会议", "conference", "proceedings"],
    "newspaper":  ["报纸", "报纸名", "newspaper"],
    "url":        ["链接", "网址", "获取路径", "访问路径", "url", "link"],
    "doi":        ["DOI", "doi", "数字对象标识符"],
    "update":     ["更新日期", "修改日期", "发布日期", "updated", "update date"],
    "source_text": ["原文出处", "原始出处", "citation", "raw citation"],
}

TEMPLATE_HEADERS = ["类型", "作者", "题名", "年份", "刊名/论文集/报纸", "卷", "期", "页码",
                    "出版地", "出版社/学位单位", "URL", "DOI", "更新日期"]

TYPE_ALIASES = {
    "J": ["期刊", "杂志", "journal", "article", "j/ol", "[j]"],
    "M": ["专著", "图书", "书籍", "著作", "book", "monograph", "[m]"],
    "D": ["学位论文", "硕博论文", "毕业论文", "硕士论文", "博士论文", "thesis", "dissertation", "[d]"],
    "C": ["会议", "论文集", "会议论文", "conference", "proceedings", "[c]"],
    "N": ["报纸", "新闻", "newspaper", "[n]"],
    "EB": ["电子", "网页", "网站", "网络", "online", "web", "eb/ol", "[eb"],
}

# ================================================================ 作者解析
_ETAL_RE = re.compile(r"[，,、;；]?\s*(等|et\.?\s*al\.?)\s*\.?[。.]?\s*$", re.IGNORECASE)
_APA_RE = re.compile(r"(?:^|[,&]\s*)([A-Za-z][A-Za-z'’\-]*)\s*,\s*((?:[A-Z]\.\s*)+|(?:[A-Z]\.\s*)*[A-Z](?=\s*[,&]|\s*$))")


def _is_cjk(s):
    return bool(re.search(r"[\u4e00-\u9fff]", s))


def _parse_western_chunk(chunk):
    """把一个作者块解析成 (surname, initials)。兼容三种常见写法：
    'HENSELER J'/'Henseler J'（国标式，姓在前）、'J Henseler'（名缩写在前）、
    'Jörg Henseler'（全名，取最后一个词为姓、其余取首字母）。"""
    toks = chunk.replace(".", " ").replace(",", " ").split()
    toks = [t for t in toks if t]
    if len(toks) == 1:
        return toks[0], ""
    if all(len(t) == 1 for t in toks[1:]):          # 姓 + 缩写名
        return toks[0], "".join(toks[1:])
    if all(len(t) == 1 for t in toks[:-1]):         # 缩写名 + 姓
        return toks[-1], "".join(toks[:-1])
    if toks[0].isupper() and len(toks[0]) > 1:      # 全大写姓在前（全名其余部分）
        return toks[0], "".join(t[0] for t in toks[1:] if t[0].isalpha())
    return toks[-1], "".join(t[0] for t in toks[:-1] if t[0].isalpha())  # 全名：姓在最后


def parse_authors(raw):
    """返回 (作者列表, 原文是否已含等/et al 截断标记)。每个作者为 ('c', 姓名) 或 ('w', 姓, 首字母串)。"""
    s = (raw or "").strip().strip("。.").strip()
    if not s:
        return [], False
    had_etal = bool(_ETAL_RE.search(s))
    s = _ETAL_RE.sub("", s).strip()
    # 机构作者整段保留：含中文且无逗号分号顿号（如"世界卫生组织"）
    chunks = None
    if re.search(r"[;；]", s):
        chunks = re.split(r"[;；]", s)
    elif "、" in s:
        chunks = s.split("、")
    elif "&" in s:
        chunks = re.split(r"\s*&\s*", s)
    elif not re.search(r"[A-Za-z]", s):
        chunks = re.split(r"[，,]", s)               # 纯中文：逗号即分隔
    else:
        # APA 式 "Wang, Y., Li, M., Chen, X."：姓, 缩写名 成对出现
        apa = list(_APA_RE.finditer(s))
        if len(apa) >= 2:
            chunks = [m.group(0) for m in apa]
        else:
            chunks = re.split(r"[，,]", s)
    authors = []
    for ch in chunks:
        ch = ch.strip().strip("。.").strip()
        if not ch:
            continue
        if _is_cjk(ch):
            authors.append(("c", ch))
        else:
            surname, initials = _parse_western_chunk(ch)
            authors.append(("w", surname, initials))
    return authors, had_etal


def format_surname(surname, name_case):
    if name_case == "2025":
        return surname[0].upper() + surname[1:].lower()
    return surname.upper()


def format_authors(raw, name_case="2015", max_list=3):
    """按 GB/T 7714 著者规则格式化：1-3 个全列，≥4 个列前 3 个加"等/et al"。"""
    authors, had_etal = parse_authors(raw)
    if not authors:
        return "", False
    use_cjk_etal = any(a[0] == "c" for a in authors[:max_list]) or _is_cjk(raw or "")
    tail = "等" if use_cjk_etal else "et al"
    parts = []
    for a in authors[:max_list]:
        if a[0] == "c":
            parts.append(a[1])
        else:
            ini = " ".join(a[2]) if a[2] else ""
            parts.append((format_surname(a[1], name_case) + (" " + ini if ini else "")).strip())
    truncated = had_etal or len(authors) > max_list
    if truncated:
        parts.append(tail)
    return ", ".join(parts), truncated


# ================================================================ 出处解析
_TAIL_RE = re.compile(
    r"(?P<journal>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z\s&\-\.]+?)"
    r"[，,]\s*(?P<year>(?:19|20)\d{2})[，,]\s*"
    r"(?P<vol>\d+)\s*\((?P<issue>\d+)\)\s*[:：]\s*(?P<pages>[\dA-Za-z–—\-]+)")
_APA_PREFIX_RE = re.compile(
    r"^(?:[A-Z][A-Za-z'’\-]*\s*,\s*[A-Z]\.\s*(?:[,&]\s*)?)+")
_CJK_PREFIX_RE = re.compile(r"^[\u4e00-\u9fff,，、\s]{2,40}[.．]\s*")


def parse_source_tail(text):
    """从'心理科学, 2025, 48(3): 123-130'类自由文本尾部抽取刊名年卷期页。"""
    m = _TAIL_RE.search(text or "")
    if not m:
        return {}
    journal = m.group("journal").strip(" .，,")
    # 英文自由文本里题名与刊名间只有句点，取最后一个 ". " 之后才是刊名
    if ". " in journal:
        journal = journal.split(". ")[-1].strip()
    return {"journal": journal,
            "year": m.group("year"), "volume": m.group("vol"),
            "issue": m.group("issue"), "pages": m.group("pages")}


def clean_title_from_source(text):
    """organizer 整理表的'原文出处'常是'作者. 题名. 刊名, 年, 卷(期): 页'，
    去掉作者前缀与刊名尾部，尽量还原纯题名。"""
    t = (text or "").strip().strip("。.")
    m = _TAIL_RE.search(t)
    if m:
        journal = m.group("journal").strip(" .，,")
        if ". " in journal:
            journal = journal.split(". ")[-1].strip()
        idx = t.rfind(journal)          # 以刊名实际位置为界，避免题名被并入刊名段
        if idx >= 0:
            t = t[:idx].rstrip(" .，,")
    t = _APA_PREFIX_RE.sub("", t).strip()
    t = _CJK_PREFIX_RE.sub("", t).strip()
    if ". " in t:                       # 兜底：作者块残留时取最后一段
        cand = t.split(". ")[-1].strip(" .，,。")
        if len(cand) >= 4:
            t = cand
    return t.strip(" .，,。")


# ================================================================ 读表与字段映射
def read_csv_rows(path):
    """多编码读 CSV，返回 (headers, 行字典列表)；失败返回 None。"""
    last_err = None
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            with io.open(path, "r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                rows = [r for r in reader]
            break
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
    else:
        print(f"✗ 文件编码无法识别（已试 UTF-8/GBK）：{last_err}")
        return None
    if not rows:
        return [], []
    headers = [h.strip() for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        out.append({headers[i]: (r[i].strip() if i < len(r) else "") for i in range(len(headers))})
    return headers, out


def map_columns(headers):
    """按同义词把实际表头映射到标准字段，返回 {字段: 列名}。"""
    lower = {h.strip().lower(): h for h in headers}
    mapped = {}
    for field, aliases in HEADER_ALIASES.items():
        for a in aliases:
            if a.lower() in lower:
                mapped[field] = lower[a.lower()]
                break
    return mapped


def g(row, colmap, field):
    return (row.get(colmap[field], "") if field in colmap else "").strip()


def normalize_type(raw, rec):
    """显式类型列优先；否则按字段推断。返回 J/M/D/C/N/EB/None。"""
    t = (raw or "").strip().lower()
    if t:
        for code, aliases in TYPE_ALIASES.items():     # 第一遍：精确命中
            if t == code.lower() or t in aliases:
                return code
        # 第二遍：子串包含，取命中别名最长的类型（newspaper article → N 而非 J）
        best_code, best_len = None, 0
        for code, aliases in TYPE_ALIASES.items():
            hit = max((len(a) for a in aliases if a in t), default=0)
            if hit > best_len:
                best_code, best_len = code, hit
        if best_code:
            return best_code
    if rec.get("journal"):
        return "J"
    if rec.get("institution"):
        return "D"
    if rec.get("conference"):
        return "C"
    if rec.get("newspaper"):
        return "N"
    if rec.get("publisher"):
        return "M"
    if rec.get("url"):
        return "EB"
    return None


# ================================================================ 著录渲染
def _punct(fullwidth):
    if fullwidth:
        return {"dot": "．", "comma": "，", "colon": "：", "sep": "．"}
    return {"dot": ".", "comma": ", ", "colon": ": ", "sep": ". "}


def _year_vol_issue(journal, year, vol, issue, pages, P):
    """期刊出处段：刊名, 年, 卷(期): 页（卷期缺失时按国标退化；全角模式逗号同步转换）。"""
    tail = journal
    if vol and issue:
        tail += P["comma"] + f"{year}{P['comma']}{vol}({issue})"
    elif issue:
        tail += P["comma"] + f"{year}({issue})"
    elif vol:
        tail += P["comma"] + f"{year}{P['comma']}{vol}"
    else:
        tail += P["comma"] + str(year)
    if pages:
        tail += P["colon"] + pages
    return tail


def render_ref(rec, name_case, fullwidth, access_date):
    """返回 (著录字符串不含编号, 缺失项说明列表)。"""
    P = _punct(fullwidth)
    missing = []
    authors_txt, _ = format_authors(rec.get("authors", ""), name_case)
    title = rec.get("title", "")
    typ = rec.get("type")
    year = rec.get("year", "")
    doi = rec.get("doi", "")
    url = rec.get("url", "")

    def marker(field):
        missing.append(field)
        return f"【待补：{field}】"

    head = (authors_txt + P["sep"]) if authors_txt else ""
    if not title:
        title = marker("题名")

    if typ == "J":
        journal = rec.get("journal") or marker("刊名")
        if not year:
            year = marker("年份")
        body = _year_vol_issue(journal, year, rec.get("volume", ""), rec.get("issue", ""),
                               rec.get("pages", ""), P)
        line = f"{head}{title}[J]{P['sep']}{body}{P['dot']}"
    elif typ == "M":
        pub = rec.get("publisher") or marker("出版社")
        if not year:
            year = marker("年份")
        place = (rec.get("place", "") + P["colon"]) if rec.get("place") else ""
        line = f"{head}{title}[M]{P['sep']}{place}{pub}{P['comma']}{year}{P['dot']}"
    elif typ == "D":
        inst = rec.get("institution") or marker("学位单位")
        if not year:
            year = marker("年份")
        place = (rec.get("place", "") + P["colon"]) if rec.get("place") else ""
        line = f"{head}{title}[D]{P['sep']}{place}{inst}{P['comma']}{year}{P['dot']}"
    elif typ == "C":
        conf = rec.get("conference") or marker("论文集名")
        if not year:
            year = marker("年份")
        placepub = ""
        if rec.get("publisher"):
            placepub = ((rec.get("place", "") + P["colon"]) if rec.get("place") else "")
            placepub += rec.get("publisher", "") + P["comma"]
        pages = (P["colon"] + rec["pages"]) if rec.get("pages") else ""
        line = f"{head}{title}[C]//{conf}{P['sep']}{placepub}{year}{pages}{P['dot']}"
    elif typ == "N":
        paper = rec.get("newspaper") or marker("报纸名")
        if not year:
            year = marker("出版日期")
        line = f"{head}{title}[N]{P['sep']}{paper}{P['comma']}{year}{P['dot']}"
    elif typ == "EB":
        if not url:
            url = marker("URL")
        upd = f"({rec['update']})" if rec.get("update") else ""
        line = f"{head}{title}[EB/OL]{P['sep']}{upd}[{access_date}]{P['sep']}{url}{P['dot']}"
    else:
        line = f"{head}{title} {marker('文献类型与出处')}"

    # DOI 统一作为电子标识尾随（J/M 等有 DOI 时）
    if doi and typ in ("J", "M", "C"):
        line = line.rstrip(P["dot"]) + P["sep"] + f"DOI:{doi}{P['dot']}"
    return line, missing


def build_records(rows, colmap):
    """把行字典整理成标准字段；organizer 整理表的自由文本出处做尽力解析。"""
    records = []
    for row in rows:
        rec = {f: g(row, colmap, f) for f in HEADER_ALIASES}
        src = rec.get("source_text", "")
        if src:
            tail = parse_source_tail(src)
            for k, v in tail.items():
                if v and not rec.get(k):
                    rec[k] = v
            if not rec.get("title"):
                cleaned = clean_title_from_source(src)
                if cleaned:
                    rec["title"] = cleaned
            elif re.search(r"\d+\(\d+\)\s*[:：]\s*\d", rec["title"]):
                # 标题列被出处尾部污染（organizer 启发式偶发），优先用原文出处还原
                cleaned = clean_title_from_source(src) or clean_title_from_source(rec["title"])
                if cleaned:
                    rec["title"] = cleaned
        # paper_search 的"期刊/会议"与模板的组合列按显式类型路由到对应出处字段
        rec["type"] = normalize_type(rec.get("type"), rec)
        venue, org = rec.get("journal", ""), rec.get("institution", "")
        if rec["type"] == "C" and venue and not rec.get("conference"):
            rec["conference"], rec["journal"] = venue, ""
        elif rec["type"] == "N" and venue and not rec.get("newspaper"):
            rec["newspaper"], rec["journal"] = venue, ""
        elif rec["type"] == "M" and org and not rec.get("publisher"):
            rec["publisher"], rec["institution"] = org, ""
        records.append(rec)
    return records


# ================================================================ 主流程
def save_template(path):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(TEMPLATE_HEADERS)
        w.writerow(["期刊", "张三,李四,王五,赵六", "示例：中文期刊论文怎么著录", "2025",
                    "心理科学", "48", "3", "123-130", "", "", "", "10.1000/example", ""])
        w.writerow(["期刊", "Henseler J, Ringle C M, Sinkovics R R",
                    "The use of partial least squares path modeling in international marketing",
                    "2009", "Advances in International Marketing", "20", "", "277-319",
                    "", "", "", "10.1108/S1474-7979(2009)0000020014", ""])
        w.writerow(["学位论文", "王五", "示例学位论文题名", "2024", "", "", "", "",
                    "北京", "某某大学", "", "", ""])
        w.writerow(["电子资源", "世界卫生组织", "示例网页题名", "", "", "", "", "",
                    "", "", "https://example.org/notice", "", "2026-01-01"])
    print(f"模板已保存：{path}")
    print("把你的题录逐行填进去（类型可写 期刊/专著/学位论文/会议/报纸/电子资源），再运行本工具。")


def main():
    parser = argparse.ArgumentParser(description="参考文献格式化工具（GB/T 7714-2015 顺序编码制）")
    parser.add_argument("input", nargs="?", help="题录 CSV（paper_search 导出/整理表/本工具模板）")
    parser.add_argument("--output", "-o", default="", help="输出 txt 路径（默认：输入文件名_参考文献.txt）")
    parser.add_argument("--fullwidth", action="store_true",
                        help="使用全角标点（．，：）；默认半角，按学校模板要求选择")
    parser.add_argument("--no-number", action="store_true", help="不加 [n] 编号（著者-出版年制场景）")
    parser.add_argument("--name-case", choices=["2015", "2025"], default="2015",
                        help="欧美著者姓氏大小写：2015=全大写（默认，现行主流）；2025=首字母大写（新国标口径）")
    parser.add_argument("--access-date", default=date.today().isoformat(),
                        help="电子资源 [引用日期]，默认今天（YYYY-MM-DD）")
    parser.add_argument("--save-template", default="", metavar="PATH", help="生成空白题录模板 CSV 后退出")
    args = parser.parse_args()

    if args.save_template:
        save_template(args.save_template)
        return

    if not args.input:
        print("✗ 请提供题录 CSV 路径；没有题录表可先运行 --save-template 生成模板。")
        sys.exit(1)
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"✗ 文件不存在：{args.input}")
        sys.exit(1)

    read = read_csv_rows(in_path)
    if read is None:
        sys.exit(1)
    headers, rows = read
    if not rows:
        print("✗ CSV 里没有任何题录数据行（0 条）：请先填题录，或用 --save-template 生成模板。")
        sys.exit(1)
    colmap = map_columns(headers)
    if "title" not in colmap and "source_text" not in colmap:
        print("✗ 没找到题名列：表头需含「标题/题名」列（paper_search 导出、整理表或 --save-template 模板均可）。")
        print(f"  实际读到的表头：{headers}")
        sys.exit(1)

    records = build_records(rows, colmap)

    print("=" * 60)
    print("参考文献格式化工具（GB/T 7714-2015 顺序编码制）")
    print("=" * 60)
    lines, warnings_, untyped = [], [], 0
    for i, rec in enumerate(records, 1):
        line, missing = render_ref(rec, args.name_case, args.fullwidth, args.access_date)
        prefix = "" if args.no_number else f"[{i}] "
        lines.append(prefix + line)
        if rec["type"] is None:
            untyped += 1
            warnings_.append(f"第 {i} 条《{rec.get('title') or '?'}》：无法判断文献类型（需在类型列注明 期刊/专著/学位论文/会议/报纸/电子资源）")
        if not rec.get("authors"):
            warnings_.append(f"第 {i} 条《{rec.get('title') or '?'}》：缺作者，GB/T 7714 中责任者为必备项，请补全")
        if rec["type"] == "J" and not (rec.get("volume") or rec.get("issue") or rec.get("pages")):
            warnings_.append(f"第 {i} 条《{rec.get('title') or '?'}》：缺卷/期/页码，请到原文核对补全后重跑（paper_search 导出常不含这些字段）")
        for fld in missing:
            warnings_.append(f"第 {i} 条《{rec.get('title') or '?'}》：缺 {fld}，已在文中用【待补】标出")

    out_path = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_参考文献.txt")
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"共著录 {len(lines)} 条，已保存：{out_path}")
    print("复制到论文前请逐条核对：作者、年份、卷期页码、DOI 必须与原文一致；工具只做格式化，不生成文献。")
    if warnings_:
        print(f"\n⚠ 有 {len(warnings_)} 处需要你补/核（文中已标【待补】，不会静默伪造）：")
        for w in warnings_:
            print("  - " + w)
    if untyped:
        print(f"\n✗ {untyped} 条无法判断类型，未形成完整著录；补全类型列后重跑。")
        sys.exit(1)
    print("\n提示：学校要求全角标点就加 --fullwidth 重跑；GB/T 7714-2025 口径加 --name-case 2025。")


if __name__ == "__main__":
    main()
