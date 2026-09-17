#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究模型图生成工具
功能：生成链式中介模型图、描述统计表格
用法：python chart_generator.py --model "A->B->C->D" --coefs "0.32,0.45,0.28,0.15"
依赖：matplotlib（如未安装会提示）
"""

import argparse
import sys
from pathlib import Path
# --- 输出编码守卫：管道/重定向时强制 UTF-8 ---
# 中文 Windows 控制台默认 GBK，Python 写真实控制台不受影响，
# 但 stdout 被管道/重定向时会退回 GBK，遇到 ² χ² ⚠ ↔ 等字符直接 UnicodeEncodeError 崩溃。
# AI 助手与 tests/full_e2e.py 都是以管道捕获输出的，故此处统一为 UTF-8。
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def check_matplotlib():
    """检查matplotlib是否安装"""
    try:
        import matplotlib
        return True
    except ImportError:
        return False


def draw_mediation_model(variables, coefficients, output_path, title='研究模型图'):
    """
    绘制链式中介模型图
    variables: [自变量, 中介1, 中介2, 因变量]
    coefficients: [a1, a2, b, c'] 对应路径系数
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis('off')

    # 节点位置
    positions = [(1.5, 2.5), (4.5, 2.5), (7.5, 2.5), (10.5, 2.5)]
    colors = ['#E8F4FD', '#FFF3E0', '#FFF3E0', '#E8F5E9']

    # 绘制节点
    for i, (var, (x, y)) in enumerate(zip(variables, positions)):
        box = FancyBboxPatch(
            (x - 1.0, y - 0.5), 2.0, 1.0,
            boxstyle="round,pad=0.1",
            facecolor=colors[i], edgecolor='#333', linewidth=1.5
        )
        ax.add_patch(box)
        ax.text(x, y, var, ha='center', va='center', fontsize=12)

    # 绘制箭头和路径系数
    coef_labels = ['a', 'b1', 'b2', "c'"]
    for i in range(3):
        x1, y1 = positions[i]
        x2, y2 = positions[i + 1]
        arrow = FancyArrowPatch(
            (x1 + 1.0, y1), (x2 - 1.0, y2),
            arrowstyle='->', mutation_scale=20,
            color='#333', linewidth=1.5
        )
        ax.add_patch(arrow)
        if i < len(coefficients):
            coef = coefficients[i]
            sig = ''
            if abs(coef) > 0:
                p = '***' if coef and abs(coef) > 0.3 else ('**' if abs(coef) > 0.2 else ('*' if abs(coef) > 0.1 else ''))
                sig = p
            ax.text((x1 + x2) / 2, y1 + 0.4, f'β={coef:.2f}{sig}',
                    ha='center', va='center', fontsize=10, color='#C62828')

    # 直接效应（如果有）
    if len(coefficients) >= 4:
        x1, y1 = positions[0]
        x2, y2 = positions[3]
        arrow = FancyArrowPatch(
            (x1, y1 - 0.5), (x2, y2 - 0.5),
            connectionstyle="arc3,rad=-0.3",
            arrowstyle='->', mutation_scale=20,
            color='#666', linewidth=1.2, linestyle='--'
        )
        ax.add_patch(arrow)
        ax.text((x1 + x2) / 2, 0.8, f"直接效应 c'={coefficients[3]:.2f}",
                ha='center', va='center', fontsize=10, color='#666')

    ax.set_title(title, fontsize=14, pad=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'模型图已保存：{output_path}')


def draw_simple_model(variables, coefficients, output_path, title='研究模型图'):
    """简单中介模型（自变量->中介->因变量）"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis('off')

    positions = [(2, 2.5), (5, 2.5), (8, 2.5)]
    colors = ['#E8F4FD', '#FFF3E0', '#E8F5E9']

    for i, (var, (x, y)) in enumerate(zip(variables, positions)):
        box = FancyBboxPatch(
            (x - 1.0, y - 0.5), 2.0, 1.0,
            boxstyle="round,pad=0.1",
            facecolor=colors[i], edgecolor='#333', linewidth=1.5
        )
        ax.add_patch(box)
        ax.text(x, y, var, ha='center', va='center', fontsize=12)

    # a路径和b路径
    for i in range(2):
        x1, y1 = positions[i]
        x2, y2 = positions[i + 1]
        arrow = FancyArrowPatch(
            (x1 + 1.0, y1), (x2 - 1.0, y2),
            arrowstyle='->', mutation_scale=20, color='#333', linewidth=1.5
        )
        ax.add_patch(arrow)
        if i < len(coefficients):
            ax.text((x1 + x2) / 2, y1 + 0.4, f'β={coefficients[i]:.2f}',
                    ha='center', va='center', fontsize=10, color='#C62828')

    # 直接效应
    if len(coefficients) >= 3:
        x1, y1 = positions[0]
        x2, y2 = positions[2]
        arrow = FancyArrowPatch(
            (x1, y1 - 0.5), (x2, y2 - 0.5),
            connectionstyle="arc3,rad=-0.3",
            arrowstyle='->', mutation_scale=20,
            color='#666', linewidth=1.2, linestyle='--'
        )
        ax.add_patch(arrow)
        ax.text((x1 + x2) / 2, 0.8, f"直接效应 c'={coefficients[2]:.2f}",
                ha='center', va='center', fontsize=10, color='#666')

    ax.set_title(title, fontsize=14, pad=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'模型图已保存：{output_path}')


def main():
    parser = argparse.ArgumentParser(description='研究模型图生成工具')
    parser.add_argument('--variables', '-v', required=True,
                        help='变量名，用逗号分隔，如"AI情感依赖,孤独感,反刍思维,NSSI"')
    parser.add_argument('--coefs', '-c', required=False, default=None,
                        help="路径系数，逗号分隔，链式4个 a,b1,b2,c'；不填则先用0占位")
    parser.add_argument('--type', '-t', choices=['chain', 'simple'], default='chain',
                        help='模型类型：chain链式中介，simple简单中介')
    parser.add_argument('--output', '-o', default='model.png', help='输出图片路径')
    parser.add_argument('--title', default='研究模型图', help='图表标题')
    args = parser.parse_args()

    if not check_matplotlib():
        print('错误：需要安装matplotlib库。')
        print('请运行：pip install matplotlib')
        sys.exit(1)

    variables = [v.strip() for v in args.variables.split(',') if v.strip()]
    need = 4 if args.type == 'chain' else 3
    if args.coefs:
        try:
            coefficients = [float(c.strip()) for c in args.coefs.split(',') if c.strip() != '']
        except ValueError:
            print('错误：路径系数必须是数字，用英文逗号分隔，例如 0.2,0.3,0.4,0.1')
            sys.exit(1)
        if len(coefficients) < need:
            print(f'提示：只填了{len(coefficients)}个系数，{args.type}模型需要{need}个，缺少的先用0占位。')
            coefficients += [0.0] * (need - len(coefficients))
        elif len(coefficients) > need:
            print(f'提示：填了{len(coefficients)}个系数，{args.type}模型只需{need}个，多余的已忽略。')
            coefficients = coefficients[:need]
    else:
        coefficients = [0.0] * need
        print('提示：未填路径系数，已先用0占位；结果出来后可重跑补上系数。')

    print('=' * 50)
    print('研究模型图生成工具')
    print('=' * 50)
    print(f'变量：{variables}')
    print(f'路径系数：{coefficients}')
    print(f'模型类型：{args.type}')

    output_path = Path(args.output)

    if args.type == 'chain':
        if len(variables) != 4:
            print('错误：链式中介需要4个变量（自变量,中介1,中介2,因变量）')
            sys.exit(1)
        draw_mediation_model(variables, coefficients, str(output_path), args.title)
    else:
        if len(variables) != 3:
            print('错误：简单中介需要3个变量（自变量,中介,因变量）')
            sys.exit(1)
        draw_simple_model(variables, coefficients, str(output_path), args.title)

    print('\n完成！图片分辨率300dpi，可直接插入论文。')


if __name__ == '__main__':
    main()
