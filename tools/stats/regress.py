# -*- coding: utf-8 -*-
"""相关矩阵、回归、中介与调节

Pearson/Spearman 相关矩阵、偏相关（控制混淆变量）、
多元回归（含容差/VIF 共线性诊断）、Bootstrap 中介（模型4/6）、
调节效应（模型1，中心化交互项＋±1SD 简单斜率）。

本模块由 tools/auto_stats.py 拆分而来（v1.53.1），函数体逐行未改动。
"""

import csv
import math
import random

from .linalg import _ols_beta, invert_matrix, solve_least_squares
from .mathx import _z, chi2_sf, durbin_watson, f_p_value, fmt_p, mean, pearson_r, shapiro_wilk, sig_mark, spearman_r, stdev, t_p_two_sided
from .plots import _plot_simple_slopes

# ============ 相关矩阵、回归、中介与调节 ============

def correlation_matrix(matrix, num_cols, max_cols=15, method="pearson"):
    corr_fn = spearman_r if method == "spearman" else pearson_r
    label = "Spearman 秩相关（偏态/有序时的稳健相关）" if method == "spearman" else "Pearson"
    print("\n" + "=" * 60)
    print(f"相关分析（{label}）")
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
                r, n = corr_fn(matrix[c1], matrix[c2])
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


def _resolve_colname(name, pool, scales):
    """把用户输入解析成 pool 中真实列名：量表名→量表总分，其次原样。"""
    if name in pool:
        return name
    cand = name + "总分"
    if cand in pool:
        return cand
    if scales and name in scales and cand in pool:
        return cand
    return None


def partial_correlation_analysis(score_matrix, target_cols, control_names,
                                 scales=None, extra_matrix=None, output=None):
    """偏相关：在控制一组变量后，目标变量两两之间的净相关（相关矩阵求逆法）。
    控制变量可以是量表总分，也可以是 extra_matrix 中的数值型人口学列（性别/年级，需已编码为数字）。
    r_ij·Z = −Pij/√(Pii·Pjj)，P 为 [目标i,目标j,控制…] 相关矩阵的逆；
    显著性 t=r·√((n−2−k)/(1−r²))，df=n−2−k。"""
    pool = dict(score_matrix)
    if extra_matrix:
        for k, v in extra_matrix.items():
            pool.setdefault(k, v)
    targets = [c for c in target_cols if c in pool]
    controls = []
    skipped = []
    for c in control_names:
        rc = _resolve_colname(c.strip(), pool, scales)
        if rc and rc not in controls and rc not in targets:
            controls.append(rc)
        elif not rc:
            skipped.append(c)
    if len(targets) < 2:
        print("\n偏相关：可分析的目标变量不足2个，跳过。")
        return None
    if control_names and not controls:
        print("\n偏相关：控制变量均无效（找不到或与目标重名），已跳过；"
              "人口学变量需已预处理为数字编码。")
        return None
    print("\n" + "=" * 60)
    print(f"偏相关分析（控制变量：{('、'.join(controls) if controls else '无')}）")
    if skipped:
        print(f"  ⚠ 以下控制变量找不到或与目标重名，已跳过：{skipped}（人口学变量需已预处理为数字编码）")
    print("=" * 60)
    k = len(controls)
    rows = []
    short = {c: c.replace("总分", "")[:8] for c in targets}
    print("          " + "".join(f"{short[c]:>10}" for c in targets))
    for i, c1 in enumerate(targets):
        row_str = f"{short[c1]:<10}"
        for j, c2 in enumerate(targets):
            if j > i:
                row_str += "       -  "
                continue
            if i == j:
                row_str += "    1.000  "
                continue
            vars_ = [c1, c2] + controls
            nrows = len(pool[c1])
            cases = []
            for r in range(nrows):
                vals = []
                ok = True
                for v in vars_:
                    x = pool[v][r] if r < len(pool[v]) else None
                    try:
                        x = float(x)
                    except (TypeError, ValueError):
                        ok = False
                        break
                    if x is None:
                        ok = False
                        break
                    vals.append(x)
                if ok:
                    cases.append(vals)
            n = len(cases)
            df = n - 2 - k
            if n < k + 4 or df <= 0:
                row_str += "     n/a  "
                continue
            m = len(vars_)
            R = [[0.0] * m for _ in range(m)]
            for a in range(m):
                for b in range(m):
                    if a == b:
                        R[a][b] = 1.0
                    else:
                        ca = [row[a] for row in cases]
                        cb = [row[b] for row in cases]
                        rr, _ = pearson_r(ca, cb)
                        R[a][b] = rr if rr is not None else 0.0
            P = invert_matrix(R)
            if P is None:
                row_str += "     n/a  "
                continue
            pr = -P[0][1] / math.sqrt(max(P[0][0] * P[1][1], 1e-12))
            pr = max(min(pr, 1.0), -1.0)
            t = pr * math.sqrt(df / max(1 - pr * pr, 1e-12))
            p = t_p_two_sided(t, df)
            mark = sig_mark(p)
            row_str += f"{pr:>7.3f}{mark:<3}"
            rows.append({"变量1": c1, "变量2": c2, "偏r": round(pr, 3),
                         "df": df, "p": fmt_p(p), "显著性": mark, "N": n,
                         "控制变量": "、".join(controls)})
        print(row_str)
    print(f"\n注：表中为控制 {('、'.join(controls) if controls else '无')} 后的偏相关系数；*p<.05 **p<.01 ***p<.001")
    if output and rows:
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["变量1", "变量2", "偏r", "df", "p",
                                              "显著性", "N", "控制变量"])
            w.writeheader()
            w.writerows(rows)
        print(f"偏相关表已导出：{output}")
    return rows


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


def moderation_analysis(matrix, x_col, w_col, y_col, reps=5000,
                        seed=20260917, output=None):
    """调节效应（PROCESS模型1）：Y=b0+b1 Xc+b2 Wc+b3 Xc*Wc。

    X、W 中心化后构造交互项；交互项 b3 显著即存在调节；
    简单斜率按 W=均值±1SD（Aiken & West, 1991），解析 SE 为
    Var(b1+b3 w)=Cov11+w^2 Cov33+2w Cov13，并用 Bootstrap 百分位 CI 复核。
    """
    cols = [x_col, w_col, y_col]
    missing = [c for c in cols if not isinstance(c, str) or c not in matrix]
    if missing:
        print("✗ 调节分析失败：存在无法识别的量表名/列名，请对照 scales.txt 与数据表头检查 --x/--y/--moderator（人口学调节变量需已编码为数字）。")
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
        slope_marks = {"low": out_rows[0]["说明"], "mid": out_rows[1]["说明"],
                       "high": out_rows[2]["说明"]} if len(out_rows) == 3 else {}
        png_path = output.replace("_调节效应.csv", "_调节效应_简单斜率图.png")
        if png_path != output:
            if _plot_simple_slopes(x_col, w_col, y_col, sdx, sdw, b0, b1, b2, b3,
                                   slope_marks, mod_sig, fmt_p(b3_p), png_path):
                print(f"简单斜率图已导出：{png_path}")
            else:
                print("未安装 matplotlib，未生成简单斜率图（不影响数值结果）；pip install matplotlib 后重跑即可。")
    return {"R2": round(r2, 3), "交互B": round(b3, 3), "交互p": fmt_p(b3_p),
            "调节成立": bool(mod_sig), "简单斜率": out_rows}


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
    missing = [c for c in cols if not isinstance(c, str) or c not in matrix]
    if missing:
        print("✗ 中介分析失败：存在无法识别的量表名/列名，请对照 scales.txt 与数据表头检查 --x/--y/--mediators。")
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
