#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问卷数据清洗工具
功能：无效问卷检测、反向计分、量表总分计算、描述统计
用法：python data_cleaner.py <输入文件.csv> [--reverse 题目列表] [--scales 量表定义]
"""

import csv
import sys
import math
import argparse
from pathlib import Path
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# 非作答列关键词（时间/序号/人口学等），无 scales.txt 时用启发式排除，不计入 longstring/SD/缺失
_NON_RESPONSE_KEYWORDS = [
    "时间", "用时", "时长", "duration", "序号", "编号", "ip", "学号", "姓名",
    "性别", "年级", "年龄", "生源", "独生", "专业", "学历", "收入", "地区",
    "民族", "政治", "宗教", "恋爱", "是否", "来源", "渠道", "提交", "作答",
    "注意力", "检查题", "请选", "本题请",
    # 多选题（问卷星默认一列用 ┋/|/， 分隔，或拆成 0/1 哑变量列，表头常带 ___ 与"哪些"）
    "哪些", "多选", "可多选", "___", "__",
]


def read_csv(filepath):
    """读取CSV文件，返回表头和数据行；自动兼容UTF-8(含BOM)与GBK/GB18030。"""
    rows = None
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            with open(filepath, 'r', encoding=enc, newline="") as f:
                rows = list(csv.reader(f))
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if rows is None:
        raise ValueError("无法识别文件编码，请把CSV另存为UTF-8后重试")
    if not rows:
        return [], []
    return rows[0], rows[1:]


def parse_scales(path):
    """解析简易 scales.txt：每行 量表名=题1,题2(R),题3；返回所有作答题列名集合（含反向题）。"""
    items = set()
    if not path:
        return items
    p = Path(path)
    if not p.exists():
        return items
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            lines = p.read_text(encoding=enc).splitlines()
            break
        except (UnicodeDecodeError, UnicodeError):
            lines = None
    if lines is None:
        return items
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        _, rhs = line.split("=", 1)
        for it in rhs.split(","):
            name = it.strip().replace("(R)", "").replace("（R）", "").strip()
            if name:
                items.add(name)
    return items


def guess_response_cols(headers, data):
    """无 scales.txt 时启发式识别 Likert 作答列：数值、取值落在 0-7、至少3个不同取值、
    排除时间/人口学/多选等非作答列。纯 0/1 二值列（多选哑变量、是否题）不在此兜底纳入——
    NSSI 等 0/1 计分量表应在 scales.txt 中显式列出（有 scales 时走精确通道，不经过本函数）。"""
    cols = []
    for j, h in enumerate(headers):
        hl = (h or "").lower()
        if any(k in hl for k in _NON_RESPONSE_KEYWORDS):
            continue
        vals = []
        for row in data:
            if j < len(row) and row[j].strip() != "":
                try:
                    vals.append(float(row[j]))
                except ValueError:
                    vals = None
                    break
        if vals and len(vals) >= max(5, int(0.5 * len(data))):
            uniq = set(vals)
            if uniq <= {0.0, 1.0}:
                # 纯 0/1：多选哑变量或是否题，不按 Likert 连续作答题算质量指标
                continue
            if all(0 <= v <= 7 for v in vals) and len(uniq) >= 3:
                cols.append(j)
    return cols


def resolve_attention_cols(headers, specs):
    """把 '列名关键词=正确答案;...' 解析为 [(列索引, 正确答案float, 原始描述)]。"""
    out = []
    for spec in specs:
        if "=" not in spec:
            continue
        key, ans = spec.split("=", 1)
        key, ans = key.strip(), ans.strip()
        try:
            target = float(ans)
        except ValueError:
            continue
        idx = next((j for j, h in enumerate(headers) if key in (h or "")), None)
        if idx is not None:
            out.append((idx, target, key))
    return out


def detect_invalid(headers, data, min_seconds=30, longstring_n=10, low_sd=0.3,
                   max_missing=0.2, attention=None, response_cols=None):
    """
    检测无效问卷（只对 Likert 作答列计算作答质量指标）：
    1. 答题时间过短（含"时间/用时/duration"列，<min_seconds 秒）
    2. 长直线作答：作答列连续 longstring_n 题选同一选项（straight-lining）
    3. 个体内低变异：所有作答的标准差 < low_sd（设 0 关闭；几乎不变化=没认真读题）
    4. 缺失率过高：作答列缺失比例 > max_missing
    5. 注意力检查题（instructed response item）答错：--attention 指定，答错即判无效
    返回：(有效行索引列表, 无效行详情列表)；详情为 dict，含各项指标值与原因。
    """
    attention = attention or []
    if response_cols is None:
        response_cols = guess_response_cols(headers, data)
    time_col = next((j for j, h in enumerate(headers)
                     if h and ("时间" in h or "duration" in h.lower() or "用时" in h)), None)

    invalid, valid_indices = [], []
    for i, row in enumerate(data):
        reasons, metrics = [], {}

        # 1. 时长
        if time_col is not None and time_col < len(row) and row[time_col].strip():
            try:
                seconds = float(row[time_col])
                metrics["时长"] = seconds
                if seconds < min_seconds:
                    reasons.append(f"答题时间过短({seconds:g}秒<{min_seconds}秒)")
            except ValueError:
                pass

        # 作答列序列（按列顺序）
        resp = []
        missing = 0
        for j in response_cols:
            if j >= len(row) or row[j].strip() == "":
                missing += 1
                resp.append(None)
            else:
                try:
                    resp.append(float(row[j]))
                except ValueError:
                    missing += 1
                    resp.append(None)
        answered = [v for v in resp if v is not None]
        ncol = len(response_cols)

        # 4. 缺失率
        if ncol > 0:
            miss_ratio = missing / ncol
            metrics["缺失率"] = miss_ratio
            if miss_ratio > max_missing:
                reasons.append(f"作答缺失率过高({miss_ratio*100:.0f}%>{max_missing*100:.0f}%)")

        # 2. 长直线（只看连续作答，缺失不打断/视为打断，保守起见缺失打断连击）
        if len(answered) >= 10:
            max_streak = cur = 1
            prev = None
            for v in resp:
                if v is None:
                    cur, prev = 0, None
                    continue
                if prev is not None and v == prev:
                    cur += 1
                    max_streak = max(max_streak, cur)
                else:
                    cur = 1
                prev = v
            metrics["最长连续相同"] = max_streak
            if max_streak >= longstring_n:
                reasons.append(f"长直线作答(连续{max_streak}题相同≥{longstring_n})")

        # 3. 个体内低变异（至少答了8题才算）
        if len(answered) >= 8:
            m = sum(answered) / len(answered)
            var = sum((v - m) ** 2 for v in answered) / (len(answered) - 1)
            sd = math.sqrt(var)
            metrics["作答SD"] = round(sd, 3)
            if low_sd and sd < low_sd:
                reasons.append(f"作答几乎无变异(SD={sd:.2f}<{low_sd})")

        # 5. 注意力检查题
        for col_idx, target, key in attention:
            if col_idx < len(row) and row[col_idx].strip() != "":
                try:
                    given = float(row[col_idx])
                    if abs(given - target) > 1e-9:
                        reasons.append(f"注意力检查题“{key}”答错(选{given:g},应选{target:g})")
                except ValueError:
                    reasons.append(f"注意力检查题“{key}”未有效作答")

        if reasons:
            invalid.append({"行号": i + 2, "原因": reasons, "指标": metrics})
        else:
            valid_indices.append(i)

    return valid_indices, invalid


def reverse_score(value, max_score=5):
    """反向计分"""
    return max_score + 1 - value


def calculate_scale_scores(headers, data, scale_defs, reverse_items=None):
    """
    计算量表总分
    scale_defs: {量表名: [题目列索引列表]}
    reverse_items: 需要反向计分的题目列索引列表
    """
    if reverse_items is None:
        reverse_items = []

    results = []
    for row in data:
        row_result = {}
        for scale_name, col_indices in scale_defs.items():
            scores = []
            for idx in col_indices:
                if idx < len(row):
                    try:
                        val = float(row[idx])
                        if idx in reverse_items:
                            val = reverse_score(val)
                        scores.append(val)
                    except (ValueError, TypeError):
                        pass
            if scores:
                row_result[scale_name] = sum(scores)
                row_result[f'{scale_name}_均值'] = round(sum(scores) / len(scores), 3)
            else:
                row_result[scale_name] = ''
                row_result[f'{scale_name}_均值'] = ''
        results.append(row_result)
    return results


def descriptive_stats(values):
    """计算描述统计"""
    if not values:
        return {}
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1) if n > 1 else 0
    std = variance ** 0.5
    return {
        'N': n,
        '均值': round(mean, 3),
        '标准差': round(std, 3),
        '最小值': min(values),
        '最大值': max(values),
    }


def main():
    parser = argparse.ArgumentParser(description='问卷数据清洗工具')
    parser.add_argument('input', help='输入CSV文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径（默认：输入文件名_cleaned.csv）')
    parser.add_argument('--min-seconds', type=float, default=30, help='最短答题时间（秒），默认30')
    parser.add_argument('--longstring', type=int, default=10,
                        help='长直线判定：连续多少题选同一项判无效，默认10')
    parser.add_argument('--low-sd', type=float, default=0.3,
                        help='个体作答SD低于该值判为低变异（几乎没读题），设0关闭，默认0.3')
    parser.add_argument('--max-missing', type=float, default=0.2,
                        help='作答列缺失率超过该比例（0-1）判无效，默认0.2即两成')
    parser.add_argument('--attention', default='',
                        help='注意力检查题，格式 "列名关键词=正确答案;第二题=答案"，如 "本题请选3=3;认真作答选2=2"')
    parser.add_argument('--scales', default='', help='可选：scales.txt 路径，提供后只对量表题目计算作答质量，更准确')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'错误：文件不存在 {args.input}')
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_name(
        input_path.stem + '_cleaned.csv'
    )
    report_path = input_path.with_name(input_path.stem + '_清洗报告.csv')

    print('=' * 50)
    print('问卷数据清洗工具')
    print('=' * 50)

    # 读取数据
    headers, data = read_csv(str(input_path))
    print(f'\n读取数据：{len(headers)}列，{len(data)}行')

    # 确定作答列
    scale_items = parse_scales(args.scales)
    if scale_items:
        response_cols = [j for j, h in enumerate(headers) if h in scale_items]
        print(f'按 scales.txt 识别 {len(response_cols)} 道量表作答题（质量指标只针对这些题）')
    else:
        response_cols = guess_response_cols(headers, data)
        print(f'未提供/未识别 scales.txt，启发式识别 {len(response_cols)} 道 Likert 作答题；')
        print('  若识别不准（混入人口学或漏题），建议加 --scales scales.txt')
    attention = resolve_attention_cols(headers, [s for s in args.attention.split(';') if s])
    if args.attention and not attention:
        print('  ⚠ 未在表头找到 --attention 指定的注意力检查题，请检查列名关键词')
    elif attention:
        print(f'已启用 {len(attention)} 道注意力检查题（答错即判无效）')

    # 检测无效问卷
    valid_indices, invalid = detect_invalid(
        headers, data, min_seconds=args.min_seconds, longstring_n=args.longstring,
        low_sd=args.low_sd, max_missing=args.max_missing,
        attention=attention, response_cols=response_cols)
    print(f'\n无效问卷检测：')
    print(f'  原始问卷：{len(data)}份；有效：{len(valid_indices)}份；无效：{len(invalid)}份')
    # 各原因计数
    reason_count = {}
    for item in invalid:
        for rsn in item["原因"]:
            key = rsn.split("(")[0]
            reason_count[key] = reason_count.get(key, 0) + 1
    if reason_count:
        print('  剔除原因计数（一份可命中多条）：')
        for key, cnt in sorted(reason_count.items(), key=lambda x: -x[1]):
            print(f'    {key}：{cnt}份')
    if invalid:
        print('  无效详情（前10份）：')
        for item in invalid[:10]:
            print(f'    第{item["行号"]}行：{"；".join(item["原因"])}')
        if len(invalid) > 10:
            print(f'    ...还有{len(invalid) - 10}份，见清洗报告')

    # 过滤有效数据
    valid_data = [data[i] for i in valid_indices]

    # 写出清洗后的数据
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(valid_data)
    print(f'\n清洗后数据已保存：{output_path}')

    # 写出剔除明细报告（便于论文"数据清洗"部分报告剔除标准与份数）
    with open(report_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['原始行号', '答题时长秒', '最长连续相同', '作答SD', '缺失率', '剔除原因'])
        for item in invalid:
            mt = item["指标"]
            w.writerow([item["行号"],
                        mt.get("时长", ""),
                        mt.get("最长连续相同", ""),
                        mt.get("作答SD", ""),
                        (f'{mt.get("缺失率", 0)*100:.0f}%' if "缺失率" in mt else ""),
                        "；".join(item["原因"])])
    print(f'剔除明细报告已保存：{report_path}')
    print(f'有效样本量：{len(valid_data)}')

    print('\n提示：剔除标准（时长/长直线/低变异/缺失率/注意力题）应在论文"数据清洗"部分如实写明；')
    print('不得为追求显著而随意放宽或加严，注意力检查题是最受认可的硬指标，建议正式问卷放1-2道。')

    print('\n' + '=' * 50)
    print('清洗完成！请检查输出文件。')


if __name__ == '__main__':
    main()
