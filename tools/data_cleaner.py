#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问卷数据清洗工具
功能：无效问卷检测、反向计分、量表总分计算、描述统计
用法：python data_cleaner.py <输入文件.csv> [--reverse 题目列表] [--scales 量表定义]
"""

import csv
import sys
import argparse
from pathlib import Path


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


def detect_invalid(headers, data, min_seconds=30):
    """
    检测无效问卷
    规则：
    1. 答题时间过短（如果有duration列）
    2. 连续10题以上选同一个选项
    3. 所有题答案完全一样
    返回：(有效行索引列表, 无效行详情列表)
    """
    invalid = []
    valid_indices = []

    for i, row in enumerate(data):
        reasons = []
        # 检查答题时间（如果有duration/用时列）
        time_col = None
        for j, h in enumerate(headers):
            if h and ('时间' in h or 'duration' in h.lower() or '用时' in h):
                time_col = j
                break
        if time_col is not None and time_col < len(row):
            try:
                seconds = float(row[time_col])
                if seconds < min_seconds:
                    reasons.append(f'答题时间过短({seconds}秒)')
            except (ValueError, IndexError):
                pass

        # 检查连续相同答案（跳过非数值列）
        numeric_values = []
        for cell in row:
            try:
                numeric_values.append(float(cell))
            except (ValueError, TypeError):
                pass

        if len(numeric_values) >= 10:
            # 全部相同
            if len(set(numeric_values)) == 1:
                reasons.append('所有题目答案完全相同')
            else:
                # 连续10题相同
                max_streak = 1
                current_streak = 1
                for k in range(1, len(numeric_values)):
                    if numeric_values[k] == numeric_values[k-1]:
                        current_streak += 1
                        max_streak = max(max_streak, current_streak)
                    else:
                        current_streak = 1
                if max_streak >= 10:
                    reasons.append(f'连续{max_streak}题答案相同')

        if reasons:
            invalid.append((i + 2, reasons))  # +2因为CSV行号从1开始，表头是第1行
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
    parser.add_argument('--min-seconds', type=int, default=30, help='最短答题时间（秒），默认30')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'错误：文件不存在 {args.input}')
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_name(
        input_path.stem + '_cleaned.csv'
    )

    print('=' * 50)
    print('问卷数据清洗工具')
    print('=' * 50)

    # 读取数据
    headers, data = read_csv(str(input_path))
    print(f'\n读取数据：{len(headers)}列，{len(data)}行')
    print(f'表头：{headers[:10]}...' if len(headers) > 10 else f'表头：{headers}')

    # 检测无效问卷
    valid_indices, invalid = detect_invalid(headers, data, args.min_seconds)
    print(f'\n无效问卷检测：')
    print(f'  有效问卷：{len(valid_indices)}份')
    print(f'  无效问卷：{len(invalid)}份')
    if invalid:
        print('  无效详情：')
        for row_num, reasons in invalid[:10]:
            print(f'    第{row_num}行：{", ".join(reasons)}')
        if len(invalid) > 10:
            print(f'    ...还有{len(invalid) - 10}份')

    # 过滤有效数据
    valid_data = [data[i] for i in valid_indices]

    # 写出清洗后的数据
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(valid_data)

    print(f'\n清洗后数据已保存：{output_path}')
    print(f'有效样本量：{len(valid_data)}')

    # 如果数据量够，做简单描述统计
    if valid_data:
        print('\n提示：如需计算量表总分和描述统计，请提供量表定义。')
        print('可以在AI对话中说明：哪些列属于哪个量表、哪些题需要反向计分。')

    print('\n' + '=' * 50)
    print('清洗完成！请检查输出文件。')


if __name__ == '__main__':
    main()
