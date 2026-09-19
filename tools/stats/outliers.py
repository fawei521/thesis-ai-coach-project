# -*- coding: utf-8 -*-
"""多元异常值筛查（Mahalanobis D²）

D² 距离与 χ² 临界值（纯标准库二分求分位）、只标记不删除的处理原则提示、
明细 CSV 导出。
由 tools/stats/regress.py 拆分而来（拆分批1 大文件拆分），函数体逐行未改动。
"""

import csv


from .linalg import invert_matrix
from .mathx import chi2_sf, fmt_p, mean

# ============ 多元异常值筛查（Mahalanobis D²） ============

def _chi2_critical(df, alpha):
    """二分求 χ²(df) 上侧 α 分位数（纯标准库，60 次迭代足够精确）。"""
    lo, hi = 0.0, max(10.0, float(df) * 4.0)
    while chi2_sf(hi, df) > alpha:
        hi *= 2.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if chi2_sf(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def mahalanobis_outliers(matrix, cols, alpha=0.001, output=None):
    """多元异常值筛查（Mahalanobis D²，回归/中介/SEM 的假设检查之一）。

    matrix : dict，列名 -> 该列数值（缺失为 None）
    cols   : 参与筛查的变量（建议用进入回归/中介的量表总分，至少 2 个）
    alpha  : 判定阈值，默认 .001（Tabachnick & Fidell 惯例；D² 近似 χ²(df=变量数)）
    只【标记】不删除：输出每个完整个案的 D²/p/是否异常，并把完整明细导出 output（CSV）。
    返回 (结果行列表, 完整个案数)；条件不满足时返回 (None, 完整个案数) 并给中文提示。
    """
    print("\n" + "=" * 60)
    print("多元异常值筛查（Mahalanobis D²，回归/中介假设检查）")
    print("=" * 60)
    k = len(cols)
    if k < 2:
        print("✗ 至少需要 2 个变量才能计算多元距离，已跳过（单变量异常请结合描述统计/箱线图）。")
        return None, 0
    n_total = len(matrix[cols[0]])
    idx = [i for i in range(n_total) if all(matrix[c][i] is not None for c in cols)]
    n = len(idx)
    print(f"变量 {k} 个：{ '、'.join(cols) }")
    print(f"完整个案 {n} 份（{n_total - n} 份因所选变量有缺失未参与）。")
    if n <= k:
        print(f"✗ 完整个案数({n}) 不多于变量数({k})，协方差矩阵奇异无法求逆，已跳过。")
        print("  通常是样本太小或变量间完全共线；请增加样本或减少高度重复的变量。")
        return None, n

    X = [[matrix[c][i] for c in cols] for i in idx]
    mu = [mean([row[a] for row in X]) for a in range(k)]
    S = [[0.0] * k for _ in range(k)]
    for a in range(k):
        for b in range(a, k):
            cov = sum((row[a] - mu[a]) * (row[b] - mu[b]) for row in X) / (n - 1)
            S[a][b] = cov
            S[b][a] = cov
    Sinv = invert_matrix(S)
    if Sinv is None:
        print("✗ 协方差矩阵不可逆（变量可能完全线性相关，如总分与其分量同时入列），已跳过。")
        return None, n

    crit = _chi2_critical(k, alpha)
    rows_out = []
    for case_no, i in enumerate(idx):
        d = [X[case_no][a] - mu[a] for a in range(k)]
        d2 = sum(d[a] * Sinv[a][b] * d[b] for a in range(k) for b in range(k))
        if d2 < 0 and d2 > -1e-9:
            d2 = 0.0
        p = chi2_sf(max(d2, 0.0), k)
        flagged = p < alpha
        rows_out.append({"数据行号": i + 2, "D2": round(d2, 3), "df": k,
                         "p": fmt_p(p), "是否多元异常值": "是" if flagged else "否"})

    flagged_rows = [r for r in rows_out if r["是否多元异常值"] == "是"]
    flagged_rows.sort(key=lambda r: r["D2"], reverse=True)
    print(f"判定标准：D² > χ²({k}) 的上侧 {alpha} 分位 = {crit:.3f}（即 p < {alpha}）。")
    if not flagged_rows:
        print(f"✔ 没有个案超过临界值，按 p<{alpha} 标准未发现多元异常值。")
    else:
        print(f"⚠ 发现 {len(flagged_rows)} 个多元异常个案（只标记、不自动删除），D² 最大的若干个：")
        for r in flagged_rows[:20]:
            print(f"    · 数据行号 {r['数据行号']}：D²={r['D2']}，p={r['p']}")
        if len(flagged_rows) > 20:
            print(f"    · 其余 {len(flagged_rows) - 20} 个见导出的明细表")
    print("处理原则（与数据真实性 P0 一致）：")
    print("  · 多元异常值不等于无效问卷，不能为了让模型好看而删点；")
    print("  · 先回查原始作答确认非录入错误，再做敏感性分析：剔除与保留各跑一次核心模型，")
    print("    若系数方向、显著性结论稳定则保留并在文中说明，若结论翻转须与导师/审稿人如实讨论；")
    print("  · D² 假设多元正态，非正态或小样本时会偏大；建议用 JASP/SPSS（回归保存 Mahalanobis 距离、")
    print("    AMOS 输出 Mahalanobis d-squared）复核。")

    if output:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["数据行号", "D2", "df", "p", "是否多元异常值"])
            w.writeheader()
            w.writerows(sorted(rows_out, key=lambda r: r["D2"], reverse=True))
        print(f"多元异常值明细（含全部个案）已导出：{output}")
    return rows_out, n
