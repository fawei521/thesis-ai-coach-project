# -*- coding: utf-8 -*-
"""调节效应（PROCESS 模型1）

中心化交互项、简单斜率（W=均值±1SD，解析 SE + Bootstrap 百分位 CI 复核）、
简单斜率图导出。
由 tools/stats/regress.py 拆分而来（v1.82 大文件拆分），函数体逐行未改动。
"""

import math
import random

from .plots import _plot_simple_slopes


from .linalg import invert_matrix, solve_least_squares
from .mathx import f_p_value, fmt_p, mean, sig_mark, stdev, t_p_two_sided

# ============ 调节效应（PROCESS 模型1） ============

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
