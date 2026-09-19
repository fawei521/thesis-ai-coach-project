#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缺失值分析与 Little's MCAR 检验工具
==================================
问卷数据在预处理后、清洗前，方法章通常要交代三件事：缺了多少、怎么缺的、
能不能直接删/插补。本工具一次算齐：

  1) 描述：总缺失率、逐题缺失率/观测均值、完整作答（成列删除后）样本量、
     每个缺失模式的人数与缺失变量；
  2) Little (1988) MCAR 检验（T_MLμ 均值项口径，与 R naniar::mcar_test、
     misty::na.test 及 Enders (2010) 一致）：EM 算法估计多元正态下的均值
     向量与协方差阵（ML，除以 N），再按缺失模式汇总马氏距离：
         d² = Σ_j n_j (x̄_j − μ̂_j)' Σ̂_j⁻¹ (x̄_j − μ̂_j)，
         df = Σ_j k_j − k，
     其中 x̄_j、k_j 为第 j 种缺失模式下观测变量的均值与个数，μ̂_j、Σ̂_j 为
     EM 估计在这些观测变量上的子向量/子矩阵；d² 在 MCAR 下渐近服从 χ²(df)。
     （SPSS 缺失值模块用的是含协方差似然项的完整 Little 统计量，数值与自由度
     会不同；均值项口径是 naniar 等免费工具的通行实现，且对小样本/稀疏模式
     更稳健。）
  3) 给可直接写进论文的报告段落与处理建议（成列删除 / 多重插补·FIML）。

纯 Python 标准库实现（矩阵求逆、χ² 分布复用 stats 子包），不联网。
检验基于连续多元正态假设，Likert 数据结果谨慎解读；不显著不等于"证明 MCAR"。

用法（项目根目录）：
  python tools/missing_report.py 预处理后数据.csv
  python tools/missing_report.py 数据.csv --scales scales.txt
  python tools/missing_report.py 数据.csv --scales scales.txt --only 孤独感
"""
import argparse
import csv
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats.dataio import (  # noqa: E402
    assert_items_exist, numeric_columns, parse_scales, read_data, to_float_matrix,
)
from stats.linalg import invert_matrix  # noqa: E402
from stats.mathx import chi2_sf, fmt_p, mean, variance  # noqa: E402

# --- 输出编码守卫：管道/重定向时强制 UTF-8（与其他工具同款，避免 GBK 崩溃）---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ================================================================ 数据准备
def select_columns(headers, matrix, scales_path, only):
    """返回参与分析的列名列表：有 scales 用题项（可 --only 某量表），否则数值列启发式。"""
    if scales_path:
        scales = parse_scales(scales_path)
        if not scales:
            print(f"✗ scales 配置为空或读不到：{scales_path}")
            sys.exit(1)
        if only:
            if only not in scales:
                print(f"✗ scales 里没有量表「{only}」；可用：{', '.join(scales)}")
                sys.exit(1)
            names = [only]
        else:
            names = list(scales)
        cols = [it for name in names for it in scales[name]["items"]]
        # 去重（不同量表理论上不共享题项，保险起见保序去重）
        seen, uniq = set(), []
        for c in cols:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        cols = uniq
        sub = {name: scales[name] for name in names}
        assert_items_exist(sub, matrix)
        return cols, "scales 题项"
    cols = numeric_columns(matrix, headers)
    if not cols:
        print("✗ 数据里识别不到数值列：请先用菜单第1项预处理，或用 --scales 指定题项。")
        sys.exit(1)
    return cols, "数值列自动识别"


def build_matrix(matrix, cols):
    """按选定列组装 float|None 矩阵；整列全缺失直接拒绝（EM 无法估计）。"""
    X = [matrix[c] for c in cols]
    k = len(cols)
    data = [[X[j][i] for j in range(k)] for i in range(len(X[0]))]
    for j, c in enumerate(cols):
        if all(v is None for v in (row[j] for row in data)):
            print(f"✗ 列「{c}」全部缺失，无法估计其均值/方差；请检查数据或剔除该列后重跑。")
            sys.exit(1)
    return data, k


# ================================================================ EM 估计
def em_normal(data, k, max_iter=500, tol=1e-7):
    """缺失多元正态的 EM（Dempster-Laird-Rubin），返回 (μ, Σ, 迭代次数)。

    E 步用观测部分条件期望填补缺失，并在二阶充分统计量上加条件协方差；
    M 步 μ=T1/N、Σ=T2/N−μμ'（ML，除以 N，与 R norm 包/naniar 同口径）。
    """
    n = len(data)
    mu = [0.0] * k
    for j in range(k):
        obs = [row[j] for row in data if row[j] is not None]
        mu[j] = mean(obs)
    sig = [[0.0] * k for _ in range(k)]
    const_cols = []
    for j in range(k):
        obs = [row[j] for row in data if row[j] is not None]
        v0 = variance(obs, ddof=0)
        if v0 == 0:
            const_cols.append(str(j + 1))
        sig[j][j] = v0 or 1.0
    if const_cols:
        print("✗ 第 " + "、".join(const_cols) + " 个分析列观测值完全无变异（常量列），"
              "协方差阵必然奇异，无法做 MCAR 检验；请剔除该列（如题项已无区分度）后重跑。")
        sys.exit(1)

    def sub_matrix(idx):
        return [[sig[a][b] for b in idx] for a in idx]

    # 缺失掩码在整个 EM 过程中不变，按缺失模式分组：同一模式的行共用同一个
    # Σ_oo⁻¹ / B / C_mm，只需各算一次。逐行求逆时 k=30 就要十几秒，
    # 79 题的真实问卷会跑到不可用；分组后求逆次数从 n 降到模式数。
    patterns = {}
    for i, row in enumerate(data):
        patterns.setdefault(tuple(j for j in range(k) if row[j] is not None), []).append(i)
    all_idx = list(range(k))

    for it in range(1, max_iter + 1):
        T1 = [0.0] * k
        T2 = [[0.0] * k for _ in range(k)]
        for o, rows in patterns.items():
            o = list(o)
            oset = set(o)
            m = [j for j in all_idx if j not in oset]
            B = C = None
            if m and o:
                inv_o = invert_matrix(sub_matrix(o))
                if inv_o is None:
                    print("✗ EM 失败：观测变量协方差阵奇异（题项可能完全线性相关，如总分与题项同时入列）。")
                    print("  建议：用 --scales 只选题项列（不要放总分列），或减少变量后重跑。")
                    sys.exit(1)
                # B = Σ_mo Σ_oo⁻¹  (len(m) × len(o))；注意 o[b] 才是全局列号
                B = [[sum(sig[a][o[b]] * inv_o[b][c] for b in range(len(o)))
                      for c in range(len(o))] for a in m]
                # C_mm = Σ_mm − B Σ_om，同一模式下恒定
                C = [[sig[a][b] - sum(B[ai][c] * sig[o[c]][b] for c in range(len(o)))
                      for bi, b in enumerate(m)] for ai, a in enumerate(m)]
            elif m and not o:
                # 整行缺失：填 μ，二阶统计加整个 Σ（该行不提供信息但计入 N）
                C = [row_sig[:] for row_sig in sig]
            n_pat = len(rows)
            if C:
                for ai, a in enumerate(m):
                    Ta, Ca = T2[a], C[ai]
                    for bi in range(len(m)):
                        Ta[m[bi]] += n_pat * Ca[bi]
            for i in rows:
                row = data[i]
                fill = list(mu)
                for j in o:
                    fill[j] = row[j]
                if B is not None:
                    resid = [row[o[c]] - mu[o[c]] for c in range(len(o))]
                    for ai, a in enumerate(m):
                        fill[a] = mu[a] + sum(B[ai][c] * resid[c] for c in range(len(o)))
                for j in range(k):
                    fj = fill[j]
                    T1[j] += fj
                    Tj = T2[j]
                    for jj in range(k):
                        Tj[jj] += fj * fill[jj]
        new_mu = [t / n for t in T1]
        new_sig = [[T2[j][jj] / n - new_mu[j] * new_mu[jj] for jj in range(k)]
                   for j in range(k)]
        # 对称化，消除浮点不对称
        for j in range(k):
            for jj in range(j + 1, k):
                avg = 0.5 * (new_sig[j][jj] + new_sig[jj][j])
                new_sig[j][jj] = new_sig[jj][j] = avg
        change = max(abs(new_mu[j] - mu[j]) for j in range(k))
        change += max(abs(new_sig[j][jj] - sig[j][jj])
                      for j in range(k) for jj in range(k))
        mu, sig = new_mu, new_sig
        if change < tol:
            return mu, sig, it
    print("✗ EM 在 500 次迭代内未收敛，请检查数据（变量过多/样本过小/近共线）。")
    sys.exit(1)


# ================================================================ Little 检验
def pattern_groups(data, k):
    """按观测掩码分组，返回 ([(观测索引元组, 行索引列表), ...], 全缺失行数)。"""
    groups, all_missing = {}, 0
    for i, row in enumerate(data):
        o = tuple(j for j in range(k) if row[j] is not None)
        if not o:
            all_missing += 1
            continue
        groups.setdefault(o, []).append(i)
    return sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])), all_missing


def little_mcar(data, k, mu, sig):
    """Little (1988) T_MLμ 均值项统计量（naniar::mcar_test / Enders 2010 口径）。

    d² = Σ_j n_j (x̄_j−μ_j)' Σ_j⁻¹ (x̄_j−μ_j)，df = Σ_j k_j − k。
    返回 (chi2, df, 明细[(观测列, n_j, 马氏项)], 全缺失行数, 模式数)；df<=0 无法检验。
    """
    groups, all_missing = pattern_groups(data, k)
    chi2, df_sum = 0.0, 0
    details = []
    for o, rows in groups:
        idx = list(o)
        m = len(idx)
        n_j = len(rows)
        xbar = [mean([data[i][j] for i in rows]) for j in idx]
        mu_j = [mu[j] for j in idx]
        sig_j = [[sig[a][b] for b in idx] for a in idx]
        inv = invert_matrix(sig_j)
        if inv is None:
            print("✗ Little 检验失败：某缺失模式对应的 EM 协方差子阵奇异，无法求逆。")
            print("  建议：用 --scales 只选题项列（不要放总分/人口学派生列），或加大样本后重跑。")
            sys.exit(1)
        d = [xbar[a] - mu_j[a] for a in range(m)]
        md2 = sum(d[a] * d[b] * inv[a][b] for a in range(m) for b in range(m))
        chi2 += n_j * md2
        df_sum += m
        details.append((idx, n_j, n_j * md2))
    df = df_sum - k
    return chi2, df, details, all_missing, len(groups)


# ================================================================ 描述统计与报告
def descriptive(data, k, cols):
    n = len(data)
    per_col, total_missing = [], 0
    for j, c in enumerate(cols):
        vals = [row[j] for row in data if row[j] is not None]
        miss = n - len(vals)
        total_missing += miss
        per_col.append({"name": c, "valid": len(vals), "miss": miss,
                        "rate": miss / n if n else 0.0,
                        "mean": mean(vals) if vals else float("nan")})
    complete = sum(1 for row in data if all(v is not None for v in row))
    return {"n": n, "k": k, "cells": n * k, "miss_cells": total_missing,
            "rate": total_missing / (n * k) if n * k else 0.0,
            "complete": complete, "per_col": per_col}


def make_paragraph(desc, chi2, df, p, n_patterns, alpha=0.05):
    d = desc
    rates = [c["rate"] * 100 for c in d["per_col"] if c["miss"] > 0]
    if not rates:
        rng_clause = "各题均无缺失，"
    elif len(rates) == 1:
        rng_clause = f"仅 1 题有缺失（缺失率 {rates[0]:.1f}%），"
    elif min(rates) == max(rates):
        rng_clause = f"逐题缺失率均为 {rates[0]:.1f}%，"
    else:
        rng_clause = f"逐题缺失率介于 {min(rates):.1f}%～{max(rates):.1f}%，"
    base = (f"本研究对 {d['k']} 个分析题项、{d['n']} 份记录做缺失值分析："
            f"缺失单元格 {d['miss_cells']} 个，总缺失率 {d['rate'] * 100:.2f}%，"
            f"完整作答 {d['complete']} 份（{d['complete'] / d['n'] * 100:.1f}%），"
            f"{rng_clause}共出现 {n_patterns} 种缺失模式。")
    if d["miss_cells"] == 0:
        return base + "数据无缺失，全部记录进入分析，无需 MCAR 检验与插补。"
    if df is not None and df > 0:
        sig_txt = f"χ²({df})={chi2:.2f}，{fmt_p(p)}"
        if p < alpha:
            concl = (f"Little's MCAR 检验 {sig_txt}，p<{alpha:g}，拒绝完全随机缺失（MCAR）假设，"
                     "提示缺失可能与观测到的变量有关（MAR）。不建议简单成列删除或均值插补，"
                     "应优先采用多重插补（SPSS 多重插补/R mice）或全息极大似然 FIML（如 AMOS），"
                     "并在局限中说明缺失机制与处理方式。SPSS/R/AMOS 的具体操作步骤、Rubin 池化"
                     "规则与论文报告模板见 psychology/missing-imputation-guide.md。")
        else:
            concl = (f"Little's MCAR 检验 {sig_txt}，p≥{alpha:g}，未拒绝完全随机缺失（MCAR）假设，"
                     f"成列删除后完整样本 {d['complete']} 份可作为主分析样本；"
                     "但检验不显著不等于证明 MCAR（小样本时功效有限），仍建议报告缺失率并做敏感性说明。")
        return base + concl
    return base + ("缺失模式过于单一，Little's MCAR 检验自由度不足、无法计算；"
                   "请直接报告上述缺失情况，并依据缺失比例与专业判断选择处理方式。")


def write_csv(path, desc, groups, cols, chi2, df, p):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["【一、逐题缺失情况】"])
        w.writerow(["题项", "有效n", "缺失n", "缺失率%", "观测均值"])
        for c in desc["per_col"]:
            w.writerow([c["name"], c["valid"], c["miss"], f"{c['rate'] * 100:.2f}",
                        "" if c["valid"] == 0 else f"{c['mean']:.3f}"])
        w.writerow([])
        w.writerow(["【二、缺失模式】（○=作答 ×=缺失；列顺序与上表题项一致）"])
        w.writerow(["模式", "n", "占比%", "缺失变量"])
        for o, rows in groups:
            mark = "".join("○" if j in o else "×" for j in range(desc["k"]))
            miss_names = [cols[j] for j in range(desc["k"]) if j not in o]
            w.writerow([mark, len(rows), f"{len(rows) / desc['n'] * 100:.2f}",
                        "、".join(miss_names) if miss_names else "（完整作答）"])
        w.writerow([])
        w.writerow(["【三、Little's MCAR 检验】（T_MLμ 口径：naniar/Enders）"])
        w.writerow(["χ²", "df", "p", "结论"])
        if df and df > 0:
            concl = "拒绝MCAR(p<.05)，建议多重插补/FIML" if p < 0.05 else "未拒绝MCAR，可成列删除（附敏感性说明）"
            w.writerow([f"{chi2:.3f}", df, f"{p:.4f}", concl])
        elif desc["miss_cells"] == 0:
            w.writerow(["—", "—", "—", "无缺失，无需检验"])
        else:
            w.writerow(["—", "—", "—", "模式单一，无法检验"])


# ================================================================ 主流程
def main():
    parser = argparse.ArgumentParser(description="缺失值分析与 Little's MCAR 检验（纯标准库）")
    parser.add_argument("input", nargs="?", help="预处理后的问卷数据 CSV")
    parser.add_argument("--scales", default="", help="scales.txt（指定只分析量表题项，推荐）")
    parser.add_argument("--only", default="", help="只分析某一个量表（配合 --scales）")
    parser.add_argument("--csv-out", default="", help="导出目录（默认在数据同目录）")
    parser.add_argument("--report", default="", help="报告 txt 路径（默认在数据同目录）")
    parser.add_argument("--alpha", default="0.05", help="显著性水平，默认 0.05")
    args = parser.parse_args()

    if not args.input:
        print("✗ 请提供预处理后的问卷数据 CSV（菜单第1项的产物）。")
        sys.exit(1)
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"✗ 文件不存在：{args.input}")
        sys.exit(1)
    try:
        alpha = float(args.alpha)
    except ValueError:
        print("✗ --alpha 要写成数字（如 0.05）。")
        sys.exit(1)
    if not 0 < alpha < 1:
        print("✗ --alpha 取值要在 0 到 1 之间。")
        sys.exit(1)

    headers, data_raw = read_data(in_path)
    if not data_raw:
        print("✗ 数据文件没有任何记录行。")
        sys.exit(1)
    matrix = to_float_matrix(headers, data_raw)
    cols, col_src = select_columns(headers, matrix, args.scales or None, args.only or None)
    data, k = build_matrix(matrix, cols)
    desc = descriptive(data, k, cols)

    print("=" * 64)
    print("缺失值分析与 Little's MCAR 检验（Little, 1988；naniar/Enders 均值项口径）")
    print("=" * 64)
    print(f"分析列：{col_src}，共 {k} 个题项；记录 {desc['n']} 份。")
    print(f"总缺失率 {desc['rate'] * 100:.2f}%（{desc['miss_cells']}/{desc['cells']} 格），"
          f"完整作答 {desc['complete']} 份。")
    print("-" * 64)
    print("逐题缺失情况：")
    for c in desc["per_col"]:
        if c["miss"]:
            print(f"  {c['name']}: 缺 {c['miss']}（{c['rate'] * 100:.2f}%），观测均值 {c['mean']:.2f}")
    if desc["miss_cells"] == 0:
        print("  （无任何缺失，成列删除样本量不变；无需 MCAR 检验与插补）")

    chi2 = df = p = None
    groups, all_missing = pattern_groups(data, k)
    if desc["miss_cells"] > 0:
        if all_missing:
            print(f"  注：{all_missing} 份记录所有分析题项均缺失，已从检验中剔除（不计入任何模式）。")
        if k > 40:
            print(f"  提示：本次分析 {k} 个题项，EM 迭代耗时随题项数急剧增长（题项数^4 量级），"
                  f"可能需要数分钟。只想快点出结果时，用 --only 逐个量表分别跑。")
        mu, sig, iters = em_normal(data, k)
        chi2, df, details, all_missing, n_patterns = little_mcar(data, k, mu, sig)
        if df is not None and df > 0:
            p = chi2_sf(chi2, df)
            print("-" * 64)
            print(f"EM {iters} 次迭代收敛；缺失模式 {n_patterns} 种。")
            print(f"Little's MCAR 检验：χ²({df}) = {chi2:.3f}，{fmt_p(p)}")
            print("  解读：" + ("p<%.2g，拒绝 MCAR，建议多重插补/FIML，不要简单删除或均值插补；"
                  "操作步骤见 psychology/missing-imputation-guide.md。" % alpha
                  if p < alpha else "p≥%.2g，未拒绝 MCAR，可成列删除；但不显著≠证明 MCAR，报告缺失率并做敏感性说明。" % alpha))
        else:
            n_patterns = len(groups)
            print("-" * 64)
            print("缺失模式过于单一（自由度不足），Little's MCAR 检验无法计算，仅输出描述统计。")
    else:
        n_patterns = len(groups)

    print("-" * 64)
    print("可写进方法/结果章的表述（数字来自你的真实数据，请核对后使用）：")
    print("  " + make_paragraph(desc, chi2, df, p, n_patterns, alpha))
    print("-" * 64)
    print("红线：MCAR 检验基于连续多元正态假设，Likert 数据谨慎解读；检验不能证明 MCAR，"
          "任何插补都不得改变真实作答，方法章必须写清缺失处理。")

    out_dir = Path(args.csv_out) if args.csv_out else in_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / (in_path.stem + "_缺失值分析.csv")
    write_csv(csv_path, desc, groups, cols, chi2, df, p)
    report_path = Path(args.report) if args.report else out_dir / (in_path.stem + "_缺失值报告.txt")
    with io.open(report_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("缺失值分析与 Little's MCAR 检验报告\n" + "=" * 40 + "\n")
        f.write(f"数据：{in_path.name}；分析列：{col_src}；题项 {k} 个；记录 {desc['n']} 份\n")
        f.write(f"总缺失率 {desc['rate'] * 100:.2f}%；完整作答 {desc['complete']} 份；缺失模式 {n_patterns} 种\n\n")
        f.write("逐题缺失情况：\n")
        any_miss = False
        for c in desc["per_col"]:
            if c["miss"]:
                any_miss = True
                f.write(f"  {c['name']}：缺 {c['miss']}（{c['rate'] * 100:.2f}%），观测均值 {c['mean']:.2f}\n")
        if not any_miss:
            f.write("  无缺失。\n")
        f.write("\n缺失模式（○=作答 ×=缺失）：\n")
        for o, gr in groups:
            mark = "".join("○" if j in o else "×" for j in range(desc["k"]))
            miss_names = [cols[j] for j in range(desc["k"]) if j not in o]
            f.write(f"  {mark}  n={len(gr)}（{len(gr) / desc['n'] * 100:.1f}%）缺："
                    + ("、".join(miss_names) if miss_names else "完整作答") + "\n")
        f.write("\n")
        f.write(make_paragraph(desc, chi2, df, p, n_patterns, alpha) + "\n")
    print(f"\n已导出：{csv_path}")
    print(f"已导出：{report_path}")


if __name__ == "__main__":
    main()
