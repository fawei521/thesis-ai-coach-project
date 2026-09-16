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
import os
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


def skew_kurt(values):
    """SPSS/Excel 口径的调整偏度 G1 与超额峰度 G2（Fisher-Pearson 近似无偏）。
    用样本标准差(ddof=1)标准化；n<3 偏度为 None，n<4 峰度为 None。"""
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n < 3:
        return None, None
    m = mean(vals)
    sd = stdev(vals)
    if sd == 0:
        return None, None
    z = [(x - m) / sd for x in vals]
    s3 = sum(t ** 3 for t in z)
    g1 = n / ((n - 1) * (n - 2)) * s3
    g2 = None
    if n >= 4:
        g2 = (n * (n + 1)) / ((n - 1) * (n - 2) * (n - 3)) * sum(t ** 4 for t in z) \
             - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
    return g1, g2


def normality_tag(g1, g2):
    """社科常用 Kline 判据：|偏度|<3 且 |峰度|<10 视为不严重偏离正态。"""
    if g1 is None or g2 is None:
        return "样本不足"
    if abs(g1) < 3 and abs(g2) < 10:
        return "可接受(|S|<3,|K|<10)"
    return "偏离正态，用Bootstrap/稳健法"


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
    """读取CSV，自动兼容UTF-8(含BOM)与GBK/GB18030（问卷星等中文导出常见编码）。"""
    last_err = None
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            with open(filepath, "r", encoding=enc, newline="") as f:
                rows = list(csv.reader(f))
            if rows:
                return rows[0], rows[1:]
            return [], []
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    print(f"错误：无法识别文件编码，请先用菜单第1项预处理，或把CSV另存为UTF-8。({last_err})")
    sys.exit(1)


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


def frequency_analysis(headers, data, matrix, scales, output=None):
    """人口学/分类变量频数分析。自动识别量表题目之外、取值种类≤10的列
    （性别、年级、生源地、是否独生子女、专业等，兼容文本和1/2编码），
    输出频数与百分比并导出，供论文“研究对象/样本构成”部分直接使用。"""
    scale_items = set()
    for conf in scales.values():
        scale_items.update(conf["items"])

    sections = []
    table_rows = []
    for ci, c in enumerate(headers):
        if c in scale_items:
            continue
        col = matrix.get(c, [])
        if any(v is not None for v in col):
            vals = [v for v in col if v is not None]
            numeric = True
        else:
            vals = []
            for r in data:
                if ci < len(r):
                    t = r[ci].strip()
                    if t:
                        vals.append(t)
            numeric = False
        if not vals:
            continue
        uniq = set(vals)
        # 文本分类列（性别/生源地等）取值≤10类；数值编码列（性别1/2、年级1-4）取值≤4类，
        # 以排除5点/7点Likert题（量表题另外已通过scale_items排除）
        max_cat = 10 if not numeric else 4
        if len(uniq) > max_cat:
            continue
        n = len(vals)
        counts = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        keys = sorted(counts) if numeric else sorted(counts, key=lambda k: -counts[k])
        lines = []
        for k in keys:
            pct = counts[k] / n * 100
            label = str(int(k)) if numeric and float(k).is_integer() else str(k)
            lines.append(f"    {label}：{counts[k]}人（{pct:.1f}%）")
            table_rows.append({"变量": c, "取值": label, "频数": counts[k],
                               "百分比%": round(pct, 1)})
        sections.append((c, n, lines))

    if not sections:
        return None
    print("\n" + "=" * 60)
    print("研究对象（人口学/分类变量频数）")
    print("=" * 60)
    for c, n, lines in sections:
        print(f"\n{c}（N={n}）")
        for ln in lines:
            print(ln)
    if output:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["变量", "取值", "频数", "百分比%"])
            w.writeheader()
            w.writerows(table_rows)
        print(f"\n频数表已导出：{output}")
    return table_rows


def _detect_group_cols(headers, data, matrix, scales):
    """识别人口学分组列（非量表题、2类及以上且数值≤4类/文本≤10类），
    返回 [(列名, 每样本组标签序列(缺失None))]。"""
    scale_items = set()
    for conf in scales.values():
        scale_items.update(conf["items"])
    out = []
    for ci, c in enumerate(headers):
        if c in scale_items:
            continue
        col = matrix.get(c)
        labels, numeric = [], True
        if col and any(v is not None for v in col):
            for v in col:
                if v is None:
                    labels.append(None)
                else:
                    labels.append(str(int(v)) if float(v).is_integer() else str(v))
        else:
            numeric = False
            for r in data:
                t = r[ci].strip() if ci < len(r) else ""
                labels.append(t if t else None)
        vals = [x for x in labels if x is not None]
        if not vals:
            continue
        uniq = set(vals)
        max_cat = 10 if not numeric else 4
        if 2 <= len(uniq) <= max_cat:
            out.append((c, labels))
    return out


def _cohens_d(a, b):
    n1, n2 = len(a), len(b)
    v1, v2 = variance(a), variance(b)
    sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)
    if sp2 <= 0:
        return None
    return (mean(a) - mean(b)) / math.sqrt(sp2)


def _levene(groups, center="median"):
    """Levene/Brown-Forsythe 方差齐性检验。center='median' 即 Brown-Forsythe
    （更稳健、推荐），'mean' 为传统 Levene。对绝对离差做单因素 ANOVA，
    统计量服从 F(k-1, N-k)。返回 (W, p)。"""
    use = [g for g in groups if len(g) >= 2]
    k = len(use)
    if k < 2:
        return None, None
    zgroups = []
    for g in use:
        if center == "median":
            sg = sorted(g)
            m_ = len(sg)
            c = sg[m_ // 2] if m_ % 2 else (sg[m_ // 2 - 1] + sg[m_ // 2]) / 2
        else:
            c = mean(g)
        zgroups.append([abs(x - c) for x in g])
    N = sum(len(z) for z in zgroups)
    grand_z = sum(sum(z) for z in zgroups) / N
    ssb = sum(len(z) * (mean(z) - grand_z) ** 2 for z in zgroups)
    ssw = sum(sum((x - mean(z)) ** 2 for x in z) for z in zgroups)
    dfb, dfw = k - 1, N - k
    if dfw <= 0 or ssw <= 0:
        return None, None
    W = (ssb / dfb) / (ssw / dfw)
    return W, f_p_value(W, dfb, dfw)


def _welch_t(a, b):
    """Welch 独立样本 t（不要求等方差），返回 (t, df, p)。"""
    n1, n2 = len(a), len(b)
    v1, v2 = variance(a), variance(b)
    a1, a2 = v1 / n1, v2 / n2
    se2 = a1 + a2
    if se2 <= 0:
        return None, None, None
    t = (mean(a) - mean(b)) / math.sqrt(se2)
    df = se2 ** 2 / (a1 ** 2 / (n1 - 1) + a2 ** 2 / (n2 - 1))
    return t, df, t_p_two_sided(t, df)


def _welch_anova(groups):
    """Welch 单因素方差分析（不要求等方差），返回 (F, df1, df2, p)。
    公式见 Liu (2015) / R oneway.test。"""
    use = [g for g in groups if len(g) >= 2]
    k = len(use)
    if k < 2:
        return None, None, None, None
    w = [len(g) / variance(g) if variance(g) > 0 else 0.0 for g in use]
    wtot = sum(w)
    if wtot <= 0:
        return None, None, None, None
    xw = sum(w[j] * mean(use[j]) for j in range(k)) / wtot
    num = sum(w[j] * (mean(use[j]) - xw) ** 2 for j in range(k)) / (k - 1)
    D = sum((1.0 / (len(use[j]) - 1)) * (1.0 - w[j] / wtot) ** 2
            for j in range(k))
    den = 1.0 + 2.0 * (k - 2) / (k ** 2 - 1) * D
    F = num / den
    df1 = k - 1
    df2 = (k ** 3 - k) / (3.0 * D) if D > 0 else float("inf")
    p = f_p_value(F, df1, df2) if df2 != float("inf") else None
    return F, df1, df2, p


def group_difference_analysis(headers, data, matrix, scales, score_matrix,
                              total_cols, output=None):
    """人口学差异：2组用独立样本t检验(等方差)+Cohen's d；
    3组及以上用单因素方差分析(ANOVA)+η²+Bonferroni校正事后两两比较。
    对每个人口学分组列 × 每个量表总分进行。"""
    group_cols = _detect_group_cols(headers, data, matrix, scales)
    if not group_cols or not total_cols:
        return None
    rows = []
    print("\n" + "=" * 60)
    print("七、人口学差异分析（独立样本t / 单因素ANOVA）")
    print("=" * 60)
    for gname, glabels in group_cols:
        for ycol in total_cols:
            y = score_matrix.get(ycol)
            if not y:
                continue
            gd = {}
            for i, lab in enumerate(glabels):
                if lab is not None and i < len(y) and y[i] is not None:
                    gd.setdefault(lab, []).append(float(y[i]))
            try:
                keys = sorted(gd, key=lambda k: float(k))
            except ValueError:
                keys = sorted(gd)
            gd = {k: gd[k] for k in keys if len(gd[k]) >= 2}
            if len(gd) < 2 or len(gd) > 8:
                continue
            yshort = ycol.replace("总分", "")
            desc = "；".join(f"{k}组 M={mean(v):.2f},SD={stdev(v):.2f},n={len(v)}"
                             for k, v in gd.items())
            if len(gd) == 2:
                (k1, a), (k2, b) = list(gd.items())[0], list(gd.items())[1]
                n1, n2 = len(a), len(b)
                sp2 = ((n1 - 1) * variance(a) + (n2 - 1) * variance(b)) / (n1 + n2 - 2)
                if sp2 <= 0:
                    continue
                t = (mean(a) - mean(b)) / math.sqrt(sp2 * (1 / n1 + 1 / n2))
                df = n1 + n2 - 2
                p = t_p_two_sided(t, df)
                d = _cohens_d(a, b)
                dt = "可忽略" if abs(d) < .2 else "小" if abs(d) < .5 else "中" if abs(d) < .8 else "大"
                lw, levp = _levene([a, b])
                wt, wdf, wp = _welch_t(a, b)
                equal = (levp is None) or (levp >= .05)
                levtxt = ("Levene/Brown-Forsythe：无法计算（按方差齐处理）" if levp is None
                          else f"Levene p={fmt_p(levp)}（方差齐性{'成立' if equal else '不成立'}）")
                welchtxt = f"Welch t({wdf:.0f})={wt:.3f}, p={fmt_p(wp)}"
                if equal:
                    test_name, stat_t, df_t, p_t = "独立样本t", f"t={t:.3f}", df, p
                    rec = "方差齐，采用等方差 t 检验"
                else:
                    test_name, stat_t, df_t, p_t = "独立样本t(Welch)", f"t={wt:.3f}", round(wdf, 1), wp
                    rec = "方差不齐，采用 Welch t 检验"
                sig = "差异显著" if p_t < .05 else "差异不显著"
                print(f"\n{gname} × {yshort}（{test_name}）：{k1}组 vs {k2}组")
                print(f"    {desc}")
                print(f"    {levtxt}")
                print(f"    等方差 t({df})={t:.3f}, p={fmt_p(p)}；{welchtxt}")
                print(f"    Cohen's d={d:.3f}（{dt}效应）→ {sig}（{rec}）")
                rows.append({"分组变量": gname, "因变量": yshort, "检验": test_name,
                             "统计量": stat_t, "df": df_t, "p": fmt_p(p_t),
                             "效应量": f"d={d:.3f}({dt})",
                             "方差齐性": levtxt, "稳健检验(Welch)": welchtxt,
                             "详情": desc + f"；{sig}；{rec}"})
            else:
                keys2 = list(gd.keys())
                groups = [gd[k] for k in keys2]
                N = sum(len(g) for g in groups)
                k = len(groups)
                grand = sum(sum(g) for g in groups) / N
                ssb = sum(len(g) * (mean(g) - grand) ** 2 for g in groups)
                ssw = sum(sum((x - mean(g)) ** 2 for x in g) for g in groups)
                dfb, dfw = k - 1, N - k
                if dfw <= 0 or ssw <= 0:
                    continue
                msw = ssw / dfw
                F = (ssb / dfb) / msw
                p = f_p_value(F, dfb, dfw)
                eta = ssb / (ssb + ssw)
                et = "小" if eta < .06 else "中" if eta < .14 else "大"
                lw, levp = _levene(groups)
                Fw, wd1, wd2, wp = _welch_anova(groups)
                equal = (levp is None) or (levp >= .05)
                levtxt = ("Levene/Brown-Forsythe：无法计算（按方差齐处理）" if levp is None
                          else f"Levene p={fmt_p(levp)}（方差齐性{'成立' if equal else '不成立'}）")
                welchtxt = (f"Welch F({wd1},{wd2:.0f})={Fw:.3f}, p={fmt_p(wp)}"
                           if Fw is not None else "Welch：无法计算")
                post = []
                npairs = k * (k - 1) // 2
                for ii in range(k):
                    for jj in range(ii + 1, k):
                        ga, gb = groups[ii], groups[jj]
                        tt = (mean(ga) - mean(gb)) / math.sqrt(msw * (1 / len(ga) + 1 / len(gb)))
                        pp = t_p_two_sided(tt, dfw)
                        if pp * npairs < .05:
                            post.append(f"{keys2[ii]}组>{keys2[jj]}组" if mean(ga) > mean(gb)
                                        else f"{keys2[jj]}组>{keys2[ii]}组")
                post_txt = "；".join(post) if post else "事后两两均不显著"
                if equal:
                    test_name, stat_F, df_F, p_F = "单因素ANOVA", f"F={F:.3f}", f"{dfb},{dfw}", p
                    rec = "方差齐，采用等方差 ANOVA＋Bonferroni事后"
                    sig = "差异显著" if p < .05 else "差异不显著"
                    post_show = f"Bonferroni事后：{post_txt}"
                else:
                    test_name, stat_F, df_F, p_F = "单因素ANOVA(Welch)", f"F={Fw:.3f}", f"{wd1},{wd2:.0f}", wp
                    rec = "方差不齐，采用 Welch ANOVA；事后请用 Games-Howell（JASP/SPSS）"
                    sig = "差异显著" if (wp is not None and wp < .05) else "差异不显著"
                    post_show = "方差不齐，Bonferroni不适用，事后改用 Games-Howell（JASP：ANOVA→Games-Howell）"
                print(f"\n{gname} × {yshort}（{test_name}，{k}组）")
                print(f"    {desc}")
                print(f"    {levtxt}")
                print(f"    等方差 F({dfb},{dfw})={F:.3f}, p={fmt_p(p)}, η²={eta:.3f}（{et}效应）；{welchtxt}")
                print(f"    {post_show}")
                print(f"    → {sig}（{rec}）")
                rows.append({"分组变量": gname, "因变量": yshort, "检验": test_name,
                             "统计量": stat_F, "df": df_F, "p": fmt_p(p_F),
                             "效应量": f"η²={eta:.3f}({et})",
                             "方差齐性": levtxt, "稳健检验(Welch)": welchtxt,
                             "详情": desc + f"；{sig}；{rec}；{post_show}"})
    if output and rows:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["分组变量", "因变量", "检验", "统计量",
                                              "df", "p", "效应量", "方差齐性",
                                              "稳健检验(Welch)", "详情"])
            w.writeheader()
            w.writerows(rows)
        print(f"\n人口学差异分析表已导出：{output}")
    return rows


def descriptive(matrix, num_cols):
    print("\n" + "=" * 60)
    print("描述统计（含偏度/峰度正态性；Kline判据 |偏度|<3、|峰度|<10）")
    print("=" * 60)
    print(f"{'变量':<12}{'N':>6}{'均值':>9}{'标准差':>9}{'最小':>7}{'最大':>7}{'偏度':>8}{'峰度':>8}")
    print("-" * 70)
    results = []
    for h in num_cols:
        vals = [v for v in matrix[h] if v is not None]
        if not vals:
            continue
        m, sd = mean(vals), stdev(vals)
        g1, g2 = skew_kurt(vals)
        g1t = f"{g1:>8.2f}" if g1 is not None else f"{'NA':>8}"
        g2t = f"{g2:>8.2f}" if g2 is not None else f"{'NA':>8}"
        print(f"{h:<12}{len(vals):>6}{m:>9.3f}{sd:>9.3f}{min(vals):>7.1f}{max(vals):>7.1f}{g1t}{g2t}")
        results.append({"变量": h, "N": len(vals),
                        "均值": round(m, 3), "标准差": round(sd, 3),
                        "最小值": min(vals), "最大值": max(vals),
                        "偏度": round(g1, 3) if g1 is not None else "",
                        "峰度": round(g2, 3) if g2 is not None else "",
                        "正态性": normality_tag(g1, g2)})
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


def reliability_analysis(matrix, scales_config, item_output=None):
    print("\n" + "=" * 60)
    print("二、信度分析（Cronbach's α，反向题已先反向计分）")
    print("=" * 60)
    if not scales_config:
        print("未提供量表配置，跳过。")
        print("配置方法：创建scales.txt，每行写 量表名=题1,题2,题3；反向题加(R)")
        return []

    results = []
    all_item_rows = []
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

        kk = len(available)
        ncol = len(items_data[0]) if items_data else 0
        rev_names = [it for it in available if reverse.get(it)]
        rev_tip = f"，反向题{len(rev_names)}道已按{likert}点反转" if rev_names else ""
        if alpha is not None:
            rating = "优秀" if alpha >= 0.9 else "良好" if alpha >= 0.8 else "可接受" if alpha >= 0.7 else "偏低，需检查"
            print(f"\n{scale_name}（{kk}题{rev_tip}）：α = {alpha:.3f}  [{rating}]")
            print("    题项分析（CITC校正项总相关建议≥.40；删题后α不应高于总α）：")
            min_citc = None
            for idx, it in enumerate(available):
                rest_data = [items_data[j] for j in range(kk) if j != idx]
                a_del = cronbach_alpha(rest_data)
                rest_total = []
                for r in range(ncol):
                    vals = [items_data[j][r] for j in range(kk) if j != idx]
                    rest_total.append(sum(vals) if all(v is not None for v in vals) else None)
                citc, _ = pearson_r(items_data[idx], rest_total)
                flags = []
                if citc is not None and citc < .4:
                    flags.append("CITC<.40偏低")
                if a_del is not None and a_del > alpha + .02:
                    flags.append("删题后α升高")
                if citc is not None and (min_citc is None or citc < min_citc):
                    min_citc = citc
                rtag = "(反向)" if reverse.get(it) else ""
                citc_txt = f"{citc:.3f}" if citc is not None else "NA"
                a_txt = f"{a_del:.3f}" if a_del is not None else "NA"
                mark = "；".join(flags)
                tail = f"  ← {mark}，结合理论检查该题" if mark else ""
                print(f"    {it}{rtag}：CITC={citc_txt}，删题后α={a_txt}{tail}")
                all_item_rows.append({
                    "量表": scale_name, "题项": it + rtag,
                    "CITC校正项总相关": round(citc, 3) if citc is not None else "",
                    "删题后alpha": round(a_del, 3) if a_del is not None else "",
                    "量表alpha": round(alpha, 3), "提示": mark})
            results.append({"量表": scale_name, "题数": kk,
                            "Cronbach_alpha": round(alpha, 3),
                            "最低CITC": round(min_citc, 3) if min_citc is not None else "",
                            "评价": rating})
    if item_output and all_item_rows:
        with open(item_output, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["量表", "题项", "CITC校正项总相关",
                                              "删题后alpha", "量表alpha", "提示"])
            w.writeheader()
            w.writerows(all_item_rows)
        print(f"\n题项分析表（CITC/删题α）已导出：{item_output}")
    return results


def _first_pc(R):
    """幂迭代求相关矩阵R的最大特征值与特征向量。"""
    p = len(R)
    vec = [1.0 / math.sqrt(p)] * p
    lam = 0.0
    for _ in range(1000):
        nv = [sum(R[a][b] * vec[b] for b in range(p)) for a in range(p)]
        norm = math.sqrt(sum(x * x for x in nv))
        if norm < 1e-12:
            break
        nv = [x / norm for x in nv]
        nl = sum(nv[a] * sum(R[a][b] * nv[b] for b in range(p)) for a in range(p))
        vec = nv
        if abs(nl - lam) < 1e-10:
            lam = nl
            break
        lam = nl
    return lam, vec


def kmo_value(corr):
    """KMO抽样适合度：基于相关系数平方和与偏相关系数平方和。"""
    p = len(corr)
    try:
        inv = invert_matrix(corr)
    except Exception:
        inv = None
    if inv is None:
        return None  # 相关矩阵奇异（题目高度共线/全同或样本不足），无法算偏相关
    sum_r2 = sum_p2 = 0.0
    for i in range(p):
        for j in range(i + 1, p):
            denom = math.sqrt(inv[i][i] * inv[j][j])
            q = (-inv[i][j] / denom) if denom > 0 else 0.0
            r = corr[i][j]
            sum_r2 += r * r
            sum_p2 += q * q
    denom = sum_r2 + sum_p2
    return sum_r2 / denom if denom > 0 else None


def _eigen_sym(A, tol=1e-11, max_sweep=100):
    """对称矩阵全部特征值/特征向量（循环Jacobi法，纯标准库）。
    返回 (特征值降序列表, 向量矩阵[行=变量,列=对应特征向量])。"""
    n = len(A)
    a = [row[:] for row in A]
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_sweep):
        off = math.sqrt(sum(a[p][q] ** 2 for p in range(n) for q in range(p + 1, n)))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if abs(apq) < 1e-14:
                    continue
                app, aqq = a[p][p], a[q][q]
                tau = (aqq - app) / (2.0 * apq)
                if tau >= 0:
                    t = 1.0 / (tau + math.sqrt(1 + tau * tau))
                else:
                    t = 1.0 / (tau - math.sqrt(1 + tau * tau))
                c = 1.0 / math.sqrt(1 + t * t)
                s = t * c
                for i in range(n):  # 列旋转
                    aip, aiq = a[i][p], a[i][q]
                    a[i][p] = c * aip - s * aiq
                    a[i][q] = s * aip + c * aiq
                for i in range(n):  # 行旋转
                    api, aqi = a[p][i], a[q][i]
                    a[p][i] = c * api - s * aqi
                    a[q][i] = s * api + c * aqi
                for i in range(n):  # 累积特征向量
                    vip, viq = V[i][p], V[i][q]
                    V[i][p] = c * vip - s * viq
                    V[i][q] = s * vip + c * viq
    eig = [a[i][i] for i in range(n)]
    order = sorted(range(n), key=lambda i: -eig[i])
    eig_sorted = [eig[i] for i in order]
    vecs = [[V[r][order[j]] for j in range(n)] for r in range(n)]
    return eig_sorted, vecs


def _varimax(loadings, normalize=True, max_iter=100, tol=1e-7):
    """Kaiser归一化的最大方差正交旋转（varimax，Kaiser 1958逐对旋转）。
    输入未旋转载荷[题×因子]，返回旋转后载荷（已统一符号、按解释方差降序）。"""
    p, k = len(loadings), len(loadings[0])
    if k <= 1:
        return [row[:] for row in loadings]
    h = [math.sqrt(sum(loadings[i][j] ** 2 for j in range(k))) for i in range(p)]
    X = [[loadings[i][j] / h[i] if normalize and h[i] > 1e-12 else loadings[i][j]
          for j in range(k)] for i in range(p)]

    def v_criterion(M):
        v = 0.0
        for j in range(k):
            v += sum(M[i][j] ** 4 for i in range(p)) / p \
                - (sum(M[i][j] ** 2 for i in range(p)) / p) ** 2
        return v

    prev_v = v_criterion(X)
    for _ in range(max_iter):
        max_theta = 0.0
        for a in range(k - 1):
            for b in range(a + 1, k):
                u = [X[i][a] ** 2 - X[i][b] ** 2 for i in range(p)]
                v = [2.0 * X[i][a] * X[i][b] for i in range(p)]
                As = sum(u)
                Bs = sum(v)
                Cs = sum(u[i] ** 2 - v[i] ** 2 for i in range(p))
                Ds = 2.0 * sum(u[i] * v[i] for i in range(p))
                num = Ds - 2.0 * As * Bs / p
                den = Cs - (As * As - Bs * Bs) / p
                theta = math.atan2(num, den) / 4.0
                max_theta = max(max_theta, abs(theta))
                if abs(theta) > 1e-12:
                    c, s = math.cos(theta), math.sin(theta)
                    for i in range(p):  # 旋转方向经Wolfram/暴力扫描验证为单调上升方向
                        xa, xb = X[i][a], X[i][b]
                        X[i][a] = c * xa + s * xb
                        X[i][b] = -s * xa + c * xb
        cur_v = v_criterion(X)
        if max_theta < tol or abs(cur_v - prev_v) < 1e-10:
            break
        prev_v = cur_v
    Lr = [[X[i][j] * (h[i] if normalize else 1.0) for j in range(k)] for i in range(p)]
    # 符号统一：每列载荷和为负则翻转
    for j in range(k):
        if sum(Lr[i][j] for i in range(p)) < 0:
            for i in range(p):
                Lr[i][j] = -Lr[i][j]
    # 按旋转后各因子载荷平方和降序排列因子
    ss = [sum(Lr[i][j] ** 2 for i in range(p)) for j in range(k)]
    order = sorted(range(k), key=lambda j: -ss[j])
    Lr = [[Lr[i][order[j]] for j in range(k)] for i in range(p)]
    return Lr


def _plot_scree(name, eigvals, nfac, out_png, pa_mean=None, pa_p95=None):
    """画碎石图（Cattell scree plot）：折线+数据点+Kaiser λ=1 参考线，高亮保留因子。
    若提供 pa_mean/pa_p95（平行分析随机特征值），叠加随机均值与95%分位线。
    matplotlib 为可选依赖，未安装时返回 False（不影响数值结果）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    k = len(eigvals)
    x = list(range(1, k + 1))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, eigvals, "-", color="#9bb8d3", linewidth=1.6, zorder=2)
    ax.plot(x, eigvals, "o", color="#1f4e79", markersize=6, zorder=3, label="真实特征值")
    ax.axhline(1.0, color="#C62828", linestyle="--", linewidth=1.3, zorder=1,
               label="Kaiser 基准 λ=1")
    if pa_mean is not None:
        ax.plot(x, pa_mean, "--", color="#ef6c00", linewidth=1.3, zorder=2,
                label="平行分析 随机均值")
    if pa_p95 is not None:
        ax.plot(x, pa_p95, ":", color="#6a1b9a", linewidth=1.5, zorder=2,
                label="平行分析 随机95%分位")
    ax.plot(x[:nfac], eigvals[:nfac], "o", color="#2e7d32", markersize=12,
            markerfacecolor="none", markeredgewidth=1.8, zorder=4,
            label=f"保留 {nfac} 个因子")
    # 题数少时标注每个特征值，题数多时只标前10个避免重叠
    for xi, yi in zip(x, eigvals):
        if k <= 15 or xi <= 10:
            ax.annotate(f"{yi:.2f}", (xi, yi), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=8, color="#333")
    ax.set_xticks(x)
    ax.set_xlabel("成分序号", fontsize=11)
    ax.set_ylabel("特征值", fontsize=11)
    title = f"{name} 碎石图（Scree Plot）"
    if pa_p95 is not None:
        title += "＋平行分析"
    ax.set_title(title, fontsize=13)
    ax.set_ylim(0, max(eigvals) * 1.15)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True


def _parallel_analysis(R, n, n_rep=500, base_seed=20260917):
    """Horn 平行分析：生成 n_rep 个与原数据同 N、同题数、题间独立的随机数据，
    求每个位置特征值的均值与95%分位；真实特征值超过随机95%分位的连续成分数即建议因子数。
    返回 real/mean/p95 特征值与按均值、按95%分位的建议因子数（95%更保守，Glorfeld 1995）。"""
    k = len(R)
    real, _ = _eigen_sym(R)
    sims = []
    for i in range(n_rep):
        rng = random.Random(base_seed + i + 1)
        Z = []
        for _a in range(k):
            col = [rng.gauss(0.0, 1.0) for _ in range(n)]
            mm = sum(col) / n
            sd = math.sqrt(sum((x - mm) ** 2 for x in col) / (n - 1))
            Z.append([(x - mm) / sd if sd > 0 else 0.0 for x in col])
        M = [[0.0] * k for _ in range(k)]
        for a in range(k):
            za = Z[a]
            for b in range(a, k):
                rr = sum(za[j] * Z[b][j] for j in range(n)) / (n - 1)
                M[a][b] = rr
                M[b][a] = rr
        ev, _ = _eigen_sym(M)
        sims.append(ev)
    mean_e, p95_e = [], []
    for j in range(k):
        col = sorted(s[j] for s in sims)
        mean_e.append(sum(col) / n_rep)
        p95_e.append(col[min(n_rep - 1, int(0.95 * n_rep))])

    def _count(thr):
        c = 0
        for j in range(k):
            if real[j] > thr[j]:
                c = j + 1
            else:
                break
        return c

    return {"real": real, "mean": mean_e, "p95": p95_e,
            "nfac_mean": _count(mean_e), "nfac_p95": _count(p95_e)}


def _safe_filename(s):
    """去掉 Windows 文件名非法字符。"""
    return "".join(c for c in s if c not in '\\/:*?"<>|').strip().rstrip(".") or "量表"


def _efa_one(name, items, conf, Z, R, n, pa_rep=500):
    """对单个量表做完整探索性因子分析（PCA提取+varimax旋转），打印并返回结果行。"""
    k = len(items)
    kmo = kmo_value(R)
    if kmo is None:
        print(f"\n{'─' * 58}")
        print(f"【完整EFA】{name}（{k}题，N={n}）：相关矩阵奇异，无法做因子分析。")
        print("  常见原因：有题目高度雷同/所有作答全同、有效样本过少或题目数超过样本数。")
        print("  请先做数据清洗、检查题目，再重跑。")
        return None
    det = determinant(R)
    dfb = k * (k - 1) / 2
    if det > 1e-300:
        chi2 = -(n - 1 - (2 * k + 5) / 6.0) * math.log(det)
        pval = chi2_pvalue(chi2, dfb)
    else:
        chi2, pval = float("inf"), 0.0

    eigvals, eigvecs = _eigen_sym(R)
    nfac = sum(1 for e in eigvals if e >= 1.0)
    nfac = max(1, min(nfac, k))
    # 未旋转载荷（主成分）：L0[:,j]=v_j*sqrt(λ_j)
    L0 = [[eigvecs[i][j] * math.sqrt(max(eigvals[j], 0)) for j in range(nfac)]
          for i in range(k)]
    # 共同度（提取nfac个因子，正交旋转不变）
    comm = [sum(L0[i][j] ** 2 for j in range(nfac)) for i in range(k)]
    Lr = _varimax(L0, normalize=True) if nfac > 1 else [[L0[i][0]] for i in range(k)]
    ss = [sum(Lr[i][j] ** 2 for i in range(k)) for j in range(nfac)]

    kmo_txt = f"{kmo:.3f}" if kmo is not None else "无法计算"
    if kmo is not None:
        rate = "极佳" if kmo >= .9 else "适合" if kmo >= .8 else "可接受" if kmo >= .7 \
            else "勉强(需谨慎)" if kmo >= .6 else "不适合因子分析"
    else:
        rate = ""
    bart = "p<.001" if pval < .001 else f"p={pval:.3f}"
    print(f"\n{'─' * 58}")
    print(f"【完整EFA】{name}（{k}题，N={n}）  提取：主成分分析  旋转：最大方差法Varimax")
    print(f"  KMO = {kmo_txt}  [{rate}]；Bartlett球形检验：χ²={chi2:.1f}"
          f"（df={int(dfb)}），{bart}（需p<.05）")
    ratio = n / k
    if ratio < 5:
        print(f"  ⚠ 样本量/题数={ratio:.1f}，偏少（建议≥5，理想≥10，N≥200），结果可能不稳定")
    # 特征值/碎石
    eig_str = "，".join(f"λ{i+1}={eigvals[i]:.2f}" for i in range(min(k, 8)))
    print(f"  特征值（Kaiser准则保留≥1，共{nfac}个）：{eig_str}" + ("…" if k > 8 else ""))
    pa = None
    if pa_rep and pa_rep > 0:
        print(f"  平行分析(Horn)模拟中（{pa_rep}次随机数据，约数秒）…")
        pa = _parallel_analysis(R, n, pa_rep)
        show = min(k, max(nfac + 2, 5))
        print("    成分   真实λ / 随机均值 / 随机95%分位")
        for j in range(show):
            keep = "保留" if pa["real"][j] > pa["p95"][j] else "—"
            print(f"     {j+1:>2}    {pa['real'][j]:5.2f} / {pa['mean'][j]:5.2f} / "
                  f"{pa['p95'][j]:5.2f}   {keep}")
        print(f"    →平行分析建议保留 {pa['nfac_p95']} 个因子（95%分位准则，更保守）；"
              f"均值准则 {pa['nfac_mean']} 个")
    # 总方差解释（旋转后）
    cum = 0.0
    var_line = []
    for j in range(nfac):
        pct = ss[j] / k * 100
        cum += pct
        var_line.append(f"因子{j+1}={pct:.1f}%")
    print(f"  旋转后方差解释率：{'，'.join(var_line)}；累计={cum:.1f}%"
          f"（社会科学建议≥50%~60%）")
    # 旋转载荷矩阵
    header = "  题项".ljust(10) + "".join(f"因子{j+1}".rjust(9) for j in range(nfac)) \
        + "共同度".rjust(8) + "  归属/提示"
    print(header)
    rows = []
    for i, it in enumerate(items):
        vals = [Lr[i][j] for j in range(nfac)]
        order_abs = sorted(range(nfac), key=lambda j: -abs(vals[j]))
        top, second = order_abs[0], order_abs[1] if nfac > 1 else None
        tag = "(反向)" if conf["reverse"].get(it) else ""
        flags = []
        if abs(vals[top]) < .4:
            flags.append("载荷<.4，考虑删题")
        if second is not None and abs(vals[second]) >= .4 and \
                abs(vals[top]) - abs(vals[second]) < .2:
            flags.append(f"交叉载荷(因子{top+1}/因子{second+1})")
        note = f"→因子{top+1}" + ("；" + "；".join(flags) if flags else "")
        cells = "".join(f"{vals[j]:9.3f}" for j in range(nfac))
        print(f"  {it[:8]}{tag}".ljust(10) + cells + f"{comm[i]:8.3f}  {note}")
        row = {"量表": name, "题项": it + tag}
        for j in range(nfac):
            row[f"因子{j+1}载荷"] = round(vals[j], 3)
        row["共同度"] = round(comm[i], 3)
        row["归属因子"] = top + 1
        row["提示"] = "；".join(flags)
        rows.append(row)
    if cum < 50:
        print("  ⚠ 累计方差解释率低于50%，结构解释力偏弱，需检查题目或因子数")
    if pa is not None:
        print(f"  因子数三依据：Kaiser特征值≥1→{nfac}个；碎石拐点→见碎石图；"
              f"平行分析→{pa['nfac_p95']}个。三者不一致时结合理论、优先平行分析，"
              f"并在JASP固定因子数复核。")
    print("  注：脚本用于快速预览/教学；碎石图"
          + ("（含平行分析线）" if pa is not None else "") + "已随结果导出PNG。")
    print("      固定因子数、斜交promax旋转、CFA验证性因子分析请在JASP/SPSS复核。")
    return {"量表": name, "题数": k, "N": n, "KMO": round(kmo, 3) if kmo else "",
            "Bartlett_p": "<.001" if pval < .001 else round(pval, 3),
            "因子数": nfac, "累计方差%": round(cum, 2),
            "平行分析因子数": pa["nfac_p95"] if pa else "",
            "特征值": [round(e, 4) for e in eigvals],
            "PA": pa, "rows": rows}


def validity_analysis(matrix, scales, efa_names=None, efa_output=None, pa_rep=500):
    """结构效度。默认对每个量表（反向计分后题目）做单维检查：KMO、Bartlett、第一主成分载荷。
    efa_names: None=全部走单维；'__ALL__'=全部做完整EFA；集合/列表=指定量表做完整EFA
    （主成分提取+特征值≥1定因子数+varimax旋转+共同度+交叉载荷）。"""
    print("\n" + "=" * 60)
    print("三、结构效度检验（各量表内部，反向计分后题目）")
    print("=" * 60)
    if efa_names:
        print("（已开启完整探索性因子分析EFA：主成分提取 + Varimax正交旋转）")
    rows = []
    efa_summaries = []
    efa_item_rows = []
    scree_pngs = []
    scree_fail = False
    for name, conf in scales.items():
        items = [it for it in conf["items"] if it in matrix]
        if len(items) < 3:
            print(f"\n{name}：题目不足3题，跳过因子分析。")
            continue
        series = recoded_item_series(matrix, conf)
        k = len(series)
        rows = [i for i in range(len(series[0])) if all(c[i] is not None for c in series)]
        n = len(rows)
        Z = []
        for col in series:
            vals = [col[i] for i in rows]
            mm = sum(vals) / n
            sd = math.sqrt(sum((v - mm) ** 2 for v in vals) / (n - 1)) if n > 1 else 0
            Z.append([(v - mm) / sd if sd > 0 else 0.0 for v in vals])
        R = [[0.0] * k for _ in range(k)]
        for a in range(k):
            for b in range(a, k):
                r = sum(Z[a][i] * Z[b][i] for i in range(n)) / (n - 1) if n > 1 else 0
                R[a][b] = r
                R[b][a] = r

        do_efa = bool(efa_names) and (efa_names == "__ALL__" or name in efa_names)
        if do_efa:
            res = _efa_one(name, items, conf, Z, R, n, pa_rep=pa_rep)
            if res is not None:
                efa_summaries.append({kk: vv for kk, vv in res.items()
                                      if kk not in ("rows", "PA")})
                efa_item_rows.extend(res["rows"])
                if efa_output:
                    if efa_output.endswith("_因子分析.csv"):
                        stem = efa_output[:-len("_因子分析.csv")]
                    else:
                        stem = os.path.splitext(efa_output)[0]
                    png = stem + "_" + _safe_filename(name) + "_碎石图.png"
                    pa = res.get("PA")
                    hl = pa["nfac_p95"] if pa else res["因子数"]
                    ok = _plot_scree(name, res["特征值"], hl, png,
                                     pa_mean=pa["mean"] if pa else None,
                                     pa_p95=pa["p95"] if pa else None)
                    if ok:
                        scree_pngs.append(png)
                    else:
                        scree_fail = True
            continue

        kmo = kmo_value(R)
        det = determinant(R)
        df = k * (k - 1) / 2
        if det > 1e-300:
            chi2 = -(n - 1 - (2 * k + 5) / 6.0) * math.log(det)
            pval = chi2_pvalue(chi2, df)
        else:
            chi2, pval = float("inf"), 0.0
        eigval, eigvec = _first_pc(R)
        if sum(eigvec) < 0:
            eigvec = [-v for v in eigvec]
        loadings = [eigvec[i] * math.sqrt(max(eigval, 0)) for i in range(k)]
        var_pct = eigval / k * 100

        kmo_txt = f"{kmo:.3f}" if kmo is not None else "无法计算"
        if kmo is not None:
            rate = "极佳" if kmo >= .9 else "适合" if kmo >= .8 else "可接受" if kmo >= .7 \
                else "勉强" if kmo >= .6 else "不适合因子分析"
        else:
            rate = ""
        bart = "p<.001" if pval < .001 else f"p={pval:.3f}"
        print(f"\n{name}（{k}题，N={n}）")
        print(f"  KMO = {kmo_txt}  [{rate}]")
        print(f"  Bartlett球形检验：χ²={chi2:.1f}（df={int(df)}），{bart}（需p<.05）")
        print(f"  第一主成分特征值={eigval:.3f}，方差解释率={var_pct:.2f}%"
              f"（单维量表建议>50%~60%）")
        low = []
        for idx, it in enumerate(items):
            tag = "(反向)" if conf["reverse"].get(it) else ""
            flag = "  ←载荷<.5，检查" if loadings[idx] < .5 else ""
            if loadings[idx] < .5:
                low.append(it)
            print(f"    {it}{tag}：因子载荷={loadings[idx]:.3f}{flag}")
        rows.append({"量表": name, "KMO": round(kmo, 3) if kmo else "",
                     "Bartlett_chi2": round(chi2, 1) if chi2 != float("inf") else "很大",
                     "Bartlett_p": "<.001" if pval < .001 else round(pval, 3),
                     "第一因子解释率%": round(var_pct, 2),
                     "低载荷题": ",".join(low)})
    if efa_item_rows:
        if efa_output:
            nfac_max = max(len([k for k in r if k.startswith("因子") and k.endswith("载荷")])
                           for r in efa_item_rows)
            fields = ["量表", "题项"] + [f"因子{j+1}载荷" for j in range(nfac_max)] + \
                     ["共同度", "归属因子", "提示"]
            with open(efa_output, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(efa_item_rows)
            print(f"\nEFA旋转载荷矩阵已导出：{efa_output}")
        for png in scree_pngs:
            print(f"碎石图已导出：{png}（300dpi，可直接插入论文；结合λ=1线与拐点定因子数）")
        if scree_fail and not scree_pngs:
            print("\n未安装 matplotlib，未生成碎石图（不影响上面的数值结果）。")
            print("  安装后重跑即可出图：pip install matplotlib；或在 JASP Factor 中查看碎石图。")
        print("EFA摘要：" + "；".join(
            f"{s['量表']}→{s['因子数']}因子/累计{s['累计方差%']}%/KMO={s['KMO']}"
            for s in efa_summaries))
        print("提示：因子归属应与理论维度一致；交叉载荷、低载荷题目需结合理论删改后重跑。")
    print("\n提示：引用成熟量表通常报告KMO、Bartlett显著、各题载荷>.5即可；")
    print("  自编/重大修订量表用 --efa 做完整探索性因子分析；CFA验证性因子分析请用JASP/lavaan。")
    return rows


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
    print("四、共同方法偏差检验（Harman单因子）")
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
    print("相关分析（Pearson）")
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


def _vif(cases_x):
    """方差膨胀因子：对每个预测变量，用其余预测变量回归它，VIF=1/(1-R²)。
    返回与列等长的 VIF 列表；单预测变量返回 [1.0]，奇异返回 None。"""
    k = len(cases_x[0])
    if k <= 1:
        return [1.0]
    out = []
    for j in range(k):
        others = [c for c in range(k) if c != j]
        D = [[1.0] + [r[c] for c in others] for r in cases_x]
        yv = [r[j] for r in cases_x]
        b = solve_least_squares(D, yv)
        if b is None:
            out.append(None)
            continue
        yh = [sum(b[a] * D[i][a] for a in range(len(b))) for i in range(len(yv))]
        ym = mean(yv)
        ss_res = sum((yv[i] - yh[i]) ** 2 for i in range(len(yv)))
        ss_tot = sum((v - ym) ** 2 for v in yv)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        out.append(float("inf") if r2 >= 1 else 1.0 / (1 - r2))
    return out


def linear_regression(matrix, x_cols, y_col):
    """多元线性回归（最小二乘），输出β、SE、t、p、R²与共线性诊断(VIF)"""
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

    vif_map = {}
    if k >= 2:
        vifs = _vif([r[:k] for r in cases])
        print("\n共线性诊断（VIF/容差）：")
        print(f"{'预测变量':<14}{'容差':>8}{'VIF':>8}  判读")
        print("-" * 50)
        for j in range(k):
            v = vifs[j]
            if v is None:
                print(f"{x_cols[j]:<14}{'—':>8}{'—':>8}  无法计算（变量冗余）")
                continue
            tol = 1.0 / v if v and v != float("inf") else 0.0
            if v >= 10:
                tag = "✗ 严重多重共线性（VIF≥10），建议删除/合并或岭回归"
            elif v >= 5:
                tag = "⚠ 存在共线性（5≤VIF<10），需关注"
            else:
                tag = "正常（VIF<5）"
            vstr = "∞" if v == float("inf") else f"{v:.2f}"
            print(f"{x_cols[j]:<14}{tol:>8.3f}{vstr:>8}  {tag}")
            vif_map[x_cols[j]] = None if v == float("inf") else round(v, 2)
    return {"R2": round(r2, 3), "调整R2": round(adj_r2, 3),
            "F": round(f, 3), "p": fmt_p(f_p), "系数": result_rows, "VIF": vif_map}


def moderation_analysis(matrix, x_col, w_col, y_col, reps=5000,
                        seed=20260917, output=None):
    """调节效应（PROCESS模型1）：Y=b0+b1 Xc+b2 Wc+b3 Xc*Wc。

    X、W 中心化后构造交互项；交互项 b3 显著即存在调节；
    简单斜率按 W=均值±1SD（Aiken & West, 1991），解析 SE 为
    Var(b1+b3 w)=Cov11+w^2 Cov33+2w Cov13，并用 Bootstrap 百分位 CI 复核。
    """
    cols = [x_col, w_col, y_col]
    missing = [c for c in cols if c not in matrix]
    if missing:
        print(f"✗ 调节分析失败，以下列不存在：{missing}")
        return None
    rows = [i for i in range(len(matrix[y_col]))
            if all(matrix[c][i] is not None for c in cols)]
    n = len(rows)
    if n < 30:
        print(f"⚠ 有效样本仅{n}（<30），调节/Bootstrap结果不稳定，建议加大样本。")
    X0 = [matrix[x_col][i] for i in rows]
    W0 = [matrix[w_col][i] for i in rows]
    Y = [matrix[y_col][i] for i in rows]

    def fit(xv, wv, yv):
        mx, mw = mean(xv), mean(wv)
        xc = [v - mx for v in xv]
        wc = [v - mw for v in wv]
        xw = [xc[i] * wc[i] for i in range(len(xv))]
        D = [[1.0, xc[i], wc[i], xw[i]] for i in range(len(xv))]
        b = solve_least_squares(D, yv)
        return b, xc, wc, xw

    beta, Xc, Wc, XW = fit(X0, W0, Y)
    if beta is None:
        print("✗ 调节回归求解失败（矩阵奇异，可能存在多重共线性）")
        return None
    b0, b1, b2, b3 = beta
    k, df = 3, n - 4
    yhat = [b0 + b1 * Xc[i] + b2 * Wc[i] + b3 * XW[i] for i in range(n)]
    ss_res = sum((Y[i] - yhat[i]) ** 2 for i in range(n))
    ybar = mean(Y)
    ss_tot = sum((v - ybar) ** 2 for v in Y)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1)
    mse = ss_res / df
    XtX = [[sum(([1.0, Xc[i], Wc[i], XW[i]][a]) * ([1.0, Xc[i], Wc[i], XW[i]][b])
                for i in range(n)) for b in range(4)] for a in range(4)]
    inv = invert_matrix(XtX)
    if inv is None:
        print("✗ 无法计算调节回归标准误")
        return None
    cov = [[inv[a][b] * mse for b in range(4)] for a in range(4)]
    f_stat = ((ss_tot - ss_res) / k) / mse if mse > 0 else 0
    f_p = f_p_value(f_stat, k, df)
    sdy, sdx, sdw, sdxw = stdev(Y), stdev(X0), stdev(W0), stdev(XW)

    print("\n" + "=" * 60)
    print("八、调节效应分析（PROCESS 模型1，变量已中心化）")
    print("=" * 60)
    print(f"自变量X={x_col}  调节变量W={w_col}  因变量Y={y_col}")
    print(f"N={n}，R²={r2:.3f}，调整R²={adj_r2:.3f}，模型F({k},{df})={f_stat:.3f}，p={fmt_p(f_p)}{sig_mark(f_p)}")
    print(f"回归方程：Y = {b0:.3f} + {b1:.3f}·Xc + {b2:.3f}·Wc + {b3:.3f}·Xc×Wc")
    print(f"{'项':<12}{'B':>9}{'SE':>8}{'标准化β':>9}{'t':>8}{'p':>9}")
    print("-" * 55)
    labels = ["截距", "X", "W", "X×W(交互)"]
    raw_cols = [None, X0, W0, XW]
    b3_se = math.sqrt(max(cov[3][3], 0))
    for j in range(4):
        se = math.sqrt(max(cov[j][j], 0))
        tv = beta[j] / se if se > 0 else 0
        pj = t_p_two_sided(tv, df) if j > 0 else None
        if j == 0:
            bstd = ""
        else:
            sdj = sdy if j == 0 else (sdx if j == 1 else (sdw if j == 2 else sdxw))
            bstd = f"{beta[j] * sdj / sdy:.3f}" if sdy > 0 else ""
        print(f"{labels[j]:<12}{beta[j]:>9.3f}{se:>8.3f}{bstd:>9}{tv:>8.3f}"
              f"{(fmt_p(pj) if pj is not None else ''):>9}{sig_mark(pj) if pj is not None else ''}")
    b3_t = b3 / b3_se if b3_se > 0 else 0
    b3_p = t_p_two_sided(b3_t, df)
    print(f"\n交互项 X×W：B={b3:.3f}, SE={b3_se:.3f}, t={b3_t:.3f}, p={fmt_p(b3_p)}{sig_mark(b3_p)}")

    # Bootstrap：交互项与三个简单斜率（重采样内重新中心化，条件值固定为原始±1SD）
    rng = random.Random(seed)
    boots = {"b3": [], "low": [], "mid": [], "high": []}
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        xs = [X0[i] for i in idx]
        ws = [W0[i] for i in idx]
        ys = [Y[i] for i in idx]
        try:
            bs, _, _, _ = fit(xs, ws, ys)
        except Exception:
            continue
        if bs is None:
            continue
        boots["b3"].append(bs[3])
        boots["low"].append(bs[1] + bs[3] * (-sdw))
        boots["mid"].append(bs[1])
        boots["high"].append(bs[1] + bs[3] * sdw)

    def ci(key):
        s = sorted(boots[key])
        nr = len(s)
        return s[min(nr - 1, int(0.025 * nr))], s[min(nr - 1, int(0.975 * nr) - 1)]

    conds = [("low", f"{w_col}低（-1SD）", -sdw),
             ("mid", f"{w_col}均值", 0.0),
             ("high", f"{w_col}高（+1SD）", sdw)]
    print("\n简单斜率（X→Y 在不同 W 水平）：")
    print(f"{'W水平':<16}{'斜率':>8}{'解析SE':>8}{'t':>8}{'p':>9}{'Boot95%CI':>20}")
    print("-" * 72)
    out_rows = []
    for key, lab, w in conds:
        theta = b1 + b3 * w
        var_th = cov[1][1] + w * w * cov[3][3] + 2 * w * cov[1][3]
        se_th = math.sqrt(max(var_th, 0))
        t_th = theta / se_th if se_th > 0 else 0
        p_th = t_p_two_sided(t_th, df)
        lo, hi = ci(key)
        mark = "显著" if (lo > 0 or hi < 0) else "不显著"
        print(f"{lab:<16}{theta:>8.3f}{se_th:>8.3f}{t_th:>8.3f}{fmt_p(p_th):>9}"
              f"   [{lo:.3f},{hi:.3f}]{mark}")
        out_rows.append({"项目": "简单斜率·" + lab, "估计值": round(theta, 3),
                         "SE": round(se_th, 3), "t": round(t_th, 3), "p": fmt_p(p_th),
                         "CI下限": round(lo, 3), "CI上限": round(hi, 3), "说明": mark})

    lo3, hi3 = ci("b3")
    ci_sig = (lo3 > 0 or hi3 < 0)
    t_sig = b3_p < 0.05
    if ci_sig:
        direction = "增强（W越高，X对Y的影响越强）" if b3 > 0 else "缓冲（W越高，X对Y的影响越弱）"
        print(f"\n★ 调节效应成立：交互项显著（t={b3_t:.3f}, p={fmt_p(b3_p)}，Bootstrap 95%CI=[{lo3:.3f},{hi3:.3f}]不含0），调节变量起{direction}作用。")
        mod_sig = True
    elif t_sig:
        print(f"\n⚠ 交互项处于边缘：解析检验 p={fmt_p(b3_p)}（<.05）但 Bootstrap 95%CI=[{lo3:.3f},{hi3:.3f}]含0，"
              f"两者结论不一致。应以 SPSS PROCESS 模型1（5000次以上Bootstrap）复核为准，暂不主张稳健的调节效应。")
        mod_sig = False
    else:
        print(f"\n交互项不显著（t={b3_t:.3f}, p={fmt_p(b3_p)}，Bootstrap 95%CI=[{lo3:.3f},{hi3:.3f}]含0），未发现调节效应；简单斜率仅作参考。")
        mod_sig = False
    print("注：变量已中心化；正式结果请用 SPSS PROCESS 模型1 / JASP 复核，并据需要出简单斜率图。")

    if output:
        import csv as _csv
        coef_rows = []
        for j in range(4):
            se = math.sqrt(max(cov[j][j], 0))
            tv = beta[j] / se if se > 0 else 0
            pj = t_p_two_sided(tv, df) if j > 0 else None
            coef_rows.append({"项目": "系数·" + labels[j], "估计值": round(beta[j], 3),
                              "SE": round(se, 3), "t": round(tv, 3),
                              "p": fmt_p(pj) if pj is not None else "",
                              "CI下限": "", "CI上限": "", "说明": ""})
        fields = ["项目", "估计值", "SE", "t", "p", "CI下限", "CI上限", "说明"]
        with open(output, "w", encoding="utf-8-sig", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for r_ in coef_rows + out_rows:
                w.writerow(r_)
        print(f"调节分析表已导出：{output}")
    return {"R2": round(r2, 3), "交互B": round(b3, 3), "交互p": fmt_p(b3_p),
            "调节成立": bool(mod_sig), "简单斜率": out_rows}


def f_p_value(f, df1, df2):
    """F检验p值"""
    if f <= 0:
        return 1.0
    x = df2 / (df2 + df1 * f)
    return betai(df2 / 2.0, df1 / 2.0, x)


def determinant(m):
    """方阵行列式（高斯消元，部分选主元）。"""
    n = len(m)
    a = [row[:] for row in m]
    det = 1.0
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(a[r][i]))
        if abs(a[piv][i]) < 1e-12:
            return 0.0
        if piv != i:
            a[i], a[piv] = a[piv], a[i]
            det = -det
        det *= a[i][i]
        for r in range(i + 1, n):
            factor = a[r][i] / a[i][i]
            for c in range(i, n):
                a[r][c] -= factor * a[i][c]
    return det


def chi2_pvalue(chi2, df):
    """卡方检验p值，Wilson-Hilferty正态近似（df较大时足够准确）。"""
    if df <= 0 or chi2 <= 0:
        return 1.0
    t = (chi2 / df) ** (1.0 / 3.0)
    z = (t - (1 - 2.0 / (9 * df))) / math.sqrt(2.0 / (9 * df))
    return 1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))


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
    print(f"七、Bootstrap中介分析（PROCESS {model}）")
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


def export_three_line_table(desc, corr, output, matrix=None, score_cols=None, alpha_map=None):
    """导出三线表：表1描述统计与正态性；表2描述+相关矩阵+信度(对角α)；表3相关明细(含p)。"""
    with open(output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["表1 描述统计与正态性"])
        w.writerow(["变量", "N", "均值", "标准差", "最小值", "最大值", "偏度", "峰度", "正态性判读"])
        for d in desc:
            w.writerow([d["变量"], d["N"], d["均值"], d["标准差"],
                        d.get("最小值", ""), d.get("最大值", ""),
                        d.get("偏度", ""), d.get("峰度", ""), d.get("正态性", "")])
        w.writerow([])

        if matrix is not None and score_cols:
            cols = [c for c in score_cols if c in matrix]
            if cols:
                dmap = {d["变量"]: d for d in desc}
                w.writerow(["表2 描述统计、相关矩阵与信度（对角括号内为Cronbach's α，下三角为Pearson r，*p<.05 **p<.01 ***p<.001）"])
                w.writerow(["变量", "均值M", "标准差SD"] + [str(i + 1) for i in range(len(cols))])
                for i, ci in enumerate(cols):
                    row = [ci, dmap.get(ci, {}).get("均值", ""), dmap.get(ci, {}).get("标准差", "")]
                    for j, cj in enumerate(cols):
                        if j > i:
                            row.append("")
                        elif j == i:
                            a = alpha_map.get(ci) if alpha_map else None
                            row.append(f"({a:.3f})" if a is not None else "1")
                        else:
                            r, nn = pearson_r(matrix[ci], matrix[cj])
                            if r is not None and nn and nn > 2:
                                t = r * math.sqrt((nn - 2) / max(1 - r * r, 1e-12))
                                star = sig_mark(t_p_two_sided(t, nn - 2))
                            else:
                                star = ""
                            row.append(f"{r:.3f}{star}" if r is not None else "")
                    w.writerow(row)
                w.writerow([])
                w.writerow(["变量编号"] + [f"{i + 1}={c}" for i, c in enumerate(cols)])
                w.writerow([])

        w.writerow(["表3 相关分析明细（r, 双尾p, 成对N）"])
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
    text = None
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            text = p.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if text is None:
        print(f"⚠ 量表配置文件编码无法识别：{path}，请另存为UTF-8")
        return scales
    for raw in text.splitlines():
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
    parser.add_argument("--moderator", help="调节变量W（配合--x X --y Y做PROCESS模型1：中心化交互项+±1SD简单斜率）")
    parser.add_argument("--boot", type=int, default=5000, help="Bootstrap次数（默认5000）")
    parser.add_argument("--seed", type=int, default=20260917, help="Bootstrap随机种子（默认固定，可复现）")
    parser.add_argument("--profile", action="store_true", help="只输出数据画像")
    parser.add_argument("--efa", nargs="*", default=None,
                        help="完整探索性因子分析：不跟量表名=对全部量表；也可跟量表名（空格或逗号分隔）")
    parser.add_argument("--pa-rep", type=int, default=500,
                        help="平行分析随机模拟次数（默认500，越大越稳但越慢；0=关闭平行分析）")
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

    # 人口学/分类变量频数（独立于量表，两个分支都做）
    freq_out = str(path.with_name(path.stem + "_频数表.csv"))
    frequency_analysis(headers, data, matrix, scales, output=freq_out)

    # 完整EFA：--efa（全部）或 --efa 量表A 量表B / --efa 量表A,量表B
    efa_names = None
    if args.efa is not None:
        if len(args.efa) == 0:
            efa_names = "__ALL__"
        else:
            efa_names = set()
            for tok in args.efa:
                for sub in tok.split(","):
                    if sub.strip():
                        efa_names.add(sub.strip())
    efa_out = str(path.with_name(path.stem + "_因子分析.csv")) if efa_names else None
    item_out = str(path.with_name(path.stem + "_题项分析.csv"))

    # 有量表配置：反向计分→信度→量表总分→在总分层面做描述/相关/回归
    if scales:
        rel = reliability_analysis(matrix, scales, item_output=item_out)
        validity_analysis(matrix, scales, efa_names=efa_names,
                          efa_output=efa_out, pa_rep=args.pa_rep)
        harman_test(matrix, scales)
        score_matrix, _ = build_scale_scores(matrix, scales)
        scale_total_cols = [f"{name}总分" for name in scales]
        dataset = export_scale_dataset(path, headers, data, score_matrix, scales)
        print(f"\n含量表总分的分析数据集已导出：{dataset}")
        print("  （JASP/SPSS做中介、PROCESS时直接打开这个文件，用各量表“总分”列）")

        print("\n" + "=" * 60)
        print("五、描述统计与相关分析（量表总分层面）")
        print("=" * 60)
        desc = descriptive(score_matrix, scale_total_cols)
        corr = correlation_matrix(score_matrix, scale_total_cols)

        if args.y and args.x:
            y_col = resolve_col(args.y, scales, score_matrix)
            x_cols = [resolve_col(c, scales, score_matrix) for c in args.x.split(",")]
            print("\n" + "=" * 60)
            print("六、回归分析（量表总分层面）")
            print("=" * 60)
            linear_regression(score_matrix, x_cols, y_col)
        active_matrix = score_matrix
        active_cols = scale_total_cols
        diff_out = str(path.with_name(path.stem + "_差异分析.csv"))
        group_difference_analysis(headers, data, matrix, scales, score_matrix,
                                  scale_total_cols, output=diff_out)
    else:
        # 无量表配置：题目级全量分析（降级模式，建议提供 --scales）
        print("\n提示：提供 --scales 量表配置后，将自动反向计分、算信度效度和量表总分。")
        print("\n" + "=" * 60)
        print("二、描述统计与相关分析（题目级）")
        print("=" * 60)
        desc = descriptive(matrix, num_cols)
        corr = correlation_matrix(matrix, num_cols)
        if args.y and args.x:
            x_cols = [c.strip() for c in args.x.split(",")]
            print("\n" + "=" * 60)
            print("三、回归分析")
            print("=" * 60)
            linear_regression(matrix, x_cols, args.y)
        active_matrix = matrix
        active_cols = num_cols

    alpha_map = None
    if scales:
        alpha_map = {f"{r['量表']}总分": r.get("Cronbach_alpha")
                     for r in rel if r.get("Cronbach_alpha") is not None}
    output = args.output or str(path.with_name(path.stem + "_统计结果.csv"))
    export_three_line_table(desc, corr, output, matrix=active_matrix,
                            score_cols=active_cols, alpha_map=alpha_map)

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

    # 调节分析（PROCESS模型1：X、W中心化+交互项+±1SD简单斜率）
    if args.moderator and args.y and args.x:
        x_first = resolve_col(args.x.split(",")[0], scales, active_matrix)
        w_col = resolve_col(args.moderator, scales, active_matrix)
        y_col = resolve_col(args.y, scales, active_matrix)
        mod_out = str(path.with_name(path.stem + "_调节效应.csv"))
        moderation_analysis(active_matrix, x_first, w_col, y_col,
                            reps=args.boot, seed=args.seed, output=mod_out)

    print("\n" + "=" * 60)
    print("分析完成。提示：")
    print("- 已用 --mediators 自动做Bootstrap中介；正式结果建议JASP/SPSS PROCESS复核")
    print("- 反向题已按scales.txt的(R)标记处理；请核对反向题是否标对")
    print("- 结果需人工核对，p值为近似计算，精确值以SPSS/JASP为准")


if __name__ == "__main__":
    main()
