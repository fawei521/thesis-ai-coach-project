# -*- coding: utf-8 -*-
"""多元线性回归与共线性、残差诊断

最小二乘多元回归（β/SE/t/p/R²/调整 R²/F）、VIF 与容差共线性诊断、
残差 Durbin-Watson 与 Shapiro-Wilk 正态性诊断。
由 tools/stats/regress.py 拆分而来（拆分批1 大文件拆分），函数体逐行未改动。
"""

import math


from .linalg import invert_matrix, solve_least_squares
from .mathx import durbin_watson, f_p_value, fmt_p, mean, shapiro_wilk, sig_mark, stdev, t_p_two_sided

# ============ 多元线性回归与共线性、残差诊断 ============

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
    # 残差诊断：Durbin-Watson（一阶自相关）＋残差正态性
    resid = [y[i] - y_hat[i] for i in range(n)]
    dw, (rw, rp) = durbin_watson(resid), shapiro_wilk(resid)
    print("\n残差诊断（回归前提）：")
    if dw is not None:
        dw_tag = "接近2，未见一阶自相关" if 1.5 <= dw <= 2.5 else ("低于1.5 提示正自相关，请查 DW 临界值表(dL/dU)" if dw < 1.5 else "高于2.5 提示负自相关，请查 DW 临界值表(dL/dU)")
        print(f"  Durbin-Watson={dw:.3f}：{dw_tag}（1.5~2.5 为常见经验区间，非统一标准）")
    if rw is not None:
        ntag = "残差可视为近似正态" if rp >= 0.05 else "残差非正态（大样本结合偏度峰度/Q-Q 图判断）"
        print(f"  残差 Shapiro-Wilk：W={rw:.3f}，p={fmt_p(rp)}（{ntag}）")
    diag = {"DW": round(dw, 3) if dw is not None else None,
            "残差W": round(rw, 4) if rw is not None else None,
            "残差p": fmt_p(rp) if rp is not None else None}
    return {"R2": round(r2, 3), "调整R2": round(adj_r2, 3),
            "F": round(f, 3), "p": fmt_p(f_p), "系数": result_rows,
            "VIF": vif_map, "残差诊断": diag}
