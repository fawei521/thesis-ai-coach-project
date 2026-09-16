#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问卷星(及类似平台)答卷数据预处理工具
====================================================================
把从问卷星导出的原始CSV，转换成 data_cleaner.py / auto_stats.py 能直接用的
标准数值数据（题目列重命名为 Q1,Q2...，Likert文本选项转数字，用时统一成秒）。

为什么需要它：
  问卷星导出的表通常有这些问题，直接统计会失败——
  1) 前面有一堆元数据列（序号、提交时间、所用时间、来源、IP…）
  2) "所用时间"是 "2分3秒" / "123秒" 这种文本，不是数字
  3) 单选题答案是中文选项（"非常同意""男"），不是数字
  4) 表头是整道题的文字，不是 Q1、Q2

本工具只做"格式转换"，绝不删数据、绝不改答案的高低含义。
转换后会生成一份《列映射报告》，你必须逐列核对选项编码方向是否正确
（尤其反向题、以及"非常不同意"该算1还是5），核对无误再进入清洗和统计。

用法：
  python wjx_preprocess.py 问卷星原始.csv
  python wjx_preprocess.py 问卷星原始.csv --output 标准数据.csv
====================================================================
"""

import csv
import re
import sys
import argparse
from pathlib import Path


# ---------- 1. 读取（自动识别编码） ----------

def read_csv_auto(filepath):
    """依次尝试常见中文编码，返回 (表头, 数据行)"""
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
    last_err = None
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc, newline="") as f:
                rows = list(csv.reader(f))
            if rows:
                return rows[0], rows[1:], enc
        except (UnicodeDecodeError, csv.Error) as e:
            last_err = e
            continue
    print(f"错误：无法识别文件编码，请另存为 UTF-8 的CSV后重试。({last_err})")
    sys.exit(1)


# ---------- 2. 识别元数据列 ----------

META_KEYWORDS = [
    "序号", "编号", "提交答卷时间", "提交时间", "作答时间", "所用时间", "答题时长",
    "用时", "时长", "来源", "来源详情", "来自ip", "ip", "ip地址", "微信", "昵称",
    "openid", "用户", "终端", "设备", "地区", "省", "市", "总分", "得分",
]


def is_meta_column(header):
    h = header.strip().lower()
    for kw in META_KEYWORDS:
        if kw in h:
            return True
    return False


# ---------- 3. 解析答题用时（支持 "2分3秒"、"123秒"、"1:23"、纯数字） ----------

def parse_duration(text):
    """把用时文本统一成秒（int）。无法解析返回 None。"""
    if text is None:
        return None
    s = str(text).strip()
    if s == "":
        return None
    # 纯数字（问卷星有时直接是秒数）
    try:
        return int(float(s))
    except ValueError:
        pass
    total = 0
    matched = False
    m = re.search(r"(\d+)\s*分", s)
    if m:
        total += int(m.group(1)) * 60
        matched = True
    m = re.search(r"(\d+)\s*秒", s)
    if m:
        total += int(m.group(1))
        matched = True
    if matched:
        return total
    # mm:ss 形式
    m = re.match(r"^\s*(\d+):(\d{1,2})\s*$", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None


# ---------- 4. Likert 文本选项 -> 数字 ----------

# 按“从低到高”的顺序排列；键为选项中可能出现的词
LIKERT_LADDERS = [
    # 5点 同意度（最常见）
    ["非常不同意", "完全不同意", "很不同意", "不同意", "不太同意",
     "一般", "不确定", "中立", "无所谓",
     "比较同意", "同意", "很同意", "非常同意", "完全同意"],
    # 5点 符合度
    ["完全不符合", "完全不符", "不符合", "不太符合",
     "一般", "不确定",
     "比较符合", "符合", "很符合", "完全符合"],
    # 5点 频率
    ["从不", "从未", "很少", "偶尔", "有时", "经常", "总是", "一直"],
    # 4点 频率
    ["从不", "偶尔", "经常", "总是"],
    # 满意程度
    ["非常不满意", "不满意", "一般", "满意", "非常满意"],
    # 是/否（2点）
    ["否", "不是", "没有", "是", "是的", "有"],
]

# 明确的等级词 -> 分值（在“5点同意/符合”语境下）
EXPLICIT_5 = {
    "非常不同意": 1, "完全不同意": 1, "很不同意": 1, "完全不符": 1, "完全不符合": 1,
    "不同意": 2, "不太同意": 2, "不符合": 2, "不太符合": 2,
    "一般": 3, "不确定": 3, "中立": 3, "无所谓": 3,
    "比较同意": 4, "同意": 4, "很同意": 4, "比较符合": 4, "符合": 4, "很符合": 4,
    "非常同意": 5, "完全同意": 5, "完全符合": 5,
}
EXPLICIT_FREQ_5 = {"从不": 1, "从未": 1, "很少": 2, "偶尔": 2, "有时": 3,
                   "经常": 4, "总是": 5, "一直": 5}
EXPLICIT_SAT_5 = {"非常不满意": 1, "不满意": 2, "一般": 3, "满意": 4, "非常满意": 5}


def normalize_option(cell):
    return str(cell).strip().replace(" ", "").replace("　", "")


def build_option_map(distinct_texts):
    """
    根据一列里出现的所有文本选项，推断 文本->数字 的映射。
    返回 (map_dict, ladder_name, note)。无法可靠映射时 map_dict 为 {}。
    """
    texts = [normalize_option(t) for t in distinct_texts if normalize_option(t) != ""]
    texts = sorted(set(texts), key=len, reverse=True)  # 长词优先，避免"同意"抢先匹配"非常同意"
    if not texts:
        return {}, "空列", ""

    # 已经全是数字
    numeric_ok = True
    for t in texts:
        try:
            float(t)
        except ValueError:
            numeric_ok = False
            break
    if numeric_ok:
        return {t: float(t) for t in texts}, "已是数字", ""

    # 是/否、男/女 这类二分类（人口学，保留文本，不强行编码）
    joined = "".join(texts)
    if set(texts) <= {"男", "女"}:
        return {}, "人口学-性别（保留文本）", "建议在统计软件里自行编码，如男=1女=2"
    if set(texts) <= {"是", "否", "有", "没有", "是的", "不是"}:
        m = {}
        for t in texts:
            m[t] = 1 if t in ("是", "是的", "有") else 0
        return m, "二分类(是=1/否=0)", "请核对方向"

    # 同意度 / 符合度（5点）
    if any(k in joined for k in ["同意", "符合"]):
        m = {}
        used = set()
        for t in texts:
            for word in sorted(EXPLICIT_5, key=len, reverse=True):
                if word in t and word not in used:
                    m[t] = EXPLICIT_5[word]
                    used.add(word)
                    break
        if len(m) == len(texts):
            return m, "Likert-5点(同意/符合度，1最低5最高)", "务必核对：低分=不同意/不符合"

    # 频率
    if any(k in joined for k in ["从不", "偶尔", "很少", "经常", "总是", "有时"]):
        m = {}
        for t in texts:
            for word in sorted(EXPLICIT_FREQ_5, key=len, reverse=True):
                if word in t:
                    m[t] = EXPLICIT_FREQ_5[word]
                    break
        if len(m) == len(texts):
            return m, "Likert-频率(从不=1,总是=5)", "请核对点数与方向"

    # 满意度
    if "满意" in joined:
        m = {}
        for t in texts:
            for word in sorted(EXPLICIT_SAT_5, key=len, reverse=True):
                if word in t:
                    m[t] = EXPLICIT_SAT_5[word]
                    break
        if len(m) == len(texts):
            return m, "Likert-满意度(非常不满意=1,非常满意=5)", "请核对方向"

    # 无法识别
    return {}, "无法自动识别（保留文本，需人工处理）", "请人工建立选项->数字映射，或在问卷星导出时选择'按选项序号'"


# 多选题选项分隔符（问卷星默认 ┋；也兼容 | ， , ； ; 、 /）
_MULTI_SEP = ["┋", "|", "；", ";", "，", ",", "、", "/"]


def detect_special_column(header_text, col_values):
    """
    识别无法直接编码的特殊题型，返回 'multi'（多选题）/ 'open'（填空/开放题）/ None（普通单选需编码）。
    - 多选题：表头含"哪些/多选/___"，或足够比例的答案含选项分隔符且能拆成多个短选项；
      问卷星"按选项拆分"导出的 0/1 哑变量列在 data_cleaner 端按列名与取值排除。
    - 开放填空题：文本、去重取值比例高或平均字数长（答案因人而异）。
    """
    h = header_text or ""
    vals = [normalize_option(v) for v in col_values if str(v).strip() != ""]
    if not vals:
        return None

    # 1) 表头显式多选标志
    if any(k in h for k in ["哪些", "多选", "可多选", "___", "__"]):
        return "multi"

    # 2) 答案中普遍含多选分隔符
    def split_multi(s):
        for sep in _MULTI_SEP:
            if sep in s:
                parts = [p.strip() for p in s.split(sep) if p.strip()]
                # 至少两段、每段较短（选项而非长句）才算多选
                if len(parts) >= 2 and all(len(p) <= 10 for p in parts):
                    return parts
        return None

    multi_hits = sum(1 for v in vals if split_multi(v))
    if multi_hits / len(vals) >= 0.3:
        return "multi"

    # 3) 开放填空：去重比例高 或 平均字数明显偏长
    uniq = set(vals)
    avg_len = sum(len(v) for v in vals) / len(vals)
    if (len(uniq) / len(vals) >= 0.5 and avg_len >= 4) or avg_len >= 8:
        return "open"
    return None


# ---------- 5. 主流程 ----------

def main():
    parser = argparse.ArgumentParser(description="问卷星答卷数据预处理（转标准数值CSV）")
    parser.add_argument("input", help="问卷星导出的原始CSV")
    parser.add_argument("--output", "-o", help="输出的标准数据CSV（默认：原文件名_标准.csv）")
    parser.add_argument("--report", help="列映射报告路径（默认：输出同名_列映射报告.txt）")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"错误：文件不存在 {args.input}")
        sys.exit(1)

    headers, data, enc = read_csv_auto(str(in_path))
    ncol = len(headers)

    out_path = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_标准.csv")
    report_path = Path(args.report) if args.report else out_path.with_name(out_path.stem + "_列映射报告.txt")

    print("=" * 64)
    print("问卷星数据预处理工具")
    print("=" * 64)
    print(f"读取：{in_path.name}（编码 {enc}），{len(data)} 份答卷，{ncol} 列")

    # 分类列
    q_index = 0
    new_headers = []
    col_plan = []  # (原列名, 新列名, 类型, 映射/说明)
    duration_col = None

    for j, h in enumerate(headers):
        h_stripped = h.strip()
        # 用时列
        if any(k in h_stripped for k in ["所用时间", "答题时长", "用时", "时长", "作答时间"]) and "提交" not in h_stripped:
            new_headers.append("用时(秒)")
            duration_col = j
            col_plan.append((h_stripped, "用时(秒)", "用时", "统一换算为秒"))
            continue
        if is_meta_column(h_stripped):
            # 元数据列丢弃（不进入分析），但记录在报告里
            col_plan.append((h_stripped, "（已跳过）", "元数据", "不进入统计分析"))
            continue
        # 题目列
        q_index += 1
        qname = f"Q{q_index}"
        new_headers.append(qname)
        col_plan.append((h_stripped, qname, "题目", ""))

    # 对每个题目列推断选项映射
    q_items = []  # (新列名Q, 原列索引j, map, 类型名, note)
    qnum = 0
    for j, h in enumerate(headers):
        h_stripped = h.strip()
        if any(k in h_stripped for k in ["所用时间", "答题时长", "用时", "时长", "作答时间"]) and "提交" not in h_stripped:
            continue
        if is_meta_column(h_stripped):
            continue
        qnum += 1
        qname = f"Q{qnum}"
        distinct = []
        seen = set()
        for row in data:
            if j < len(row):
                v = row[j].strip()
                if v != "" and v not in seen:
                    seen.add(v)
                    distinct.append(v)
        opt_map, ladder_name, note = build_option_map(distinct)
        q_items.append((qname, j, opt_map, ladder_name, note, distinct))

    # 转换数据
    converted_rows = []
    for row in data:
        new_row = []
        # 用时
        if duration_col is not None and duration_col < len(row):
            sec = parse_duration(row[duration_col])
            new_row.append("" if sec is None else sec)
        else:
            new_row.append("")
        # 题目
        for (qname, j, opt_map, ladder_name, note, distinct) in q_items:
            raw = row[j].strip() if j < len(row) else ""
            if raw == "":
                new_row.append("")
                continue
            cell = normalize_option(raw)
            if not opt_map:
                # 无法映射：保留原文（后续人工处理）
                new_row.append(raw)
            else:
                val = opt_map.get(cell)
                if val is None:
                    # 出现了建表时没见过的选项
                    new_row.append(raw)
                else:
                    new_row.append(int(val) if float(val).is_integer() else val)
        converted_rows.append(new_row)

    # 只有当存在用时列时才保留第一列；否则去掉空的用时列
    if duration_col is None:
        new_headers = new_headers[1:]
        converted_rows = [r[1:] for r in converted_rows]

    # 写出标准数据
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(new_headers)
        w.writerows(converted_rows)

    # 分类：人口学列 / 多选题·开放填空题（不编码进量表）/ 真正需要人工编码的单选题
    unrecognized = []
    demographic = []
    special = []  # (qname, orig, kind, distinct)
    for (qname, j, opt_map, ladder_name, note, distinct) in q_items:
        if opt_map:
            continue
        if ladder_name.startswith("人口学"):
            demographic.append((qname, headers[j].strip(), distinct))
            continue
        col_vals = [row[j] if j < len(row) else "" for row in data]
        kind = detect_special_column(headers[j].strip(), col_vals)
        if kind in ("multi", "open"):
            special.append((qname, headers[j].strip(), kind, distinct))
        else:
            unrecognized.append((qname, headers[j].strip(), distinct))

    # 写列映射报告
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("问卷星数据 列映射报告（请逐列核对，尤其选项编码方向）\n")
        f.write("=" * 64 + "\n")
        f.write(f"源文件：{in_path.name}\n答卷数：{len(data)}\n标准数据：{out_path.name}\n\n")

        f.write("一、被跳过的元数据列（不参与分析）\n")
        f.write("-" * 64 + "\n")
        for (orig, new, typ, note) in col_plan:
            if typ == "元数据":
                f.write(f"  {orig}\n")
        f.write("\n")

        f.write("二、题目列映射（重点核对）\n")
        f.write("-" * 64 + "\n")
        for (qname, j, opt_map, ladder_name, note, distinct) in q_items:
            orig = headers[j].strip().replace("\n", " ")
            f.write(f"\n[{qname}] {orig}\n")
            f.write(f"  识别类型：{ladder_name}\n")
            if opt_map:
                mapping_str = "；".join(f"{k}→{int(v) if float(v).is_integer() else v}"
                                        for k, v in sorted(opt_map.items(), key=lambda x: x[1]))
                f.write(f"  编码：{mapping_str}\n")
            else:
                f.write(f"  出现的选项：{ '、'.join(distinct[:20]) }\n")
            if note:
                f.write(f"  ⚠ {note}\n")

        f.write("\n" + "=" * 64 + "\n")
        f.write("三、人口学分类列（保留文字，做频数/百分比统计即可，无需转数字）\n")
        f.write("-" * 64 + "\n")
        if demographic:
            for (qname, orig, distinct) in demographic:
                f.write(f"  {qname}：{orig[:40]}（选项：{ '、'.join(distinct[:12]) }）\n")
        else:
            f.write("  无\n")

        f.write("\n四、多选题与开放填空题（保留原文，不要编码进量表）\n")
        f.write("-" * 64 + "\n")
        if special:
            for (qname, orig, kind, distinct) in special:
                kind_cn = "多选题" if kind == "multi" else "开放填空题"
                f.write(f"  {qname}【{kind_cn}】：{orig[:40]}\n")
                if kind == "multi":
                    f.write(f"     示例：{ '、'.join(distinct[:6]) }\n")
            f.write("\n处理方式：\n")
            f.write("  · 这些题不是 Likert 量表题，写 scales.txt 时【不要】列入，否则信度/总分会错；\n")
            f.write("  · 多选题：在问卷星可直接看各选项的选择人数与百分比，写进论文描述统计；\n")
            f.write("    若要做交叉分析，在问卷星导出时选『按选项拆分』成多个 0/1 列，清洗器会自动识别并排除；\n")
            f.write("  · 开放填空题：做归类/词频或引用典型回答，不参与数值统计。\n")
        else:
            f.write("  无\n")

        f.write("\n五、需要你人工编码的单选题（未能自动转数字）\n")
        f.write("-" * 64 + "\n")
        if unrecognized:
            for (qname, orig, distinct) in unrecognized:
                f.write(f"  {qname}：{orig[:40]}\n")
                f.write(f"     选项：{ '、'.join(distinct[:20]) }\n")
            f.write("\n这些一般是有固定选项但措辞无法自动识别的单选题（如年级、专业类别）。\n")
            f.write("请在问卷星重新导出时选择『按选项序号下载』，")
            f.write("或在AI/统计软件里手动指定编码（如大一=1、大二=2…）。\n")
        else:
            f.write("  无。所有量表单选题均已成功转为数字。\n")

        f.write("\n六、重要提醒\n")
        f.write("  1. 本工具只转格式，没有删除任何答卷、没有改变任何答案高低含义。\n")
        f.write("  2. 反向题不会在这里自动反转，请在统计阶段统一做反向计分。\n")
        f.write("  3. 请抽查3-5份原始答卷与转换结果，确认编码无误后再清洗、统计。\n")

    # 控制台摘要
    print(f"\n题目列：{len(q_items)} 个；元数据列已跳过；"
          f"用时列：{'已识别并换算为秒' if duration_col is not None else '未识别（不影响）'}")
    print(f"标准数据已保存：{out_path}")
    print(f"列映射报告已保存：{report_path}")
    if demographic:
        print(f"人口学分类列（保留文字，正常）：{len(demographic)} 个 -> "
              f"{', '.join(q for q, _, _ in demographic)}")
    if special:
        print(f"\n○ 识别到 {len(special)} 个多选/开放填空题（已保留原文，不进量表，写 scales.txt 时请勿列入）：")
        for (qname, orig, kind, _) in special:
            print(f"   {qname}【{'多选' if kind=='multi' else '开放填空'}】 {orig[:28]}")
    if unrecognized:
        print(f"\n⚠ 有 {len(unrecognized)} 个单选题无法自动转数字，请打开列映射报告查看并人工编码：")
        for (qname, orig, _) in unrecognized:
            print(f"   {qname}  {orig[:30]}")
    else:
        print("\n所有量表单选题均已转为数字。请打开《列映射报告》核对编码方向，抽查无误后继续。")
    print("\n下一步：")
    print("  1) 打开列映射报告核对（重点：非常不同意=1，非常同意=5）")
    print("  2) python tools/data_cleaner.py " + str(out_path.name))
    print("  3) 让AI帮你写 scales.txt，再跑 auto_stats.py")


if __name__ == "__main__":
    main()
