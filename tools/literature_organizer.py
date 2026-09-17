#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文献整理工具
功能：文献去重、分类、导出整理表
用法：python literature_organizer.py <输入文件.csv或txt>
输入格式：每行一篇文献，包含标题、作者、年份、期刊等信息
"""

import csv
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def parse_literature_line(line):
    """解析一行文献信息，提取标题、作者、年份"""
    line = line.strip()
    if not line:
        return None

    # 尝试提取年份（4位数字，1900-2099）
    year_match = re.search(r'(19|20)\d{2}', line)
    year = year_match.group() if year_match else ''

    # 尝试提取作者（逗号前的部分，或第一个句号前）
    author = ''
    parts = re.split(r'[.,]', line, maxsplit=1)
    if parts and len(parts[0]) < 50:
        author = parts[0].strip()

    # 标题：去掉作者和年份后的剩余部分
    title = line
    if author:
        title = title.replace(author, '', 1).strip(' ,.')
    if year:
        title = title.replace(year, '').strip(' ,.()')

    return {
        'raw': line,
        'title': title[:100],
        'author': author,
        'year': year,
        'category': '',
        'notes': ''
    }


def normalize_title(title):
    """标准化标题用于去重（去标点、转小写、去空格）"""
    return re.sub(r'[^\w]', '', title.lower())


def deduplicate(literatures):
    """按标题去重"""
    seen = {}
    unique = []
    duplicates = []

    for lit in literatures:
        key = normalize_title(lit['title'])
        if key and key in seen:
            duplicates.append(lit)
        else:
            if key:
                seen[key] = True
            unique.append(lit)

    return unique, duplicates


def auto_categorize(literatures, keywords_map=None):
    """
    自动分类
    keywords_map: {分类名: [关键词列表]}
    """
    if keywords_map is None:
        keywords_map = {
            '自变量相关': ['AI', '人工智能', '依赖', '成瘾', '手机', '网络', '短视频'],
            '因变量相关': ['自伤', 'NSSI', '自杀', '抑郁', '焦虑', '心理健康'],
            '中介变量': ['孤独', '反刍', '社会支持', '自尊', '自我效能'],
            '方法学': ['中介', '调节', '网络分析', '纵向', '元分析'],
            '理论综述': ['综述', '理论', '模型', '机制'],
        }

    for lit in literatures:
        text = lit['raw'].lower()
        for category, keywords in keywords_map.items():
            for kw in keywords:
                if kw.lower() in text:
                    if lit['category']:
                        lit['category'] += '; ' + category
                    else:
                        lit['category'] = category
                    break
        if not lit['category']:
            lit['category'] = '其他'

    return literatures


def export_csv(literatures, output_path):
    """导出为CSV整理表"""
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['序号', '标题', '作者', '年份', '分类', '是否精读', '核心发现', '与本研究关系', '原文出处'])
        for i, lit in enumerate(literatures, 1):
            writer.writerow([
                i,
                lit['title'],
                lit['author'],
                lit['year'],
                lit['category'],
                '',  # 是否精读
                '',  # 核心发现
                '',  # 与本研究关系
                lit['raw'][:200]
            ])


def print_summary(literatures, duplicates):
    """打印统计摘要"""
    print('\n' + '=' * 50)
    print('文献整理摘要')
    print('=' * 50)
    print(f'总文献数：{len(literatures) + len(duplicates)}')
    print(f'去重后：{len(literatures)}')
    print(f'重复文献：{len(duplicates)}')

    # 按分类统计
    cat_count = defaultdict(int)
    for lit in literatures:
        for cat in lit['category'].split('; '):
            cat_count[cat] += 1

    print('\n分类统计：')
    for cat, count in sorted(cat_count.items(), key=lambda x: -x[1]):
        print(f'  {cat}：{count}篇')

    # 按年份统计
    year_count = defaultdict(int)
    for lit in literatures:
        if lit['year']:
            year_count[lit['year']] += 1

    if year_count:
        print('\n年份分布：')
        for year in sorted(year_count.keys()):
            print(f'  {year}年：{year_count[year]}篇')


def main():
    parser = argparse.ArgumentParser(description='文献整理工具')
    parser.add_argument('input', help='输入文件路径（txt或csv，每行一篇文献）')
    parser.add_argument('--output', '-o', help='输出文件路径（默认：输入文件名_整理表.csv）')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'错误：文件不存在 {args.input}')
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_name(
        input_path.stem + '_整理表.csv'
    )

    print('=' * 50)
    print('文献整理工具')
    print('=' * 50)

    # 读取文献（自动兼容UTF-8/GBK）
    literatures = []
    text = None
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            with open(input_path, 'r', encoding=enc) as f:
                text = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if text is None:
        print('无法识别文件编码，请把文献清单另存为UTF-8后重试。')
        return
    for line in text.splitlines():
        parsed = parse_literature_line(line)
        if parsed:
            literatures.append(parsed)

    print(f'\n读取文献：{len(literatures)}篇')

    # 去重
    unique, duplicates = deduplicate(literatures)

    # 自动分类
    unique = auto_categorize(unique)

    # 导出
    export_csv(unique, output_path)

    # 打印摘要
    print_summary(unique, duplicates)

    print(f'\n整理表已保存：{output_path}')
    print('\n提示：整理表中"是否精读""核心发现""与本研究关系"列需要你手动填写。')
    print('建议精读10-15篇最相关的文献，每篇写2-3句核心发现。')


if __name__ == '__main__':
    main()
