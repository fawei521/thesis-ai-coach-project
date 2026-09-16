#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化统计分析工具（心理学问卷研究）
功能：数据画像、描述统计、Cronbach's α信度、Pearson相关矩阵、线性回归
输出：控制台结果 + CSV三线表
特点：纯Python标准库实现，无需安装numpy/scipy/pandas

用法：
  python auto_stats.py data.csv                          # 全自动分析所有数值列
  python auto_stats.py data.csv --scales scales.txt      # 按量表分组算信度
  python auto_stats.py data.csv --profile                # 只看数据画像
  python auto_stats.py data.csv --output 结果.csv

量表配置文件 scales.txt 格式（每行：量表名=列1,列2,列3）：
  AI情感依赖=Q1,Q2,Q3,Q4,Q5
  孤独感=Q6,Q7,Q8,Q9,Q10,Q11
"""

import csv
import sys
import math
import argparse
from pathlib import Path


# ============ 基础数学函数 ============

def mean(values):
    return sum(values) / len(values) if values else 0.0


def variance(values, ddof=1):
    if len(values) <= ddof:
        return 0.0
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - ddof)


def stdev(values, ddof=1):
    return math.sqrt(variance(values, ddof))


def pearson_r(x, y):
    """Pearson相关系数，成对删除缺失"""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 3:
        return None, n
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    den_x = math.sqrt(sum((a - mx) ** 2 for a in xs))
    den_y = math.sqrt(sum((b - my) ** 2 for b in ys))
    if den_x == 0 or den_y == 0:
        return None, n
    return num / (den_x * den_y), n


def betacf(a, b, x, max_iter=200, eps=3e-12):
    """不完全beta函数的连分数展开（Numerical Recipes）"""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betai(a, b, x):
    """正则化不完全beta函数 I_x(a,b)"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    else:
        return 1.0 - bt * betacf(b, a, 1.0 - x) / b


def t_p_two_sided(t, df):
    """t统计量的双尾p值"""
    if df <= 0:
        return None
    x = df / (df + t * t)
    return betai(df / 2.0, 0.5, x)


def sig_mark(p):
    """显著性标记"""
    if p is None:
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def fmt_p(p):
    if p is None:
        return ""
    if p < 0.001:
        return "<.001"
    return f"{p:.3f}".lstrip("0")


# ============ 数据读取 ============

def read_data(filepath):
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return [], []
    headers = rows[0]
    data = rows[1:]
    return headers, data


def to_float_matrix(headers, data):
    """把数据转成数值矩阵，非数值记为None"""
    matrix = {h: [] for h in headers}
    for row in data:
        for j, h in enumerate(headers):
            val = row[j] if j < len(row) else ""
            try:
                matrix[h].append(float(val) if val.strip() != "" else None)
            except (ValueError, AttributeError):
                matrix[h].append(None)
    return matrix


def numeric_columns(matrix, headers):
    """识别数值列（至少80%是数字）"""
    numeric = []
    for h in headers:
        vals = matrix[h]
        valid = [v for v in vals if v is not None]
        if valid and len(valid) >= 0.8 * len(vals):
            numeric.append(h)
    return numeric


# ============ 分析模块 ============

def data_profile(headers, data, matrix, num_cols):
    print("\n" + "=" * 60)
    print("一、数据画像")
    print("=" * 60)
    print(f"总样本量：{len(data)}")
    print(f"总变量数：{len(headers)}")
    print(f"数值变量：{len(num_cols)}个")
    print(f"非数值变量：{len(headers) - len(num_cols)}个")

    print("\n缺失值情况：")
    total_missing = 0
    for h in num_cols:
        miss = sum(1 for v in matrix[h] if v is None)
        total_missing += miss
        if miss > 0:
            pct = miss / len(matrix[h]) * 100
            print(f"  {h}：缺失{miss}个（{pct:.1f}%）")
    if total_missing == 0:
        print("  无缺失值")


def descriptive(matrix, num_cols):
    print("\n" + "=" * 60)
    print("二、描述统计")
    print("=" * 60)
    print(f"{'变量':<12}{'N':>6}{'均值':>10}{'标准差':>10}{'最小值':>9}{'最大值':>9}")
    print("-" * 60)
    results = []
    for h in num_cols:
        vals = [v for v in matrix[h] if v is not None]
        if not vals:
            continue
        m, sd = mean(vals), stdev(vals)
        print(f"{h:<12}{len(vals):>6}{m:>10.3f}{sd:>10.3f}{min(vals):>9.1f}{max(vals):>9.1f}")
        results.append({"变量": h, "N": len(vals), "均值": round(m, 3),
                        "标准差": round(sd, 3), "最小值": min(vals), "最大值": max(vals)})
    return results


def cronbach_alpha(items_data):
    """
    Cronbach's α
    items_data: list of lists，每个子列表是一个题目的所有作答
    """
    k = len(items_data)
    if k < 2:
        return None
    n = len(items_data[0])
    item_vars = []
    total_scores = [0.0] * n
    valid_count = 0
    for i in range(n):
        row_vals = [items_data[j][i] for j in range(k) if items_data[j][i] is not None]
        if len(row_vals) == k:
            total_scores[i] = sum(row_vals)
            valid_count += 1
        else:
            total_scores[i] = None
    for item in items_data:
        vals = [v for v in item if v is not None]
        item_vars.append(variance(vals))
    valid_totals = [t for t in total_scores if t is not None]
    if len(valid_totals) < 3:
        return None
    total_var = variance(valid_totals)
    if total_var == 0:
        return None
    alpha = (k / (k - 1)) * (1 - sum(item_vars) / total_var)
    return alpha


def reliability_analysis(matrix, scales_config):
    print("\n" + "=" * 60)
    print("三、信度分析（Cronbach's α）")
    print("=" * 60)
    if not scales_config:
        print("未提供量表配置，跳过。")
        print("配置方法：创建scales.txt，每行写 量表名=题1,题2,题3")
        return []

    results = []
    for scale_name, items in scales_config.items():
        available = [it for it in items if it in matrix]
        missing_items = [it for it in items if it not in matrix]
        if missing_items:
            print(f"⚠ {scale_name}：以下题目在数据中找不到：{missing_items}")
        if len(available) < 2:
            print(f"✗ {scale_name}：可用题目不足2个，无法计算α")
            continue
        items_data = [matrix[it] for it in available]
        alpha = cronbach_alpha(items_data)

        # 删题后α
        item_alphas = {}
        for idx, it in enumerate(available):
            rest = [items_data[j] for j in range(len(available)) if j != idx]
            a = cronbach_alpha(rest)
            item_alphas[it] = a

        if alpha is not None:
            rating = "优秀" if alpha >= 0.9 else "良好" if alpha >= 0.8 else "可接受" if alpha >= 0.7 else "偏低，需检查"
            print(f"\n{scale_name}（{len(available)}题）：α = {alpha:.3f}  [{rating}]")
            for it in available:
                a = item_alphas[it]
                flag = " ← 删题后α升高，考虑删除" if a and alpha and a > alpha + 0.02 else ""
                print(f"    {it}：删题后α = {a:.3f}{flag}")
            results.append({"量表": scale_name, "题数": len(available),
                            "Cronbach_alpha": round(alpha, 3), "评价": rating})
    return results


def correlation_matrix(matrix, num_cols, max_cols=15):
    print("\n" + "=" * 60)
    print("四、相关分析（Pearson）")
    print("=" * 60)
    cols = num_cols[:max_cols]
    if len(num_cols) > max_cols:
        print(f"（变量较多，只显示前{max_cols}个，建议用量表总分做相关）")

    results = []
    # 打印矩阵
    short = {c: c[:8] for c in cols}
    header_row = "          " + "".join(f"{short[c]:>10}" for c in cols)
    print(header_row)
    for i, c1 in enumerate(cols):
        row_str = f"{short[c1]:<10}"
        for j, c2 in enumerate(cols):
            if j > i:
                row_str += "       -  "
            else:
                r, n = pearson_r(matrix[c1], matrix[c2])
                if r is None:
                    row_str += "     n/a  "
                elif i == j:
                    row_str += "    1.000  "
                else:
                    t = r * math.sqrt((n - 2) / max(1 - r * r, 1e-12))
                    p = t_p_two_sided(t, n - 2)
                    mark = sig_mark(p)
                    row_str += f"{r:>7.3f}{mark:<3}"
                    results.append({"变量1": c1, "变量2": c2, "r": round(r, 3),
                                    "p": fmt_p(p), "显著性": mark, "N": n})
        print(row_str)
    print("\n注：*p<.05  **p<.01  ***p<.001")
    return results


def linear_regression(matrix, x_cols, y_col):
    """多元线性回归（最小二乘），输出β、SE、t、p、R²"""
    # 构建完整数据（列表删除缺失）
    all_cols = x_cols + [y_col]
    cases = []
    for i in range(len(matrix[y_col])):
        row = []
        ok = True
        for c in all_cols:
            v = matrix[c][i] if c in matrix else None
            if v is None:
                ok = False
                break
            row.append(v)
        if ok:
            cases.append(row)
    n = len(cases)
    k = len(x_cols)
    if n <= k + 2:
        print(f"✗ 样本量{n}太小，无法对{k}个预测变量做回归")
        return None

    # X矩阵（含截距），y向量
    X = [[1.0] + r[:k] for r in cases]
    y = [r[k] for r in cases]

    beta = solve_least_squares(X, y)
    if beta is None:
        print("✗ 回归求解失败（矩阵奇异，可能存在多重共线性）")
        return None

    # 预测值、残差、R²
    y_hat = [sum(beta[j] * X[i][j] for j in range(k + 1)) for i in range(n)]
    y_mean = mean(y)
    ss_res = sum((y[i] - y_hat[i]) ** 2 for i in range(n))
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1)
    mse = ss_res / (n - k - 1)

    # 标准误（(X'X)^-1 * MSE）
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k + 1)] for a in range(k + 1)]
    inv = invert_matrix(XtX)
    if inv is None:
        print("✗ 无法计算标准误")
        return None

    print(f"\n回归分析：{y_col}（N={n}, R²={r2:.3f}, 调整R²={adj_r2:.3f}）")
    print(f"{'预测变量':<14}{'B':>10}{'SE':>9}{'β(标准化)':>11}{'t':>9}{'p':>9}")
    print("-" * 62)

    # 标准化β
    sd_y = stdev(y)
    result_rows = []
    labels = ["截距"] + x_cols
    for j in range(k + 1):
        se = math.sqrt(max(inv[j][j] * mse, 0))
        t = beta[j] / se if se > 0 else 0
        p = t_p_two_sided(t, n - k - 1)
        if j == 0:
            beta_std = ""
        else:
            sd_x = stdev([r[j - 1] for r in cases])
            beta_std_val = beta[j] * sd_x / sd_y if sd_y > 0 else 0
            beta_std = f"{beta_std_val:.3f}"
        print(f"{labels[j]:<14}{beta[j]:>10.3f}{se:>9.3f}{beta_std:>11}{t:>9.3f}{fmt_p(p):>9}{sig_mark(p)}")
        result_rows.append({"预测变量": labels[j], "B": round(beta[j], 3),
                            "SE": round(se, 3), "标准化β": beta_std,
                            "t": round(t, 3), "p": fmt_p(p), "显著性": sig_mark(p)})

    # F检验
    ss_reg = ss_tot - ss_res
    f = (ss_reg / k) / mse if mse > 0 else 0
    # F的p值用beta函数
    f_p = f_p_value(f, k, n - k - 1)
    print(f"\n整体模型：F({k},{n - k - 1}) = {f:.3f}, p = {fmt_p(f_p)}{sig_mark(f_p)}")
    return {"R2": round(r2, 3), "调整R2": round(adj_r2, 3),
            "F": round(f, 3), "p": fmt_p(f_p), "系数": result_rows}


def f_p_value(f, df1, df2):
    """F检验p值"""
    if f <= 0:
        return 1.0
    x = df2 / (df2 + df1 * f)
    return betai(df2 / 2.0, df1 / 2.0, x)


def solve_least_squares(X, y):
    """最小二乘：β=(X'X)^-1 X'y"""
    n = len(X)
    p = len(X[0])
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(p)]
    inv = invert_matrix(XtX)
    if inv is None:
        return None
    return [sum(inv[a][b] * Xty[b] for b in range(p)) for a in range(p)]


def invert_matrix(A):
    """高斯-约当消元求逆矩阵"""
    n = len(A)
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-12:
            return None
        M[col], M[pivot] = M[pivot], M[col]
        pivot_val = M[col][col]
        M[col] = [v / pivot_val for v in M[col]]
        for r in range(n):
            if r != col:
                factor = M[r][col]
                M[r] = [M[r][j] - factor * M[col][j] for j in range(2 * n)]
    return [row[n:] for row in M]


def export_three_line_table(desc, corr, output):
    """导出三线表（描述统计+相关矩阵合并CSV）"""
    with open(output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["表1 描述统计与相关分析结果"])
        w.writerow(["变量", "N", "均值", "标准差"])
        for d in desc:
            w.writerow([d["变量"], d["N"], d["均值"], d["标准差"]])
        w.writerow([])
        w.writerow(["表2 相关分析（r, 双尾）"])
        w.writerow(["变量1", "变量2", "r", "p", "显著性", "N"])
        for c in corr:
            w.writerow([c["变量1"], c["变量2"], c["r"], c["p"], c["显著性"], c["N"]])
    print(f"\n三线表已导出：{output}")


# ============ 主程序 ============

def parse_scales(path):
    scales = {}
    p = Path(path)
    if not p.exists():
        print(f"⚠ 量表配置文件不存在：{path}")
        return scales
    with open(p, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, items = line.split("=", 1)
            scales[name.strip()] = [it.strip() for it in items.split(",") if it.strip()]
    return scales


def main():
    parser = argparse.ArgumentParser(description="自动化统计分析工具（心理学问卷）")
    parser.add_argument("data", help="CSV数据文件")
    parser.add_argument("--scales", help="量表配置文件（算信度用）")
    parser.add_argument("--y", help="回归因变量列名")
    parser.add_argument("--x", help="回归自变量列名，逗号分隔")
    parser.add_argument("--profile", action="store_true", help="只输出数据画像")
    parser.add_argument("--output", "-o", help="三线表输出路径")
    args = parser.parse_args()

    path = Path(args.data)
    if not path.exists():
        print(f"错误：文件不存在 {args.data}")
        sys.exit(1)

    print("=" * 60)
    print("自动化统计分析工具（心理学问卷研究）")
    print("=" * 60)

    headers, data = read_data(str(path))
    matrix = to_float_matrix(headers, data)
    num_cols = numeric_columns(matrix, headers)

    data_profile(headers, data, matrix, num_cols)
    if args.profile:
        return

    desc = descriptive(matrix, num_cols)

    rel = []
    if args.scales:
        scales = parse_scales(args.scales)
        rel = reliability_analysis(matrix, scales)

    corr = correlation_matrix(matrix, num_cols)

    if args.y and args.x:
        x_cols = [c.strip() for c in args.x.split(",")]
        print("\n" + "=" * 60)
        print("五、回归分析")
        print("=" * 60)
        linear_regression(matrix, x_cols, args.y)

    output = args.output or str(path.with_name(path.stem + "_统计结果.csv"))
    export_three_line_table(desc, corr, output)

    print("\n" + "=" * 60)
    print("分析完成。提示：")
    print("- 中介/链式中介请用JASP或SPSS的PROCESS（模型4/6）")
    print("- 建议用量表总分（而非单个题目）做相关和回归")
    print("- 结果需人工核对，p值为近似计算，精确值以SPSS/JASP为准")


if __name__ == "__main__":
    main()
