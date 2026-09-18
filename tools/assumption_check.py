#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数检验前提假设检验工具（正态性 / 方差齐性）
============================================
t 检验、方差分析、线性回归等参数检验在论文方法章通常要交代两个前提：
  1) 因变量（或各组内因变量、回归残差）近似正态；
  2) 组间比较时各组方差齐性。

本工具一次算齐并给可粘进论文的结论：
  - Shapiro-Wilk W 检验（Royston 1992/1995 AS R94 算法，3≤n≤5000，
    纯标准库实现，与 R shapiro.test / scipy.stats.shapiro 同口径）；
  - 调整偏度 G1、超额峰度 G2 及其标准误 z（SPSS 口径，|z|>1.96 标记；
    同时给大样本常用的 Kline 判据 |G1|<3、|G2|<10）；
  - 分组时：逐组 Shapiro-Wilk＋Brown-Forsythe 方差齐性检验
    （Levene 以中位数为中心，比传统 Levene 更稳健，与 SPSS“基于中位数”一致）。

数据口径：
  - 给 --scales：对每个量表按反向计分后的题项求【量表均分】（仅题项全答的
    记录纳入，n 会如实报告）；这正是 t/ANOVA/回归实际使用的因变量。
  - 不给 --scales：自动识别数值列（适合直接吃 auto_stats 导出的
    “_量表总分.csv”或回归残差文件）。
  - --group 列名：按人口学/分组列拆分（如 性别、组别），做组内正态与方差齐性。

解释红线（工具只给证据，不替你“做出正态”）：
  - Shapiro-Wilk 在大样本（n 数百以上）时对微小偏离极敏感，p<.05 很常见；
    此时以偏度峰度、Q-Q 图、直方图综合判断，参数检验对轻度偏离稳健（CLT）。
  - Likert 单个题项是有序分类，不要求正态；正态性看量表总分/均分。
  - 不得为了“通过”正态检验而删数据、删离群值或反复变换挑 p；变换需有
    方法学理由（如对数变换适用于右偏计数数据）并在方法章写明。
  - 方差不齐时优先 Welch t / Welch ANOVA 或非参数检验，而非删组。

用法（项目根目录）：
  python tools/assumption_check.py 清洗后数据.csv --scales scales.txt
  python tools/assumption_check.py 数据.csv --scales scales.txt --group 性别
  python tools/assumption_check.py 量表总分.csv
"""
import argparse
import csv
import io
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats.dataio import (  # noqa: E402
    numeric_columns, parse_scales, read_data, recoded_item_series, to_float_matrix,
)
from stats.compare import _levene  # noqa: E402
from stats.mathx import (  # noqa: E402
    fmt_p, mean, normal_quantile, normal_sf, skew_kurt, stdev,
)

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与其他工具同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ================================================================ Shapiro-Wilk
# Royston AS R94 多项式系数（与 R src/library/stats/src/swilk.c、
# scipy 编译的 swilk.f、EnvStats::swGofTestStatistic 同源）
_C1 = [0.0, 0.221157, -0.147981, -2.071190, 4.434685, -2.706056]
_C2 = [0.0, 0.042981, -0.293762, -1.752461, 5.682633, -3.582633]
_C3 = [0.5440, -0.39978, 0.025054, -6.714e-4]      # n 4..11：均值
_C4 = [1.3822, -0.77857, 0.062767, -0.0020322]     # n 4..11：对数标准差
_C5 = [-1.5861, -0.31082, -0.083751, 0.0038915]    # n≥12：均值（关于 ln n）
_C6 = [-0.4803, -0.082676, 0.0030302]              # n≥12：对数标准差
_G = [-2.273, 0.459]                               # n 4..11：gamma 截距
_P_MIN = 1e-19


def _poly(c, x):
    """常数项在前的系数表的 Horner 求值。"""
    r = c[-1]
    for v in reversed(c[:-1]):
        r = r * x + v
    return r


def _norm_upper(z):
    """标准正态上尾概率。z≤1.28 用 erfc（双精度）；z>1.28 用 AS66 的
    Mills 比连分式（与 swilk.f 的 alnorm 同系数），可算到约 1e-150，
    避免极小 p 被过早截到 1e-19。"""
    if z <= 1.28:
        return normal_sf(z)
    r = 0.398942280385
    c1, c2, c3, c4, c5, c6 = (-3.8052e-8, 3.98064794e-4, -0.151679116635,
                              4.8385912808, 0.742380924027, 3.99019417011)
    d1, d2, d3, d4, d5 = (1.00000615302, 1.98615381364, 5.29330324926,
                          -15.1508972451, 30.789933034)
    if z > 18.66:
        return 0.0
    return r * math.exp(-0.5 * z * z) / (
        z + c1 + d1 / (z + c2 + d2 / (z + c3 + d3 / (
            z + c4 + d4 / (z + c5 + d5 / (z + c6))))))


def shapiro_wilk(values):
    """Shapiro-Wilk 正态性检验，返回 (W, p)；n<3 或常量返回 (None, None)。

    权重用 Royston 对期望正态序次统计量的多项式近似（EnvStats 写法）；
    p 值用 Royston (1992) 正态化变换（AS R94），n=3 用精确分布。
    """
    x = sorted(float(v) for v in values)
    n = len(x)
    if n < 3:
        return None, None
    xbar = sum(x) / n
    s2 = sum((v - xbar) ** 2 for v in x) / (n - 1)
    if s2 <= 0:
        return None, None
    # 期望正态序次统计量 m_i = Φ⁻¹((i−3/8)/(n+1/4))
    m = [normal_quantile((i - 0.375) / (n + 0.25)) for i in range(1, n + 1)]
    ssm = sum(v * v for v in m)
    cvec = [v / math.sqrt(ssm) for v in m]
    a = [0.0] * n
    if n == 3:
        # AS R94 特例：权重恰为 ±1/√2（Fortran swilk 的 n==3 分支）
        a = [math.sqrt(0.5), 0.0, -math.sqrt(0.5)]
    else:
        y = 1.0 / math.sqrt(n)
        a[n - 1] = cvec[n - 1] + _poly(_C1, y)
        a[0] = -a[n - 1]
    if n == 3:
        pass
    elif n <= 5:
        phi = (ssm - 2.0 * m[n - 1] ** 2) / (1.0 - 2.0 * a[n - 1] ** 2)
        for i in range(1, n - 1):
            a[i] = m[i] / math.sqrt(phi)
    else:
        a[n - 2] = cvec[n - 2] + _poly(_C2, y)
        phi = (ssm - 2.0 * m[n - 1] ** 2 - 2.0 * m[n - 2] ** 2) / \
              (1.0 - 2.0 * a[n - 1] ** 2 - 2.0 * a[n - 2] ** 2)
        for i in range(2, n - 2):
            a[i] = m[i] / math.sqrt(phi)
        a[1] = -a[n - 2]
    num = sum(a[i] * x[i] for i in range(n))
    w = num * num / ((n - 1) * s2)
    if w > 1.0:
        w = 1.0
    w1 = 1.0 - w
    if w1 <= 0:
        return w, 1.0
    if n == 3:
        # 精确 p：6/π·(arcsin(√W) − π/3)
        p = (6.0 / math.pi) * (math.asin(math.sqrt(w)) - math.pi / 3.0)
        return w, min(1.0, max(_P_MIN, p))
    ylog = math.log(w1)
    if n <= 11:
        gamma = _poly(_G, float(n))
        if ylog >= gamma:
            p = _P_MIN
        else:
            zeta = -math.log(gamma - ylog)
            mu = _poly(_C3, float(n))
            sd = math.exp(_poly(_C4, float(n)))
            p = _norm_upper((zeta - mu) / sd)
    else:
        xx = math.log(float(n))
        mu = _poly(_C5, xx)
        sd = math.exp(_poly(_C6, xx))
        p = _norm_upper((ylog - mu) / sd)
    # n≤11 分支按 AS R94 在 gamma 处截到 1e-19；n≥12 允许报告更小的 p（远尾展开）
    p = min(1.0, p)
    if n <= 11:
        p = max(_P_MIN, p)
    return w, p


# ================================================================ 数据组织
def build_dvs(headers, matrix, scales_path, only):
    """返回 [(dv名, [按行对齐的值或None]), ...]。"""
    if not scales_path:
        names = numeric_columns(matrix, headers)
        return [(nm, matrix[nm]) for nm in names]
    scales = parse_scales(scales_path)
    if not scales:
        print(f"✗ scales 配置为空或读不到：{scales_path}")
        sys.exit(1)
    if only:
        if only not in scales:
            print(f"✗ scales 里找不到量表「{only}」，可用：{ '、'.join(scales) }")
            sys.exit(1)
        scales = {only: scales[only]}
    dvs = []
    nrow = len(matrix[headers[0]]) if headers else 0
    for name, conf in scales.items():
        missing_items = [it for it in conf["items"] if it not in matrix]
        if missing_items:
            print(f"✗ 量表「{name}」有题项在数据中找不到：{ '、'.join(missing_items) }")
            sys.exit(1)
        series = recoded_item_series(matrix, conf)
        scores = []
        for r in range(nrow):
            row = [col[r] for col in series]
            if any(v is None for v in row):
                scores.append(None)
            else:
                scores.append(sum(row) / len(row))
        dvs.append((name, scores))
    return dvs


def normality_row(name, group_label, vals, alpha):
    """一个变量（或一组）一行正态性诊断。"""
    x = [float(v) for v in vals if v is not None]
    n = len(x)
    row = {"变量": name, "组别": group_label, "n": n, "均值": None, "标准差": None,
           "偏度": None, "偏度z": None, "峰度": None, "峰度z": None,
           "W": None, "p": None, "判读": ""}
    if n == 0:
        row["判读"] = "无数据"
        return row
    row["均值"] = mean(x)
    if n >= 2:
        row["标准差"] = stdev(x)
    g1, g2 = skew_kurt(x)
    notes = []
    if g1 is not None:
        row["偏度"] = g1
        se1 = math.sqrt(6.0 / n)
        row["偏度z"] = g1 / se1
        if abs(row["偏度z"]) > 1.96:
            notes.append("偏度z超±1.96")
    if g2 is not None:
        row["峰度"] = g2
        se2 = math.sqrt(24.0 / n)
        row["峰度z"] = g2 / se2
        if abs(row["峰度z"]) > 1.96:
            notes.append("峰度z超±1.96")
    kline_ok = (g1 is not None and g2 is not None and abs(g1) < 3 and abs(g2) < 10)
    z_strong = ((row["偏度z"] is not None and abs(row["偏度z"]) > 3.29)
                or (row["峰度z"] is not None and abs(row["峰度z"]) > 3.29))
    w, p = shapiro_wilk(x)
    if w is None:
        row["判读"] = "常量/样本不足，无法做 Shapiro-Wilk"
        return row
    row["W"], row["p"] = w, p
    sw_ok = p >= alpha
    if n > 5000:
        notes.append("n>5000，Shapiro p 值口径不稳，以偏度峰度/Q-Q图为准")
    if sw_ok and (kline_ok or n < 4):
        verdict = "不拒绝正态"
    elif sw_ok and not kline_ok:
        verdict = "Shapiro不显著但偏度峰度超Kline判据，结合Q-Q图判断"
    elif (not sw_ok) and not kline_ok:
        verdict = "偏离正态且偏度峰度超Kline判据，采用Welch/非参数/Bootstrap"
    elif (not sw_ok) and kline_ok and z_strong:
        verdict = ("Shapiro与偏度/峰度z均显著，但|偏度|<3、|峰度|<10 仍在"
                   "Kline可接受范围；建议以Bootstrap置信区间或Welch为主分析")
    elif (not sw_ok) and kline_ok and n >= 300:
        verdict = ("Shapiro显著但|偏度|<3、|峰度|<10；n≥300 时检验对微小偏离"
                   "过敏感，可视为近似正态，建议补Bootstrap稳健性校验")
    elif (not sw_ok) and kline_ok and n >= 50:
        verdict = ("Shapiro显著但偏度峰度在Kline可接受范围，属轻度偏离，"
                   "参数检验通常仍稳健，建议补Welch/Bootstrap校验")
    else:
        verdict = ("小样本下Shapiro功效有限且显著，以偏度峰度/Q-Q图为准，"
                   "建议同时报非参数结果")
    row["判读"] = verdict + ("（" + "；".join(notes) + "）" if notes else "")
    return row


def fmt_num(v, nd=3):
    return "" if v is None else f"{v:.{nd}f}"


def print_norm_table(title, rows):
    print(f"\n{title}")
    print("-" * 104)
    print(f"{'变量':<12}{'组别':<8}{'n':>5}{'均值':>8}{'SD':>8}"
          f"{'偏度':>8}{'偏度z':>8}{'峰度':>8}{'峰度z':>8}{'W':>9}{'p':>9}")
    for r in rows:
        print(f"{r['变量'][:12]:<12}{r['组别'][:8]:<8}{r['n']:>5}"
              f"{fmt_num(r['均值']):>8}{fmt_num(r['标准差']):>8}"
              f"{fmt_num(r['偏度']):>8}{fmt_num(r['偏度z'],2):>8}"
              f"{fmt_num(r['峰度']):>8}{fmt_num(r['峰度z'],2):>8}"
              f"{fmt_num(r['W'],4):>9}{fmt_p(r['p']):>9}")
        print(f"  → {r['判读']}")
    print("-" * 104)


# ================================================================ 论文段落
def _rng(vals, fmt):
    """区间措辞：只有一个变量（或格式化后相同）时写"为 X"，不写"介于 X～X"这种废话。"""
    lo, hi = fmt(min(vals)), fmt(max(vals))
    return f"为 {lo}" if lo == hi else f"介于 {lo}～{hi}"


def _rng_p(ps):
    """p 值区间措辞：极小 p 用 <.001 表述，避免写出"介于 <.001～.800"。"""
    lo, hi = min(ps), max(ps)
    if hi < 0.001:
        return "均<.001"
    if lo < 0.001:
        return f"最小<.001、最大{fmt_p(hi)}"
    return _rng(ps, fmt_p)


def make_paragraph(overall, grouped, levene_rows, alpha, group_col):
    lines = []
    dv_names = [r["变量"] for r in overall]
    sw_rows = [r for r in overall if r["p"] is not None]
    if sw_rows:
        ps = [r["p"] for r in sw_rows]
        ws = [r["W"] for r in sw_rows]
        skew_vals = [abs(r["偏度"]) for r in overall if r["偏度"] is not None]
        kurt_vals = [abs(r["峰度"]) for r in overall if r["峰度"] is not None]
        sig = [r for r in sw_rows if r["p"] < alpha]
        seg = (f"对 {('、'.join(dv_names))} 做 Shapiro-Wilk 正态性检验，"
               f"W {_rng(ws, lambda v: f'{v:.3f}')}，p {_rng_p(ps)}；")
        if skew_vals and kurt_vals:
            seg += (f"偏度绝对值{_rng(skew_vals, lambda v: f'{v:.2f}')}，"
                    f"峰度绝对值{_rng(kurt_vals, lambda v: f'{v:.2f}')}。")
        if not sig:
            seg += (f"各变量 p 均≥{alpha:g}，未拒绝正态分布假设，"
                    "结合偏度、峰度与 Q-Q 图，可认为近似正态分布。")
        else:
            def _mild(r):
                return (r["偏度"] is not None and r["峰度"] is not None
                        and abs(r["偏度"]) < 3 and abs(r["峰度"]) < 10)
            mild = [r["变量"] for r in sig if _mild(r)]
            hard = [r["变量"] for r in sig if not _mild(r)]
            seg += f"其中 {('、'.join(r['变量'] for r in sig))} 的 p<{alpha:g}。"
            if mild:
                strong = [r["变量"] for r in sig if _mild(r) and (
                    (r["偏度z"] is not None and abs(r["偏度z"]) > 3.29)
                    or (r["峰度z"] is not None and abs(r["峰度z"]) > 3.29))]
                seg += ("但 " + "、".join(mild) + " 的偏度、峰度均在 Kline 可接受范围"
                        "（|偏度|<3、|峰度|<10），Shapiro-Wilk 在 n 较大或变量为离散"
                        "量表均分时对微小偏离敏感，结合 Q-Q 图可认为近似正态，"
                        "参数检验结果通常稳健，建议同时报告 Welch/Bootstrap 结果作为"
                        "稳健性校验；")
                if strong:
                    seg += ("其中 " + "、".join(strong) + " 的偏度/峰度 z 检验亦达 "
                            "p<.001，建议以 Bootstrap 偏差校正置信区间（如 5000 次）"
                            "作为主分析结果；")
            if hard:
                seg += ("、".join(hard) + " 偏度/峰度超出可接受范围，后续比较采用 "
                        "Welch 校正或非参数检验，并报告 Bootstrap 置信区间；")
        lines.append(seg)
    if grouped:
        lines.append(f"按「{group_col}」分组后，各组内的 Shapiro-Wilk 检验结果见上表。")
    if levene_rows:
        eq = [r for r in levene_rows if r["p"] is not None and r["p"] >= alpha]
        ne = [r for r in levene_rows if r["p"] is not None and r["p"] < alpha]
        if not ne:
            lines.append(
                f"Brown-Forsythe 方差齐性检验（Levene 基于中位数）各变量 p 均≥{alpha:g}"
                "（见上表），可认为各组方差齐性，采用等方差 t 检验/单因素方差分析。")
        else:
            lines.append(
                f"{'、'.join(r['变量'] for r in ne)} 的 Brown-Forsythe 检验 p<{alpha:g}，"
                "方差不齐，组间比较采用 Welch t / Welch ANOVA（或 Mann-Whitney U / "
                "Kruskal-Wallis 非参数检验），不对方差做齐性假设。")
    dropped_note = [(r["变量"], r.get("排除组别") or []) for r in levene_rows
                    if r.get("排除组别")]
    if dropped_note:
        lines.append(
            "注：方差齐性检验未纳入组内人数少于 2 的组别（"
            + "；".join(f"{v}：{'、'.join(g)}" for v, g in dropped_note)
            + "）。这些记录仍在样本内、未被删除，只是无法参与该检验的离差计算；"
              "若为分组列漏填或错填所致，应在清洗阶段核对并修正归类。")
    lines.append("注：Shapiro-Wilk 不显著不等于“证明正态”；Likert 单个题项为有序"
                 "分类不要求正态，正态性针对量表总分/均分；未通过检验时不得删改数据"
                 "“凑正态”。")
    return "\n".join(lines)


# ================================================================ 导出
def write_csv(path, overall, grouped, levene_rows):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["一、总体正态性检验（Shapiro-Wilk / 偏度峰度）"])
        w.writerow(["变量", "n", "均值", "标准差", "偏度", "偏度z", "峰度", "峰度z",
                    "Shapiro-Wilk W", "p", "判读"])
        for r in overall:
            w.writerow([r["变量"], r["n"],
                        "" if r["均值"] is None else round(r["均值"], 4),
                        "" if r["标准差"] is None else round(r["标准差"], 4),
                        "" if r["偏度"] is None else round(r["偏度"], 4),
                        "" if r["偏度z"] is None else round(r["偏度z"], 3),
                        "" if r["峰度"] is None else round(r["峰度"], 4),
                        "" if r["峰度z"] is None else round(r["峰度z"], 3),
                        "" if r["W"] is None else round(r["W"], 5),
                        "" if r["p"] is None else fmt_p(r["p"]), r["判读"]])
        w.writerow([])
        w.writerow(["二、分组组内正态性检验"])
        w.writerow(["变量", "组别", "n", "均值", "标准差", "偏度", "偏度z", "峰度",
                    "峰度z", "Shapiro-Wilk W", "p", "判读"])
        if grouped:
            for r in grouped:
                w.writerow([r["变量"], r["组别"], r["n"],
                            "" if r["均值"] is None else round(r["均值"], 4),
                            "" if r["标准差"] is None else round(r["标准差"], 4),
                            "" if r["偏度"] is None else round(r["偏度"], 4),
                            "" if r["偏度z"] is None else round(r["偏度z"], 3),
                            "" if r["峰度"] is None else round(r["峰度"], 4),
                            "" if r["峰度z"] is None else round(r["峰度z"], 3),
                            "" if r["W"] is None else round(r["W"], 5),
                            "" if r["p"] is None else fmt_p(r["p"]), r["判读"]])
        else:
            w.writerow(["未使用 --group，本段为空"])
        w.writerow([])
        w.writerow(["三、Brown-Forsythe 方差齐性检验（Levene 基于中位数）"])
        w.writerow(["变量", "F", "df1", "df2", "p", "未纳入组别", "判读"])
        if levene_rows:
            for r in levene_rows:
                w.writerow([r["变量"], "" if r["F"] is None else round(r["F"], 4),
                            r["df1"], r["df2"],
                            "" if r["p"] is None else fmt_p(r["p"]),
                            "、".join(r.get("排除组别") or []) or "（全部组别均纳入）",
                            r["判读"]])
        else:
            w.writerow(["未使用 --group，本段为空"])


def write_report(path, in_path, overall, grouped, levene_rows, paragraph, alpha, group_col):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write("参数检验前提假设检验报告（正态性 / 方差齐性）\n")
        f.write("=" * 60 + "\n")
        f.write(f"数据：{os.path.basename(in_path)}；"
                f"{'分组列：' + group_col + '；' if group_col else ''}"
                f"显著性水平 α={alpha:g}\n\n")
        f.write("一、总体正态性\n")
        for r in overall:
            f.write(f"  {r['变量']}：n={r['n']}，"
                    f"M={fmt_num(r['均值'])}，SD={fmt_num(r['标准差'])}，"
                    f"偏度={fmt_num(r['偏度'])}（z={fmt_num(r['偏度z'],2)}），"
                    f"峰度={fmt_num(r['峰度'])}（z={fmt_num(r['峰度z'],2)}），"
                    f"W={fmt_num(r['W'],4)}，p={fmt_p(r['p'])}\n    → {r['判读']}\n")
        if grouped:
            f.write("\n二、分组组内正态性\n")
            for r in grouped:
                f.write(f"  {r['变量']}｜{r['组别']}：n={r['n']}，"
                        f"W={fmt_num(r['W'],4)}，p={fmt_p(r['p'])} → {r['判读']}\n")
        if levene_rows:
            f.write("\n三、方差齐性（Brown-Forsythe）\n")
            for r in levene_rows:
                f.write(f"  {r['变量']}：F({r['df1']},{r['df2']})={fmt_num(r['F'],3)}，"
                        f"p={fmt_p(r['p'])} → {r['判读']}\n")
        f.write("\n可写进方法/结果章的表述（数字来自你的真实数据，请核对后使用）：\n")
        f.write(paragraph + "\n")


# ================================================================ 主流程
def main():
    parser = argparse.ArgumentParser(description="参数检验前提假设检验（正态性/方差齐性）")
    parser.add_argument("input", nargs="?", help="清洗后的问卷数据 CSV（或量表总分 CSV）")
    parser.add_argument("--scales", default="", help="scales.txt（按量表均分检验，推荐）")
    parser.add_argument("--only", default="", help="只分析某一个量表（配合 --scales）")
    parser.add_argument("--group", default="", help="分组列名（如 性别、组别）：组内正态＋方差齐性")
    parser.add_argument("--csv-out", default="", help="CSV 导出目录（默认在数据同目录）")
    parser.add_argument("--report", default="", help="报告 txt 路径（默认在数据同目录）")
    parser.add_argument("--alpha", default="0.05", help="显著性水平，默认 0.05")
    args = parser.parse_args()
    if not args.input:
        parser.print_help()
        sys.exit(1)
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"✗ 找不到数据文件：{in_path}")
        sys.exit(1)
    try:
        alpha = float(args.alpha)
    except ValueError:
        print(f"✗ --alpha 必须是数字，收到：{args.alpha}")
        sys.exit(1)
    if not 0.0 < alpha < 1.0:
        print("✗ --alpha 必须在 0 与 1 之间。")
        sys.exit(1)
    try:
        headers, data = read_data(str(in_path))
    except Exception as exc:
        print(f"✗ 数据读取失败：{exc}")
        sys.exit(1)
    if not headers or not data:
        print("✗ 数据为空（没有表头或数据行）。")
        sys.exit(1)
    matrix = to_float_matrix(headers, data)
    try:
        dvs = build_dvs(headers, matrix, args.scales, args.only)
    except Exception as exc:
        print(f"✗ scales 配置解析失败：{exc}")
        sys.exit(1)
    if not dvs:
        print("✗ 没有可分析的数值列；给 --scales scales.txt 可显式指定量表题项。")
        sys.exit(1)

    group_col = args.group.strip()
    groups = None
    if group_col:
        if group_col not in headers:
            print(f"✗ 找不到分组列「{group_col}」，表头为：{ '、'.join(headers) }")
            sys.exit(1)
        gidx = headers.index(group_col)
        groups = []
        for row in data:
            g = (row[gidx] or "").strip() if gidx < len(row) else ""
            groups.append(g if g else None)
        levels = []
        for g in groups:
            if g is not None and g not in levels:
                levels.append(g)
        if len(levels) < 2:
            print(f"✗ 分组列「{group_col}」只有 {len(levels)} 个非空组别，无法做方差齐性检验。")
            sys.exit(1)

    # 总体正态性
    overall = []
    for name, series in dvs:
        overall.append(normality_row(name, "总体", series, alpha))
    print("=" * 72)
    print("参数检验前提假设检验（Shapiro-Wilk 正态性 / Brown-Forsythe 方差齐性）")
    print("=" * 72)
    print_norm_table("一、总体正态性", overall)
    big_n = [r for r in overall if r["n"] > 5000]
    if big_n:
        print("提示：以下变量 n>5000，Royston p 值口径在该范围不稳，"
              "请以偏度峰度与 Q-Q 图为准：" + "、".join(r["变量"] for r in big_n))

    # 分组：组内正态＋方差齐性
    grouped, levene_rows = [], []
    if groups is not None:
        level_order = []
        for g in groups:
            if g is not None and g not in level_order:
                level_order.append(g)
        for name, series in dvs:
            grp_vals = {lv: [] for lv in level_order}
            for r, g in enumerate(groups):
                if g is not None and r < len(series) and series[r] is not None:
                    grp_vals[g].append(float(series[r]))
            for lv in level_order:
                grouped.append(normality_row(name, lv, grp_vals[lv], alpha))
            # _levene 内部会丢掉组内 n<2 的组，df 必须跟着按实际参与的组算，
            # 否则报告里 F(df1,df2) 与 p 自相矛盾（p 按参与组算、df 按全部组写）。
            used = [lv for lv in level_order if len(grp_vals[lv]) >= 2]
            dropped = [lv for lv in level_order if len(grp_vals[lv]) < 2]
            n_drop_rows = sum(len(grp_vals[lv]) for lv in dropped)
            if dropped:
                print(f"⚠ 「{name}」的方差齐性检验无法纳入组别："
                      + "、".join(f"{lv}(n={len(grp_vals[lv])})" for lv in dropped)
                      + f"，共 {n_drop_rows} 份记录未参与该检验（组内少于 2 人算不出离差）；"
                        "这些记录仍计入组内正态性与总样本，请勿当作已删除。")
            fstat, pp = _levene([grp_vals[lv] for lv in used], center="median")
            ntot = sum(len(grp_vals[lv]) for lv in used)
            k = len(used)
            if fstat is None:
                reason = ("有效组不足 2 个（其余组人数<2），无法做方差齐性检验" if k < 2
                          else "组内无变异/样本不足，无法计算")
                levene_rows.append({"变量": name, "F": None, "df1": max(k - 1, 0),
                                    "df2": max(ntot - k, 0), "p": None,
                                    "排除组别": dropped, "判读": reason})
            else:
                ok = pp >= alpha
                levene_rows.append({"变量": name, "F": fstat, "df1": k - 1,
                                    "df2": ntot - k, "p": pp,
                                    "排除组别": dropped,
                                    "判读": ("方差齐性成立" if ok
                                            else "方差不齐，用 Welch/非参数")})
        print_norm_table("二、分组组内正态性", grouped)
        print("\n三、Brown-Forsythe 方差齐性检验（Levene 基于中位数，推荐口径）")
        print("-" * 72)
        print(f"{'变量':<14}{'F':>10}{'df':>10}{'p':>10}  判读")
        for r in levene_rows:
            dfstr = f"{r['df1']},{r['df2']}"
            print(f"{r['变量'][:14]:<14}{fmt_num(r['F'],3):>10}{dfstr:>10}"
                  f"{fmt_p(r['p']):>10}  {r['判读']}")
        print("-" * 72)

    paragraph = make_paragraph(overall, grouped, levene_rows, alpha, group_col)
    print("\n可写进方法/结果章的表述（数字来自你的真实数据，请核对后使用）：")
    for line in paragraph.split("\n"):
        print("  " + line)
    print("\n红线：Shapiro 大样本过敏感，综合偏度峰度/Q-Q图判断；Likert 题项不要求"
          "正态；不得为通过检验删数据或反复变换挑 p；方差不齐用 Welch/非参数。")

    stem = in_path.with_suffix("")
    out_dir = Path(args.csv_out) if args.csv_out else in_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{stem.name}_前提假设检验.csv"
    report_path = Path(args.report) if args.report else out_dir / f"{stem.name}_前提假设报告.txt"
    write_csv(csv_path, overall, grouped, levene_rows)
    write_report(report_path, in_path, overall, grouped, levene_rows,
                 paragraph, alpha, group_col)
    print(f"\n已导出：{csv_path}")
    print(f"已导出：{report_path}")


if __name__ == "__main__":
    main()
