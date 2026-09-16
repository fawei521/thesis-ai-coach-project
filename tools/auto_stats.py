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

进阶（反向题与量表点数）：
  - 题目后加 (R) 或 * 表示反向题，算α和总分前会自动反向计分（5点：6-原值）
  - 量表名后用 :点数 指定是几点量表（默认5点），反向计分=点数+1-原值
  示例：
  孤独感:5=ULS1,ULS2(R),ULS3,ULS4(R),ULS5
  生活满意度:7=LS1,LS2*,LS3

提供 --scales 时会：
  1) 对反向题计分后再算 Cronbach's α（否则含反向题的α是错的）
  2) 自动计算每个量表的总分/均分，导出“_量表总分.csv”（供JASP/SPSS/PROCESS直接用）
  3) 描述统计、相关、回归在“量表总分”层面进行（论文表1表2用这个）
"""

import csv
import sys
import re
import math
import random
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


def recoded_item_series(matrix, conf):
    """返回某量表【反向计分后】的题目数据（与可用题目同序），缺失保持None。"""
    likert = conf.get("likert", 5)
    reverse = conf.get("reverse", {})
    out = []
    for it in conf["items"]:
        if it not in matrix:
            continue
        col = []
        for v in matrix[it]:
            if v is None:
                col.append(None)
            elif reverse.get(it):
                col.append(float(likert + 1 - v))
            else:
                col.append(float(v))
        out.append(col)
    return out


def build_scale_scores(matrix, scales):
    """用反向计分后的题目计算每个量表的总分/均分。
    返回 score_matrix：{“量表总分”:[...], “量表均分”:[...]}；题目有缺失则该样本为None。"""
    n = len(next(iter(matrix.values()))) if matrix else 0
    score_matrix = {}
    for name, conf in scales.items():
        available = [it for it in conf["items"] if it in matrix]
        rec = recoded_item_series(matrix, conf) if available else []
        totals, means = [], []
        for i in range(n):
            vals = [rec[j][i] for j in range(len(rec)) if rec[j][i] is not None]
            if len(rec) >= 2 and len(vals) == len(rec):
                totals.append(round(sum(vals), 3))
                means.append(round(sum(vals) / len(vals), 3))
            else:
                totals.append(None)
                means.append(None)
        score_matrix[f"{name}总分"] = totals
        score_matrix[f"{name}均分"] = means
    return score_matrix, n


def reliability_analysis(matrix, scales_config):
    print("\n" + "=" * 60)
    print("三、信度分析（Cronbach's α，反向题已先反向计分）")
    print("=" * 60)
    if not scales_config:
        print("未提供量表配置，跳过。")
        print("配置方法：创建scales.txt，每行写 量表名=题1,题2,题3；反向题加(R)")
        return []

    results = []
    for scale_name, conf in scales_config.items():
        items = conf["items"]
        reverse = conf.get("reverse", {})
        likert = conf.get("likert", 5)
        available = [it for it in items if it in matrix]
        missing_items = [it for it in items if it not in matrix]
        if missing_items:
            print(f"⚠ {scale_name}：以下题目在数据中找不到：{missing_items}")
        if len(available) < 2:
            print(f"✗ {scale_name}：可用题目不足2个，无法计算α")
            continue
        # 关键：反向计分后的题目数据
        items_data = recoded_item_series(matrix, conf)
        alpha = cronbach_alpha(items_data)

        # 删题后α
        item_alphas = {}
        for idx in range(len(available)):
            rest = [items_data[j] for j in range(len(available)) if j != idx]
            item_alphas[available[idx]] = cronbach_alpha(rest)

        rev_names = [it for it in available if reverse.get(it)]
        rev_tip = f"，反向题{len(rev_names)}道已按{likert}点反转" if rev_names else ""
        if alpha is not None:
            rating = "优秀" if alpha >= 0.9 else "良好" if alpha >= 0.8 else "可接受" if alpha >= 0.7 else "偏低，需检查"
            print(f"\n{scale_name}（{len(available)}题{rev_tip}）：α = {alpha:.3f}  [{rating}]")
            for it in available:
                a = item_alphas[it]
                rtag = "(反向)" if reverse.get(it) else ""
                flag = " ← 删题后α升高，考虑删除" if a and alpha and a > alpha + 0.02 else ""
                print(f"    {it}{rtag}：删题后α = {a:.3f}{flag}")
            results.append({"量表": scale_name, "题数": len(available),
                            "Cronbach_alpha": round(alpha, 3), "评价": rating})
    return results


def export_scale_dataset(src_path, headers, data, score_matrix, scales):
    """导出含量表总分/均分的分析数据集（保留原始所有列），供JASP/SPSS/PROCESS使用。"""
    out_path = src_path.with_name(src_path.stem + "_量表总分.csv")
    new_cols = []
    for name in scales:
        new_cols += [f"{name}总分", f"{name}均分"]
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers + new_cols)
        for i, row in enumerate(data):
            extra = []
            for c in new_cols:
                v = score_matrix[c][i]
                extra.append("" if v is None else v)
            w.writerow(row + extra)
    return out_path


def first_pc_variance_ratio(item_cols_data):
    """Harman单因子检验：对题目做未旋转主成分分析，返回第一主成分方差解释率。
    基于相关矩阵（题目先z标准化），用幂迭代求最大特征值λ1，
    第一因子解释率 = λ1 / 题目数（相关矩阵迹=题目数）。"""
    p = len(item_cols_data)
    if p < 2:
        return None
    # 列表删除缺失行
    rows = [i for i in range(len(item_cols_data[0]))
            if all(c[i] is not None for c in item_cols_data)]
    n = len(rows)
    if n < 3:
        return None
    # z标准化
    Z = []
    for col in item_cols_data:
        vals = [col[i] for i in rows]
        m = sum(vals) / n
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1)) if n > 1 else 0
        Z.append([(v - m) / sd if sd > 0 else 0.0 for v in vals])
    # 相关矩阵
    R = [[0.0] * p for _ in range(p)]
    for a in range(p):
        for b in range(a, p):
            r = sum(Z[a][i] * Z[b][i] for i in range(n)) / (n - 1) if n > 1 else 0
            R[a][b] = r
            R[b][a] = r
    # 幂迭代求最大特征值
    vec = [1.0 / math.sqrt(p)] * p
    lam = 0.0
    for _ in range(1000):
        nv = [sum(R[a][b] * vec[b] for b in range(p)) for a in range(p)]
        norm = math.sqrt(sum(x * x for x in nv))
        if norm < 1e-12:
            break
        nv = [x / norm for x in nv]
        new_lam = sum(nv[a] * sum(R[a][b] * nv[b] for b in range(p)) for a in range(p))
        vec = nv
        if abs(new_lam - lam) < 1e-10:
            lam = new_lam
            break
        lam = new_lam
    return lam / p


def harman_test(matrix, scales):
    """共同方法偏差Harman单因子检验：所有量表题目（反向计分后）一起做未旋转因子分析。"""
    print("\n" + "=" * 60)
    print("共同方法偏差检验（Harman单因子）")
    print("=" * 60)
    item_cols, item_names = [], []
    for name, conf in scales.items():
        rec = recoded_item_series(matrix, conf)
        avail = [it for it in conf["items"] if it in matrix]
        for idx, it in enumerate(avail):
            item_cols.append(rec[idx])
            item_names.append(it)
    if len(item_cols) < 2:
        print("题目不足，跳过。")
        return None
    ratio = first_pc_variance_ratio(item_cols)
    if ratio is None:
        print("有效样本不足，跳过。")
        return None
    pct = ratio * 100
    verdict = "不严重（<40%），可接受" if pct < 40 else "超过40%，需在讨论中说明并强调程序控制"
    print(f"纳入题目数：{len(item_cols)}（反向题已先反向计分）")
    print(f"第一公因子方差解释率：{pct:.2f}%")
    print(f"判断标准：<40% 即共同方法偏差不严重")
    print(f"结论：{verdict}")
    print("论文表述：Harman单因子检验显示，第一公因子解释率为XX%，低于40%临界值，")
    print("          表明本研究不存在严重的共同方法偏差。")
    return round(pct, 2)


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


def _ols_beta(y, Xpred):
    """最小二乘系数，返回 [截距, 预测变量1系数, ...]。Xpred为预测变量列的列表。"""
    n = len(y)
    X = [[1.0] + [Xpred[j][i] for j in range(len(Xpred))] for i in range(n)]
    return solve_least_squares(X, y)


def _z(vals):
    n = len(vals)
    m = sum(vals) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1)) if n > 1 else 0
    return [(v - m) / sd if sd > 0 else 0.0 for v in vals]


def _mediation_effects(x, ms, y, idx):
    """对给定样本索引计算中介效应。ms长度1=简单中介(模型4)，长度2=链式中介(模型6)。"""
    gx = [x[i] for i in idx]
    gy = [y[i] for i in idx]
    gms = [[m[i] for i in idx] for m in ms]
    eff = {}
    eff["c(总效应)"] = _ols_beta(gy, [gx])[1]
    if len(gms) == 1:
        m1 = gms[0]
        eff["a(X→M)"] = _ols_beta(m1, [gx])[1]
        bY = _ols_beta(gy, [gx, m1])
        eff["c'(直接效应)"] = bY[1]
        eff["b(M→Y)"] = bY[2]
        eff["间接(a*b)"] = eff["a(X→M)"] * eff["b(M→Y)"]
    else:
        m1, m2 = gms[0], gms[1]
        eff["a1(X→M1)"] = _ols_beta(m1, [gx])[1]
        r2 = _ols_beta(m2, [gx, m1])
        eff["a2(X→M2)"] = r2[1]
        eff["d21(M1→M2)"] = r2[2]
        rY = _ols_beta(gy, [gx, m1, m2])
        eff["c'(直接效应)"] = rY[1]
        eff["b1(M1→Y)"] = rY[2]
        eff["b2(M2→Y)"] = rY[3]
        eff["间接:X→M1→Y(a1*b1)"] = eff["a1(X→M1)"] * eff["b1(M1→Y)"]
        eff["间接:X→M2→Y(a2*b2)"] = eff["a2(X→M2)"] * eff["b2(M2→Y)"]
        eff["间接:链式X→M1→M2→Y"] = eff["a1(X→M1)"] * eff["d21(M1→M2)"] * eff["b2(M2→Y)"]
        eff["间接合计"] = (eff["间接:X→M1→Y(a1*b1)"] + eff["间接:X→M2→Y(a2*b2)"]
                          + eff["间接:链式X→M1→M2→Y"])
    return eff


def mediation_analysis(matrix, x_col, m_cols, y_col, reps=5000, seed=20260917, output=None):
    """Bootstrap中介分析（模型4简单中介 / 模型6链式中介），百分位95%CI。"""
    cols = [x_col] + m_cols + [y_col]
    missing = [c for c in cols if c not in matrix]
    if missing:
        print(f"✗ 中介分析失败，以下列不存在：{missing}")
        return None
    rows = [i for i in range(len(matrix[x_col]))
            if all(matrix[c][i] is not None for c in cols)]
    n = len(rows)
    if n < 30:
        print(f"⚠ 有效样本仅{n}（<30），Bootstrap结果不稳定，建议加大样本。")
    x = [matrix[x_col][i] for i in rows]
    y = [matrix[y_col][i] for i in rows]
    ms = [[matrix[m][i] for i in rows] for m in m_cols]

    model = "模型6（链式中介）" if len(m_cols) == 2 else "模型4（简单中介）"
    print("\n" + "=" * 60)
    print(f"六、Bootstrap中介分析（PROCESS {model}）")
    print("=" * 60)
    print(f"X={x_col}  中介={'→'.join(m_cols)}  Y={y_col}")
    print(f"N={n}，Bootstrap={reps}次，95%置信区间（百分位法），随机种子={seed}")

    point = _mediation_effects(x, ms, y, list(range(n)))

    # 标准化点估计（路径展示用β）
    zx, zy, zms = _z(x), _z(y), [_z(m) for m in ms]
    zpoint = _mediation_effects(zx, zms, zy, list(range(n)))

    rng = random.Random(seed)
    boots = {k: [] for k in point}
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        e = _mediation_effects(x, ms, y, idx)
        for k in boots:
            boots[k].append(e[k])

    def ci(k):
        s = sorted(boots[k])
        lo = s[int(0.025 * reps)]
        hi = s[int(0.975 * reps) - 1]
        return lo, hi

    def sig(lo, hi):
        return "显著（CI不含0）" if (lo > 0 or hi < 0) else "不显著（CI含0）"

    print("\n路径系数（点估计；括号内为标准化β）：")
    path_keys = [k for k in point if not k.startswith("间接")]
    for k in path_keys:
        print(f"  {k:<16} B={point[k]:.3f}   β={zpoint[k]:.3f}")

    print("\n中介效应分解（未标准化，Bootstrap 95%CI）：")
    rows_out = []
    ind_keys = [k for k in point if k.startswith("间接")]
    for k in ind_keys + ["c'(直接效应)", "c(总效应)"]:
        lo, hi = ci(k)
        se = (sum((v - point[k]) ** 2 for v in boots[k]) / (reps - 1)) ** 0.5
        mark = "★" if k.startswith("间接") and (lo > 0 or hi < 0) else " "
        print(f"  {mark}{k:<22} 效应={point[k]:.3f}  BootSE={se:.3f}  "
              f"95%CI=[{lo:.3f}, {hi:.3f}]  {sig(lo, hi) if k.startswith('间接') else ''}")
        rows_out.append({"效应": k, "效应值": round(point[k], 3), "BootSE": round(se, 3),
                         "CI下限": round(lo, 3), "CI上限": round(hi, 3),
                         "显著性": sig(lo, hi) if k.startswith("间接") else ""})

    # 结论
    if len(m_cols) == 1:
        lo, hi = ci("间接(a*b)")
        ind_sig = lo > 0 or hi < 0
        direct_lo, direct_hi = ci("c'(直接效应)")
        direct_sig = direct_lo > 0 or direct_hi < 0
        if ind_sig and not direct_sig:
            kind = "完全中介（间接效应显著、直接效应不显著）"
        elif ind_sig and direct_sig:
            kind = "部分中介（间接、直接效应均显著）"
        else:
            kind = "中介效应不显著"
        print(f"\n结论：{kind}。")
    else:
        chain_lo, chain_hi = ci("间接:链式X→M1→M2→Y")
        print(f"\n链式中介路径X→M1→M2→Y：{sig(chain_lo, chain_hi)}。")
    print("提示：脚本用于快速预览，正式结果建议用JASP/SPSS PROCESS复核（含偏差校正CI）。")

    if output:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["效应", "效应值", "BootSE", "CI下限", "CI上限", "显著性"])
            w.writeheader()
            w.writerows(rows_out)
        print(f"中介效应表已导出：{output}")
    return rows_out


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
    """解析量表配置，返回 {名称: {"items":[...], "reverse":{题:True}, "likert":点数}}。
    格式：
      量表名=题1,题2,题3
      量表名:5=题1,题2(R),题3*       # :5 指定5点(默认)，(R)或*标记反向题
      量表名:7=题1,题2(R)
    """
    scales = {}
    p = Path(path)
    if not p.exists():
        print(f"⚠ 量表配置文件不存在：{path}")
        return scales
    with open(p, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            left, right = line.split("=", 1)
            left = left.strip()
            likert = 5
            m = re.match(r"^(.+?)\s*[:：]\s*(\d+)$", left)
            if m:
                left = m.group(1).strip()
                likert = int(m.group(2))
            items, reverse = [], {}
            for tok in right.split(","):
                tok = tok.strip()
                if not tok:
                    continue
                is_rev = False
                if tok.endswith("(R)") or tok.endswith("（R）") or tok.endswith("(r)") or tok.endswith("*"):
                    is_rev = True
                    tok = (tok.replace("(R)", "").replace("（R）", "")
                              .replace("(r)", "").rstrip("*").strip())
                if tok:
                    items.append(tok)
                    if is_rev:
                        reverse[tok] = True
            if left and items:
                scales[left] = {"items": items, "reverse": reverse, "likert": likert}
    return scales


def resolve_col(name, scales, matrix):
    """学生可能传量表名或具体列名；传量表名时映射到其总分列。"""
    name = name.strip()
    if name in matrix:
        return name
    if scales and name in scales:
        return f"{name}总分"
    if name.endswith("总分") or name.endswith("均分"):
        return name
    return name


def main():
    parser = argparse.ArgumentParser(description="自动化统计分析工具（心理学问卷）")
    parser.add_argument("data", help="CSV数据文件")
    parser.add_argument("--scales", help="量表配置文件（算信度用）")
    parser.add_argument("--y", help="回归/中介因变量列名（可传量表名）")
    parser.add_argument("--x", help="回归自变量列名，逗号分隔（中介时只取第一个作X）")
    parser.add_argument("--mediators", help="中介变量，逗号分隔；1个=模型4简单中介，2个=模型6链式中介")
    parser.add_argument("--boot", type=int, default=5000, help="Bootstrap次数（默认5000）")
    parser.add_argument("--seed", type=int, default=20260917, help="Bootstrap随机种子（默认固定，可复现）")
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

    scales = parse_scales(args.scales) if args.scales else {}

    # 有量表配置：反向计分→信度→量表总分→在总分层面做描述/相关/回归
    if scales:
        rel = reliability_analysis(matrix, scales)
        harman_test(matrix, scales)
        score_matrix, _ = build_scale_scores(matrix, scales)
        scale_total_cols = [f"{name}总分" for name in scales]
        dataset = export_scale_dataset(path, headers, data, score_matrix, scales)
        print(f"\n含量表总分的分析数据集已导出：{dataset}")
        print("  （JASP/SPSS做中介、PROCESS时直接打开这个文件，用各量表“总分”列）")

        print("\n" + "=" * 60)
        print("量表总分层面的描述统计与相关分析")
        print("=" * 60)
        desc = descriptive(score_matrix, scale_total_cols)
        corr = correlation_matrix(score_matrix, scale_total_cols)

        if args.y and args.x:
            y_col = resolve_col(args.y, scales, score_matrix)
            x_cols = [resolve_col(c, scales, score_matrix) for c in args.x.split(",")]
            print("\n" + "=" * 60)
            print("五、回归分析（量表总分层面）")
            print("=" * 60)
            linear_regression(score_matrix, x_cols, y_col)
        active_matrix = score_matrix
    else:
        # 无量表配置：保持题目级全量分析（原行为）
        print("\n提示：提供 --scales 量表配置后，将自动反向计分、算量表总分并在总分层面分析。")
        desc = descriptive(matrix, num_cols)
        corr = correlation_matrix(matrix, num_cols)
        if args.y and args.x:
            x_cols = [c.strip() for c in args.x.split(",")]
            print("\n" + "=" * 60)
            print("五、回归分析")
            print("=" * 60)
            linear_regression(matrix, x_cols, args.y)
        active_matrix = matrix

    output = args.output or str(path.with_name(path.stem + "_统计结果.csv"))
    export_three_line_table(desc, corr, output)

    # 中介分析（模型4/6，Bootstrap）
    if args.mediators and args.y and args.x:
        x_first = resolve_col(args.x.split(",")[0], scales, active_matrix)
        y_col = resolve_col(args.y, scales, active_matrix)
        m_cols = [resolve_col(c, scales, active_matrix) for c in args.mediators.split(",")]
        if len(m_cols) > 2:
            print("\n⚠ 链式中介最多支持2个中介变量（模型6），已取前两个。")
            m_cols = m_cols[:2]
        med_out = str(path.with_name(path.stem + "_中介效应.csv"))
        mediation_analysis(active_matrix, x_first, m_cols, y_col,
                           reps=args.boot, seed=args.seed, output=med_out)

    print("\n" + "=" * 60)
    print("分析完成。提示：")
    print("- 已用 --mediators 自动做Bootstrap中介；正式结果建议JASP/SPSS PROCESS复核")
    print("- 反向题已按scales.txt的(R)标记处理；请核对反向题是否标对")
    print("- 结果需人工核对，p值为近似计算，精确值以SPSS/JASP为准")


if __name__ == "__main__":
    main()
